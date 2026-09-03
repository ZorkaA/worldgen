"""
Asset Catalog Builder and Cache Manager.
Discovers 3D models/prefabs from Synty PolygonMilitary assets,
orchestrates headless Blender extraction, applies VLM/heuristic metadata enrichment,
maintains persistent JSON caching, and produces a validated catalog.json.
"""

import os
import sys
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.catalog.vlm_enrich import enrich_asset_vlm, heuristic_enrich_asset

BLENDER_BIN = "/Applications/Blender.app/Contents/MacOS/Blender"
DEFAULT_MODELS_DIR = "/Users/jack/Downloads/assetripper_export/ExportedProject/Assets/PolygonMilitary/Models"
DEFAULT_CATALOG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RENDERS_DIR = os.path.join(DEFAULT_CATALOG_DIR, "renders")
DEFAULT_CATALOG_PATH = os.path.join(DEFAULT_CATALOG_DIR, "catalog.json")
BLENDER_SCRIPT_PATH = os.path.join(DEFAULT_CATALOG_DIR, "blender_extract.py")


def compute_file_hash(file_path: str) -> str:
    """Computes SHA-256 hash of a file for caching."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_cached_catalog(catalog_path: str) -> Dict[str, Any]:
    """Loads existing catalog.json if present."""
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CatalogBuilder] Warning: Failed to load existing catalog ({e}), creating fresh.")
    return {"version": "1.0.0", "generated_at": "", "asset_count": 0, "assets": {}, "prefabs": {}}


def run_blender_extraction(
    models_dir: str,
    renders_dir: str,
    assets_to_extract: Optional[List[str]] = None,
    resolution: int = 512,
    skip_renders: bool = False
) -> Dict[str, Any]:
    """
    Invokes headless Blender 2.83.3 CLI to extract bounding boxes and render multi-angle thumbnails.
    """
    tmp_out_json = os.path.join(renders_dir, "_temp_extracted_metrics.json")
    os.makedirs(renders_dir, exist_ok=True)

    cmd = [
        BLENDER_BIN,
        "--background",
        "--factory-startup",
        "-P", BLENDER_SCRIPT_PATH,
        "--",
        "--models-dir", models_dir,
        "--renders-dir", renders_dir,
        "--out-json", tmp_out_json,
        "--resolution", str(resolution)
    ]

    if assets_to_extract:
        cmd.extend(["--assets", ",".join(assets_to_extract)])
    if skip_renders:
        cmd.append("--skip-renders")

    print(f"[CatalogBuilder] Invoking Blender CLI extraction...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[CatalogBuilder] Blender extraction exited with code {result.returncode}")
        print(f"STDOUT:\n{result.stdout[-1000:]}")
        print(f"STDERR:\n{result.stderr[-1000:]}")

    extracted_data = {}
    if os.path.exists(tmp_out_json):
        try:
            with open(tmp_out_json, "r", encoding="utf-8") as f:
                extracted_data = json.load(f)
            os.remove(tmp_out_json)
        except Exception as e:
            print(f"[CatalogBuilder] Failed to read Blender metrics JSON: {e}")

    return extracted_data


def validate_catalog_data(catalog_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates catalog structure, bounding boxes, and tags against requirements.
    """
    errors = []
    if "assets" not in catalog_data and "prefabs" not in catalog_data:
        errors.append("Missing 'assets' or 'prefabs' dictionary in catalog root.")
        return False, errors

    assets_dict = catalog_data.get("assets") or catalog_data.get("prefabs", {})
    if not assets_dict:
        errors.append("Catalog contains no assets.")
        return False, errors

    for name, entry in assets_dict.items():
        # Check name
        if not entry.get("name") and not entry.get("prefab_name"):
            errors.append(f"Asset '{name}' missing 'name' or 'prefab_name'")

        # Check category and placement_role
        if not entry.get("category"):
            errors.append(f"Asset '{name}' missing 'category'")
        if not entry.get("placement_role"):
            errors.append(f"Asset '{name}' missing 'placement_role'")

        # Check tags
        tags = entry.get("tags")
        if not isinstance(tags, list) or len(tags) == 0:
            errors.append(f"Asset '{name}' tags must be non-empty list of strings")
        elif not all(isinstance(t, str) for t in tags):
            errors.append(f"Asset '{name}' has non-string tag entries")

        # Check bounding box
        bbox = entry.get("bounding_box")
        if not bbox or not isinstance(bbox, dict):
            errors.append(f"Asset '{name}' missing 'bounding_box'")
            continue

        for vec_field in ["min", "max", "size", "center"]:
            vec = bbox.get(vec_field) or (bbox.get("dimensions") if vec_field == "size" else None)
            if not isinstance(vec, list) or len(vec) != 3:
                errors.append(f"Asset '{name}' bounding_box.{vec_field} must be 3-element list of floats")
            elif not all(isinstance(v, (int, float)) for v in vec):
                errors.append(f"Asset '{name}' bounding_box.{vec_field} contains non-numeric values")

        # Check dimensions are positive
        dims = bbox.get("size") or bbox.get("dimensions")
        if dims and any(d <= 0 for d in dims):
            errors.append(f"Asset '{name}' has non-positive dimensions: {dims}")

    return len(errors) == 0, errors


def build_catalog(
    models_dir: str = DEFAULT_MODELS_DIR,
    renders_dir: str = DEFAULT_RENDERS_DIR,
    catalog_path: str = DEFAULT_CATALOG_PATH,
    use_vlm: bool = False,
    vlm_sample_limit: int = 1,
    force_rebuild: bool = False,
    asset_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Main catalog build pipeline:
    1. Discovers FBX models in models_dir.
    2. Checks cache hashes and identifies new/modified assets.
    3. Runs Blender CLI extraction for missing/updated assets.
    4. Enriches with VLM and robust naming heuristic.
    5. Saves and validates catalog.json.
    """
    os.makedirs(os.path.dirname(os.path.abspath(catalog_path)), exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)

    catalog_data = load_cached_catalog(catalog_path) if not force_rebuild else {"version": "1.0.0", "assets": {}, "prefabs": {}}
    existing_assets = catalog_data.get("assets", {})

    # Discover FBX files
    discovered_files: Dict[str, str] = {}
    if os.path.exists(models_dir):
        for root, _, files in os.walk(models_dir):
            for f in sorted(files):
                if f.lower().endswith(".fbx"):
                    name = os.path.splitext(f)[0]
                    if asset_filter is None or name in asset_filter or f in asset_filter:
                        discovered_files[name] = os.path.join(root, f)

    print(f"[CatalogBuilder] Discovered {len(discovered_files)} FBX assets in {models_dir}")

    # Determine which assets need Blender extraction
    to_extract: List[str] = []
    file_hashes: Dict[str, str] = {}

    for name, fbx_path in discovered_files.items():
        fhash = compute_file_hash(fbx_path)
        file_hashes[name] = fhash

        # Check if cached entry exists and is up-to-date
        cached_entry = existing_assets.get(name)
        cached_hash = cached_entry.get("file_hash") if cached_entry else None
        
        # Check if thumbnails exist
        front_img = os.path.join(DEFAULT_CATALOG_DIR, f"renders/{name}_front.png")
        renders_exist = os.path.exists(front_img)

        if not cached_entry or cached_hash != fhash or not renders_exist or force_rebuild:
            to_extract.append(name)

    print(f"[CatalogBuilder] {len(to_extract)} assets require Blender extraction / rendering.")

    extracted_metrics: Dict[str, Any] = {}
    if to_extract:
        # Run Blender extraction in batch
        extracted_metrics = run_blender_extraction(
            models_dir=models_dir,
            renders_dir=renders_dir,
            assets_to_extract=to_extract,
            resolution=512,
            skip_renders=False
        )

    # Process and assemble catalog
    updated_assets: Dict[str, Any] = {}
    vlm_queries_run = 0

    for name, fbx_path in discovered_files.items():
        fhash = file_hashes.get(name, "")
        
        # If freshly extracted
        if name in extracted_metrics:
            m = extracted_metrics[name]
            bbox = m["bounding_box"]
            render_paths = m["render_paths"]
            abs_render_paths = m.get("abs_render_paths", {
                "front": os.path.join(renders_dir, f"{name}_front.png"),
                "side": os.path.join(renders_dir, f"{name}_side.png"),
                "top": os.path.join(renders_dir, f"{name}_top.png"),
            })

            # Enrichment
            if use_vlm and vlm_queries_run < vlm_sample_limit:
                print(f"[CatalogBuilder] Querying Ollama VLM for '{name}'...")
                meta = enrich_asset_vlm(name, bbox["size"], abs_render_paths, timeout_sec=20.0)
                vlm_queries_run += 1
            else:
                meta = heuristic_enrich_asset(name, bbox["size"])

            entry = {
                "name": name,
                "prefab_name": name,
                "source_file": fbx_path,
                "file_hash": fhash,
                "category": meta["category"],
                "placement_role": meta["placement_role"],
                "tags": meta["tags"],
                "description": meta["description"],
                "bounding_box": bbox,
                "render_paths": render_paths,
                "thumbnails": render_paths,
                "affinities": meta["affinities"],
                "suggested_density": meta["suggested_density"],
                "footprint_type": meta["footprint_type"],
                "stackable": meta["stackable"],
                "supported_factions": meta["supported_factions"],
                "max_destruction_level": meta["max_destruction_level"]
            }
            updated_assets[name] = entry

        elif name in existing_assets:
            # Preserve cached
            entry = existing_assets[name]
            entry["file_hash"] = fhash
            # Ensure exact mathematical consistency of bounding box
            if "bounding_box" in entry and isinstance(entry["bounding_box"], dict):
                b = entry["bounding_box"]
                min_v = [round(c, 3) for c in b.get("min", [0.0, 0.0, 0.0])]
                max_v = [round(c, 3) for c in b.get("max", [1.0, 1.0, 1.0])]
                for i in range(3):
                    if max_v[i] <= min_v[i]:
                        max_v[i] = round(min_v[i] + 0.001, 3)
                sz_v = [round(max_v[i] - min_v[i], 3) for i in range(3)]
                ctr_v = [round((min_v[i] + max_v[i]) / 2.0, 3) for i in range(3)]
                b["min"] = min_v
                b["max"] = max_v
                b["size"] = sz_v
                b["dimensions"] = sz_v
                b["center"] = ctr_v
            if "thumbnails" not in entry:
                entry["thumbnails"] = entry.get("render_paths", {})
            if "prefab_name" not in entry:
                entry["prefab_name"] = entry.get("name", name)
            updated_assets[name] = entry

    # Assemble complete catalog JSON
    now_iso = datetime.now(timezone.utc).isoformat()
    catalog = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "version": "1.0.0",
        "generated_at": now_iso,
        "asset_count": len(updated_assets),
        "assets": updated_assets,
        "prefabs": updated_assets  # Alias for dual interface compatibility
    }

    # Validate
    valid, errors = validate_catalog_data(catalog)
    if not valid:
        print(f"[CatalogBuilder] Validation warnings ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")

    # Write catalog.json
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print(f"[CatalogBuilder] Successfully saved catalog with {len(updated_assets)} assets to {catalog_path}")
    return catalog


def get_catalog(catalog_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    Cached getter for the asset catalog.
    If catalog does not exist or force_reload is True, builds it.
    """
    path = catalog_path or DEFAULT_CATALOG_PATH
    if not os.path.exists(path) or force_reload:
        return build_catalog(catalog_path=path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Asset Catalog Builder CLI")
    parser.add_argument("--models-dir", type=str, default=DEFAULT_MODELS_DIR, help="Path to FBX models")
    parser.add_argument("--renders-dir", type=str, default=DEFAULT_RENDERS_DIR, help="Path for rendered thumbnails")
    parser.add_argument("--catalog-out", type=str, default=DEFAULT_CATALOG_PATH, help="Path for catalog.json")
    parser.add_argument("--use-vlm", action="store_true", help="Enable Ollama VLM enrichment")
    parser.add_argument("--vlm-samples", type=int, default=3, help="Max VLM queries to run")
    parser.add_argument("--force", action="store_true", help="Force rebuild all assets")
    
    args = parser.parse_args()
    build_catalog(
        models_dir=args.models_dir,
        renders_dir=args.renders_dir,
        catalog_path=args.catalog_out,
        use_vlm=args.use_vlm,
        vlm_sample_limit=args.vlm_samples,
        force_rebuild=args.force
    )
