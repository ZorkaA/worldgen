"""End-to-End Procedural Generation Pipeline."""

import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import numpy as np

from ..core.schemas import (
    GenerateWorldRequest,
    TerrainConfig,
    ZoneConfig,
    WorldManifest,
    ManifestMetadata,
    TerrainManifest,
)
from .terrain import generate_terrain
from .erosion import simulate_hydraulic_erosion
from .zones import generate_zones, flatten_zone_footprints
from .buildings import place_buildings
from .roads import generate_roads


def generate_world_pipeline(
    request: Optional[GenerateWorldRequest] = None,
    seed: Optional[int] = None,
) -> Tuple[WorldManifest, np.ndarray, Dict[str, Any]]:
    """Execute complete world generation pipeline and produce WorldManifest.

    Returns:
        manifest: WorldManifest model
        final_heightmap: 2D NumPy array of shape (resolution, resolution)
        summary: dict containing generation metrics and execution timing
    """
    start_time = time.perf_counter()

    # Resolve seed and configurations
    effective_seed = seed
    if effective_seed is None and request and request.seed is not None:
        effective_seed = request.seed
    if effective_seed is None:
        effective_seed = 42

    # Map negative seed to unsigned 32-bit integer for RNGs
    uint_seed = int(effective_seed) & 0xFFFFFFFF

    terrain_config = request.terrain.model_copy() if (request and request.terrain) else TerrainConfig()
    zone_config = request.zones.model_copy() if (request and request.zones) else ZoneConfig()

    # Merge flat request parameters if supplied
    if request:
        if request.resolution is not None:
            terrain_config.resolution = request.resolution
        if request.world_size is not None:
            terrain_config.world_size = request.world_size
        if request.scale is not None:
            terrain_config.scale = request.scale
        if request.octaves is not None:
            terrain_config.octaves = request.octaves
        if request.persistence is not None:
            terrain_config.persistence = request.persistence
        if request.lacunarity is not None:
            terrain_config.lacunarity = request.lacunarity
        if request.domain_warp_strength is not None:
            terrain_config.domain_warp_strength = request.domain_warp_strength
        if request.erosion_droplets is not None:
            terrain_config.erosion_droplets = request.erosion_droplets
        if request.height_scale is not None:
            terrain_config.height_scale = request.height_scale
        if request.min_zone_distance is not None:
            zone_config.min_zone_distance = request.min_zone_distance
        if request.zone_count_target is not None:
            zone_config.zone_count_target = request.zone_count_target
        if request.default_factions is not None:
            zone_config.default_factions = request.default_factions
        if request.max_destruction is not None:
            zone_config.max_destruction = request.max_destruction
        if request.min_radius is not None:
            zone_config.min_radius = request.min_radius
        if request.max_radius is not None:
            zone_config.max_radius = request.max_radius

    # 1. Base Terrain Synthesis (Perlin FBM + Chained Domain Warping)
    t0 = time.perf_counter()
    raw_heightmap = generate_terrain(config=terrain_config, seed=uint_seed)
    t_terrain = time.perf_counter() - t0

    # 2. Hydraulic Erosion Simulation (Numba JIT)
    t0 = time.perf_counter()
    eroded_heightmap = simulate_hydraulic_erosion(
        heightmap=raw_heightmap,
        droplets=terrain_config.erosion_droplets,
        seed=uint_seed,
    )
    t_erosion = time.perf_counter() - t0

    # 3. Poisson-Disc Zone Distribution
    t0 = time.perf_counter()
    zones, zone_internal_data = generate_zones(
        heightmap=eroded_heightmap,
        terrain_config=terrain_config,
        zone_config=zone_config,
        seed=uint_seed,
    )
    t_zones = time.perf_counter() - t0

    # 4. Plateau Footprint Flattening (C1 Hermite smoothstep)
    t0 = time.perf_counter()
    flattened_heightmap = flatten_zone_footprints(
        heightmap=eroded_heightmap,
        zones=zones,
        zone_internal_data=zone_internal_data,
        terrain_config=terrain_config,
    )
    t_flatten = time.perf_counter() - t0

    # 5. SAT Oriented Bounding Box Building Placement
    t0 = time.perf_counter()
    buildings = place_buildings(
        heightmap=flattened_heightmap,
        zones=zones,
        terrain_config=terrain_config,
        seed=uint_seed,
    )
    t_buildings = time.perf_counter() - t0

    # 6. Slope-Aware A* Road Network Routing & Spline Smoothing
    t0 = time.perf_counter()
    roads = generate_roads(
        heightmap=flattened_heightmap,
        zones=zones,
        terrain_config=terrain_config,
        seed=uint_seed,
    )
    t_roads = time.perf_counter() - t0

    total_time = time.perf_counter() - start_time

    # Calculate grid cell size
    res = terrain_config.resolution
    world_w = terrain_config.world_size[0]
    world_h = terrain_config.world_size[1]
    world_l = terrain_config.world_size[2]
    cell_size = float(world_w / max(1, res - 1))

    # Construct final WorldManifest model
    metadata = ManifestMetadata(
        version="1.0.0",
        seed=effective_seed,
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        generator="FastAPI Procedural WorldGen v1.0",
        bounds=[0.0, 0.0, 0.0, float(world_w), float(world_h), float(world_l)],
        world_size_meters=float(world_w),
        max_elevation_meters=float(world_h),
        zone_count=len(zones),
        building_count=len(buildings),
        road_segment_count=len(roads),
    )

    terrain_manifest = TerrainManifest(
        resolution=res,
        world_size=terrain_config.world_size,
        heightmap=flattened_heightmap.tolist(),
        cell_size=round(cell_size, 3),
        height_scale=terrain_config.height_scale,
        heightmap_encoding="float32_array",
        heightmap_url="/api/v1/heightmap/png",
    )

    manifest = WorldManifest(
        metadata=metadata,
        terrain=terrain_manifest,
        zones=zones,
        buildings=buildings,
        roads=roads,
    )

    summary = {
        "seed": effective_seed,
        "total_execution_time_seconds": round(total_time, 4),
        "timing_breakdown": {
            "terrain_generation_s": round(t_terrain, 4),
            "hydraulic_erosion_s": round(t_erosion, 4),
            "zone_distribution_s": round(t_zones, 4),
            "plateau_flattening_s": round(t_flatten, 4),
            "building_placement_s": round(t_buildings, 4),
            "road_routing_s": round(t_roads, 4),
        },
        "metrics": {
            "resolution": res,
            "zone_count": len(zones),
            "building_count": len(buildings),
            "road_count": len(roads),
            "min_height": round(float(np.min(flattened_heightmap)), 2),
            "max_height": round(float(np.max(flattened_heightmap)), 2),
        },
    }

    return manifest, flattened_heightmap, summary
