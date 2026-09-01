"""FastAPI API routes for procedural generation, world manifest, catalog, and health."""

import io
import json
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from ..core.config import CATALOG_FILE, RENDERS_DIR
from ..core.schemas import (
    GenerateWorldRequest,
    GenerateWorldResponse,
    WorldManifest,
    HealthStatus,
)
from ..generator.pipeline import generate_world_pipeline
from ..generator.buildings import load_asset_catalog

router = APIRouter()

# In-memory storage for active manifests and heightmaps
_active_manifest: Optional[WorldManifest] = None
_active_heightmap: Optional[np.ndarray] = None
_manifest_cache: Dict[int, WorldManifest] = {}
_heightmap_cache: Dict[int, np.ndarray] = {}


def _get_or_create_manifest(seed: Optional[int] = None) -> Tuple[WorldManifest, np.ndarray]:
    """Retrieve existing manifest or lazily generate a default one."""
    global _active_manifest, _active_heightmap

    target_seed = seed if seed is not None else 42

    if target_seed in _manifest_cache:
        return _manifest_cache[target_seed], _heightmap_cache[target_seed]

    if _active_manifest is not None and seed is None:
        return _active_manifest, _active_heightmap

    # Generate new default world
    req = GenerateWorldRequest(seed=target_seed)
    manifest, heightmap, _ = generate_world_pipeline(request=req, seed=target_seed)
    _active_manifest = manifest
    _active_heightmap = heightmap
    _manifest_cache[target_seed] = manifest
    _heightmap_cache[target_seed] = heightmap
    return manifest, heightmap


@router.post("/generate", response_model=GenerateWorldResponse)
@router.post("/v1/generate", response_model=GenerateWorldResponse)
def generate_world_endpoint(request: Optional[GenerateWorldRequest] = None):
    """Generate a procedural world with terrain, zones, buildings, and roads."""
    global _active_manifest, _active_heightmap

    if request is None:
        request = GenerateWorldRequest(seed=42)

    effective_seed = request.seed if request.seed is not None else 42
    manifest, heightmap, summary = generate_world_pipeline(request=request, seed=effective_seed)

    _active_manifest = manifest
    _active_heightmap = heightmap
    _manifest_cache[effective_seed] = manifest
    _heightmap_cache[effective_seed] = heightmap

    return GenerateWorldResponse(
        success=True,
        seed=effective_seed,
        execution_time_seconds=summary["total_execution_time_seconds"],
        summary=summary,
        manifest=manifest,
    )


@router.get("/manifest", response_model=WorldManifest)
@router.get("/v1/manifest", response_model=WorldManifest)
def get_manifest_endpoint(seed: Optional[int] = Query(None, description="Optional seed to retrieve")):
    """Get current active world manifest or generate default on demand."""
    manifest, _ = _get_or_create_manifest(seed=seed)
    return manifest


@router.get("/catalog")
@router.get("/v1/catalog")
def get_catalog_endpoint():
    """Retrieve the Synty PolygonMilitary asset catalog metadata."""
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback to loaded dictionary
    prefabs = load_asset_catalog()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "version": "1.0.0",
        "assets": prefabs,
        "prefabs": prefabs,
        "asset_count": len(prefabs),
    }


@router.get("/catalog/prefabs/{name}")
@router.get("/v1/catalog/prefabs/{name}")
def get_prefab_endpoint(name: str):
    """Get metadata for a single prefab by name."""
    catalog = load_asset_catalog()
    if name in catalog:
        return catalog[name]
    raise HTTPException(status_code=404, detail=f"Prefab '{name}' not found in catalog.")


@router.get("/heightmap/png")
@router.get("/v1/heightmap/png")
def get_heightmap_png_endpoint(seed: Optional[int] = Query(None)):
    """Export the terrain heightmap as a 16-bit grayscale PNG image."""
    _, heightmap = _get_or_create_manifest(seed=seed)

    h_min = float(np.min(heightmap))
    h_max = float(np.max(heightmap))
    if h_max > h_min:
        norm_h = (heightmap - h_min) / (h_max - h_min)
    else:
        norm_h = np.zeros_like(heightmap)

    uint16_data = (norm_h * 65535.0).astype(np.uint16)
    img = Image.fromarray(uint16_data, mode="I;16")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/heightmap/raw")
@router.get("/v1/heightmap/raw")
def get_heightmap_raw_endpoint(seed: Optional[int] = Query(None)):
    """Export the terrain heightmap as raw 32-bit float binary buffer."""
    _, heightmap = _get_or_create_manifest(seed=seed)
    float32_bytes = heightmap.astype(np.float32).tobytes()
    return Response(content=float32_bytes, media_type="application/octet-stream")


@router.get("/health", response_model=HealthStatus)
@router.get("/v1/health", response_model=HealthStatus)
def get_health_endpoint():
    """Service health check."""
    catalog_exists = CATALOG_FILE.exists()
    catalog_data = load_asset_catalog()
    return HealthStatus(
        status="ok",
        version="1.0.0",
        generator="FastAPI Procedural WorldGen v1.0",
        catalog_available=catalog_exists or len(catalog_data) > 0,
        catalog_asset_count=len(catalog_data),
    )
