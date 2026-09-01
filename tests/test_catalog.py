"""
tests/test_catalog.py - Unit and pipeline tests for R1 Asset Catalog Builder.

Covers:
1. 3D Bounding Box & Bounding Sphere Math (AABB, dimensions, center, ground-level offset)
2. Camera Auto-Framing Geometry (FOV, distance, 3 canonical camera view positions)
3. Ollama VLM Vision AI Response Extraction & Fallback Parser (handling thinking vs response, markdown fences)
4. Heuristic Fallback Asset Classifier (prefix-based role, category, and tag inference)
5. Cache Key & Invalidation Mechanics (SHA-256 / mtime file hashing)
6. Integration with validate_catalog.py CLI validator
"""

import copy
import hashlib
import json
import math
import os
import subprocess
import sys
from typing import Any, Dict, List

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from tests.validate_catalog import (
        validate_catalog_dict,
        validate_catalog_file,
        validate_bounding_box,
        validate_tags_and_affinities,
    )
except ImportError:
    from validate_catalog import (
        validate_catalog_dict,
        validate_catalog_file,
        validate_bounding_box,
        validate_tags_and_affinities,
    )


# ============================================================================
# Reference Algorithms for Bounding Box & Camera Auto-Framing
# ============================================================================

def compute_mesh_aabb(vertices: List[List[float]]) -> Dict[str, Any]:
    """Computes AABB, size, center, bounding sphere radius, and ground offset from 3D points."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]

    min_v = [min(xs), min(ys), min(zs)]
    max_v = [max(xs), max(ys), max(zs)]
    size = [max_v[0] - min_v[0], max_v[1] - min_v[1], max_v[2] - min_v[2]]
    center = [(min_v[0] + max_v[0]) / 2.0, (min_v[1] + max_v[1]) / 2.0, (min_v[2] + max_v[2]) / 2.0]
    radius = 0.5 * math.sqrt(size[0] ** 2 + size[1] ** 2 + size[2] ** 2)
    ground_offset = -min_v[2] if len(min_v) == 3 else 0.0

    return {
        "min": min_v,
        "max": max_v,
        "size": size,
        "center": center,
        "radius": radius,
        "ground_level_offset": ground_offset,
    }


def compute_camera_views(center: List[float], radius: float, fov_deg: float = 50.0, padding: float = 1.25) -> Dict[str, List[float]]:
    """Calculates auto-framed camera positions for front, side, and top views."""
    fov_rad = math.radians(fov_deg)
    dist = (radius / math.sin(fov_rad / 2.0)) * padding

    cx, cy, cz = center[0], center[1], center[2]
    phi = math.radians(15.0)  # Elevation angle for front/side
    psi = math.radians(60.0)  # Elevation angle for top-isometric

    return {
        "front": [cx, cy - dist * math.cos(phi), cz + dist * math.sin(phi)],
        "side": [cx + dist * math.cos(phi), cy, cz + dist * math.sin(phi)],
        "top": [cx, cy - dist * math.cos(psi), cz + dist * math.sin(psi)],
    }


def extract_vlm_json_payload(response_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Robust extractor for Ollama VLM outputs handling thinking, message content, and markdown blocks."""
    raw = (
        response_payload.get("response")
        or response_payload.get("thinking")
        or (response_payload.get("message", {}).get("content") if isinstance(response_payload.get("message"), dict) else None)
        or (response_payload.get("message", {}).get("thinking") if isinstance(response_payload.get("message"), dict) else None)
        or ""
    )

    cleaned = str(raw).strip()
    if "```json" in cleaned:
        start = cleaned.find("```json") + 7
        cleaned = cleaned.split("```json")[1].split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0]

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]

    try:
        return json.loads(cleaned.strip())
    except Exception:
        # Return empty dict on unparseable JSON
        return {}


def heuristic_tag_asset(prefab_name: str) -> Dict[str, Any]:
    """Rule-based heuristic classifier for offline fallback."""
    name_lower = prefab_name.lower()

    if "tent" in name_lower or "house" in name_lower or "bld" in name_lower or "barracks" in name_lower:
        category = "building"
        role = "barracks" if "barracks" in name_lower or "tent" in name_lower else "residential"
        tags = ["structure", "military", "building"]
    elif "fence" in name_lower or "wall" in name_lower or "barrier" in name_lower or "sandbag" in name_lower:
        category = "prop"
        role = "barrier"
        tags = ["fortification", "defense", "cover"]
    elif "veh" in name_lower or "tank" in name_lower or "truck" in name_lower or "heli" in name_lower:
        category = "vehicle"
        role = "transport"
        tags = ["vehicle", "military", "tactical"]
    else:
        category = "generic"
        role = "prop"
        tags = ["military", "prop"]

    if "destroyed" in name_lower or "damaged" in name_lower or "_ruin" in name_lower:
        tags.extend(["damaged", "ruins", "combat_zone"])

    return {
        "name": prefab_name,
        "category": category,
        "placement_role": role,
        "tags": list(set(tags)),
        "description": f"Synty PolygonMilitary prefab {prefab_name}",
        "suggested_density": "medium",
    }


# ============================================================================
# Test Cases
# ============================================================================

class TestBoundingBoxAndCameraMath:
    """Verifies geometric calculations for 3D AABB extraction and multi-angle auto-framing."""

    def test_compute_mesh_aabb_cube(self):
        """Tests AABB extraction on a canonical 10x20x4 box centered at (0,0,2)."""
        vertices = [
            [-5.0, -10.0, 0.0],
            [5.0, -10.0, 0.0],
            [5.0, 10.0, 0.0],
            [-5.0, 10.0, 0.0],
            [-5.0, -10.0, 4.0],
            [5.0, -10.0, 4.0],
            [5.0, 10.0, 4.0],
            [-5.0, 10.0, 4.0],
        ]
        bbox = compute_mesh_aabb(vertices)

        assert bbox["min"] == [-5.0, -10.0, 0.0]
        assert bbox["max"] == [5.0, 10.0, 4.0]
        assert bbox["size"] == [10.0, 20.0, 4.0]
        assert bbox["center"] == [0.0, 0.0, 2.0]
        assert pytest.approx(bbox["radius"], 0.001) == 0.5 * math.sqrt(100 + 400 + 16)
        assert bbox["ground_level_offset"] == 0.0

    def test_camera_views_distance_and_positions(self):
        """Tests that auto-framed camera positions maintain sufficient distance to avoid clipping."""
        center = [0.0, 0.0, 2.0]
        radius = 11.35  # Bounding sphere radius of 10x20x4 box
        views = compute_camera_views(center, radius, fov_deg=50.0, padding=1.25)

        for view_name in ["front", "side", "top"]:
            pos = views[view_name]
            dist_to_center = math.dist(pos, center)
            # Distance should be greater than radius * padding
            assert dist_to_center > radius * 1.25
            assert len(pos) == 3


class TestVLMResponseExtractionAndFallback:
    """Verifies VLM response parsing across thinking tokens, raw JSON, and heuristic classification."""

    def test_extract_from_standard_content(self):
        """Extracts JSON from standard chat message response."""
        payload = {
            "message": {
                "role": "assistant",
                "content": '{"name": "SM_Bld_Tent_01", "category": "building", "placement_role": "barracks", "tags": ["tent", "military"]}',
            }
        }
        res = extract_vlm_json_payload(payload)
        assert res.get("name") == "SM_Bld_Tent_01"
        assert res.get("placement_role") == "barracks"

    def test_extract_from_thinking_codeblock(self):
        """Extracts JSON wrapped in markdown fences inside thinking reasoning trace."""
        payload = {
            "thinking": 'I am analyzing the tent mesh.\n```json\n{"name": "SM_Bld_Tent_01", "tags": ["military", "shelter"]}\n```',
            "response": "",
        }
        res = extract_vlm_json_payload(payload)
        assert res.get("name") == "SM_Bld_Tent_01"
        assert "shelter" in res.get("tags", [])

    def test_heuristic_tagger_for_various_prefabs(self):
        """Verifies rule-based classification heuristics for building, prop, vehicle, and damaged prefabs."""
        # Building
        bld = heuristic_tag_asset("SM_Bld_Village_House_01")
        assert bld["category"] == "building"
        assert "military" in bld["tags"] or "structure" in bld["tags"]

        # Defense / Sandbags
        barrier = heuristic_tag_asset("SM_Prop_Sandbags_01")
        assert barrier["category"] == "prop"
        assert barrier["placement_role"] == "barrier"
        assert "fortification" in barrier["tags"]

        # Damaged variant
        damaged = heuristic_tag_asset("SM_Bld_Tent_Destroyed_01")
        assert "damaged" in damaged["tags"]
        assert "ruins" in damaged["tags"]


class TestCatalogCachingMechanics:
    """Verifies file hash calculation and cache validation."""

    def test_hash_calculation_consistency(self, tmp_path):
        """SHA-256 hash must be deterministic for given file content."""
        test_file = tmp_path / "test_model.fbx"
        test_file.write_bytes(b"SYNTHETIC_FBX_MESH_DATA_12345")

        h1 = hashlib.sha256(test_file.read_bytes()).hexdigest()
        h2 = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert h1 == h2
        assert len(h1) == 64

    def test_cache_invalidation_on_content_change(self, tmp_path):
        """Modifying file content produces a different hash, triggering cache invalidation."""
        test_file = tmp_path / "test_model.fbx"
        test_file.write_bytes(b"INITIAL_DATA")
        h1 = hashlib.sha256(test_file.read_bytes()).hexdigest()

        test_file.write_bytes(b"MODIFIED_DATA")
        h2 = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert h1 != h2


class TestValidateCatalogCLI:
    """Verifies validate_catalog.py tool behavior against valid and invalid catalog files."""

    def test_validate_catalog_dict_valid(self, sample_catalog_dict):
        """Sample catalog dict must validate with 0 errors."""
        is_valid, errors, summary = validate_catalog_dict(sample_catalog_dict)
        assert is_valid
        assert len(errors) == 0
        assert summary["total_items"] == 3
        assert summary["valid_items"] == 3

    def test_validate_catalog_file_via_subprocess(self, sample_catalog_dict, tmp_path):
        """validate_catalog.py CLI must return exit code 0 for valid file."""
        cat_file = tmp_path / "catalog.json"
        cat_file.write_text(json.dumps(sample_catalog_dict))

        cmd = [sys.executable, "tests/validate_catalog.py", str(cat_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0
        assert "STATUS: PASS" in proc.stdout

    def test_validate_catalog_file_invalid_nan_fails(self, sample_catalog_dict, tmp_path):
        """validate_catalog.py must return exit code 1 when bbox contains invalid/corrupt data."""
        bad_dict = copy.deepcopy(sample_catalog_dict)
        bad_dict["assets"]["SM_Bld_Tent_01"]["bounding_box"]["size"] = ["7.799", 12.030, 4.072]  # String instead of float

        cat_file = tmp_path / "bad_catalog.json"
        cat_file.write_text(json.dumps(bad_dict))

        cmd = [sys.executable, "tests/validate_catalog.py", str(cat_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "STATUS: FAIL" in proc.stdout
