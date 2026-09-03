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
from .mesh import generate_adaptive_mesh


def generate_world_pipeline(
    request: Optional[GenerateWorldRequest] = None,
    seed: Optional[int] = None,
    existing_eroded_heightmap: Optional[np.ndarray] = None,
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
    zone_config = request.zones.model_copy() if (request and isinstance(request.zones, ZoneConfig)) else ZoneConfig()

    # Merge flat request parameters if supplied
    if request:
        if request.resolution is not None:
            terrain_config.resolution = request.resolution
        if request.world_size is not None:
            terrain_config.world_size = request.world_size
        if request.map_width_km is not None:
            terrain_config.map_width_km = request.map_width_km
            terrain_config.world_size[0] = request.map_width_km * 1000.0
        if request.map_length_km is not None:
            terrain_config.map_length_km = request.map_length_km
            terrain_config.world_size[2] = request.map_length_km * 1000.0
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
        if request.deformation_strength is not None:
            terrain_config.deformation_strength = request.deformation_strength
        if request.edge_margin is not None:
            terrain_config.edge_margin = request.edge_margin
            zone_config.edge_margin = request.edge_margin
        if request.flattening_falloff is not None:
            terrain_config.flattening_falloff = request.flattening_falloff
        if request.flattening_margin_ratio is not None:
            terrain_config.flattening_margin_ratio = request.flattening_margin_ratio
        if request.max_road_slope is not None:
            terrain_config.max_road_slope = request.max_road_slope
        if request.adaptive_mesh_max_error is not None:
            terrain_config.adaptive_mesh_max_error = request.adaptive_mesh_max_error
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

    # 1 & 2: Terrain generation and erosion
    if existing_eroded_heightmap is not None:
        eroded_heightmap = existing_eroded_heightmap
        t_terrain = 0.0
        t_erosion = 0.0
    else:
        t0 = time.perf_counter()
        raw_heightmap = generate_terrain(config=terrain_config, seed=uint_seed)
        t_terrain = time.perf_counter() - t0

        t0 = time.perf_counter()
        eroded_heightmap = simulate_hydraulic_erosion(
            heightmap=raw_heightmap,
            droplets=terrain_config.erosion_droplets,
            seed=uint_seed,
        )
        t_erosion = time.perf_counter() - t0

    # 3. Poisson-Disc Zone Distribution or use existing provided zones
    passed_zones = None
    if request:
        if request.existing_zones:
            passed_zones = request.existing_zones
        elif request.zones_list:
            passed_zones = request.zones_list
        elif isinstance(request.zones, list):
            passed_zones = request.zones

    t0 = time.perf_counter()
    if passed_zones is not None and len(passed_zones) > 0:
        zones = passed_zones
        zone_internal_data = [
            {
                "id": z.id,
                "center_x": z.center[0],
                "center_z": z.center[2],
                "radius": z.radius,
                "phi1": 0.0,
                "phi2": 0.0,
                "faction": z.faction,
                "destruction": str(z.destruction),
                "density": z.density,
                "type": getattr(z, "zone_type", None) or getattr(z, "type", None) or "military_base",
            }
            for z in zones
        ]
    else:
        zones, zone_internal_data = generate_zones(
            heightmap=eroded_heightmap,
            terrain_config=terrain_config,
            zone_config=zone_config,
            seed=uint_seed,
        )
    t_zones = time.perf_counter() - t0

    # 4. Plateau Footprint Flattening (Smooth non-linear falloff)
    t0 = time.perf_counter()
    flattened_heightmap = flatten_zone_footprints(
        heightmap=eroded_heightmap,
        zones=zones,
        zone_internal_data=zone_internal_data,
        terrain_config=terrain_config,
    )
    t_flatten = time.perf_counter() - t0

    # 5. SAT Oriented Bounding Box Building Placement (Templated AI layout)
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
    roads = []
    do_roads = getattr(terrain_config, "generate_roads", True)
    if hasattr(request, "generate_roads") and request.generate_roads is not None:
        do_roads = request.generate_roads

    if do_roads:
        roads = generate_roads(
            heightmap=flattened_heightmap,
            zones=zones,
            terrain_config=terrain_config,
            seed=uint_seed,
        )
    t_roads = time.perf_counter() - t0

    # 7. Adaptive Mesh Decimation
    t0 = time.perf_counter()
    decimated_mesh = generate_adaptive_mesh(
        heightmap=flattened_heightmap,
        world_size=terrain_config.world_size,
        max_error=getattr(terrain_config, "adaptive_mesh_max_error", 1.0) or 1.0,
    )
    t_mesh = time.perf_counter() - t0

    total_time = time.perf_counter() - start_time

    # Calculate grid cell size
    res = terrain_config.resolution
    world_w = terrain_config.world_size[0]
    world_h = terrain_config.world_size[1]
    world_l = terrain_config.world_size[2]
    cell_size = float(world_w / max(1, res - 1))

    # Construct final WorldManifest model
    metadata = ManifestMetadata(
        version="2.0.0",
        seed=effective_seed,
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        generator="FastAPI Procedural WorldGen v2.0",
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
        mesh=decimated_mesh,
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
            "adaptive_mesh_decimation_s": round(t_mesh, 4),
        },
        "metrics": {
            "resolution": res,
            "zone_count": len(zones),
            "building_count": len(buildings),
            "road_count": len(roads),
            "mesh_vertex_count": decimated_mesh.vertex_count,
            "mesh_triangle_count": decimated_mesh.triangle_count,
            "decimation_ratio": decimated_mesh.decimation_ratio,
            "min_height": round(float(np.min(flattened_heightmap)), 2),
            "max_height": round(float(np.max(flattened_heightmap)), 2),
        },
    }

    return manifest, flattened_heightmap, summary
