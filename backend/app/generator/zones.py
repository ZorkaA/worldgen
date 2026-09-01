"""Bridson's 2D Poisson-Disc Zone Distribution and Plateau Height Flattening."""

import math
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from ..core.schemas import Zone, ZoneConfig, TerrainConfig


NATO_PHONETIC = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel",
    "India", "Juliett", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa",
    "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "X-Ray",
    "Yankee", "Zulu"
]

ZONE_TYPE_NAMES = {
    "military_base": "Military Base",
    "outpost": "Forward Outpost",
    "airfield": "Airfield Command",
    "depot": "Supply Depot",
    "radar_station": "Radar Station",
}

ZONE_TYPE_PROBS = [
    ("military_base", 0.25),
    ("outpost", 0.35),
    ("airfield", 0.10),
    ("depot", 0.20),
    ("radar_station", 0.10),
]


def _poisson_disc_sampling(
    width: float,
    length: float,
    r_min: float,
    margin: float = 80.0,
    k: int = 30,
    seed: int = 42,
    target_count: Optional[int] = None,
) -> List[Tuple[float, float]]:
    """Bridson's 2D Poisson-disc sampling algorithm."""
    rng = np.random.RandomState(seed)

    min_x, max_x = margin, width - margin
    min_z, max_z = margin, length - margin

    if max_x <= min_x or max_z <= min_z:
        min_x, max_x = 0.1 * width, 0.9 * width
        min_z, max_z = 0.1 * length, 0.9 * length

    w_eff = max_x - min_x
    l_eff = max_z - min_z

    cell_size = r_min / math.sqrt(2)
    grid_w = int(math.ceil(w_eff / cell_size))
    grid_h = int(math.ceil(l_eff / cell_size))

    grid = np.full((grid_h, grid_w), -1, dtype=np.int32)
    points: List[Tuple[float, float]] = []
    active_list: List[int] = []

    # Initial seed point
    first_x = min_x + rng.uniform(0.2 * w_eff, 0.8 * w_eff)
    first_z = min_z + rng.uniform(0.2 * l_eff, 0.8 * l_eff)
    points.append((first_x, first_z))
    gx = min(int((first_x - min_x) / cell_size), grid_w - 1)
    gz = min(int((first_z - min_z) / cell_size), grid_h - 1)
    grid[gz, gx] = 0
    active_list.append(0)

    r_min_sq = r_min * r_min

    while active_list:
        rand_idx = rng.randint(0, len(active_list))
        point_idx = active_list[rand_idx]
        px, pz = points[point_idx]
        found = False

        for _ in range(k):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            dist = rng.uniform(r_min, 2.0 * r_min)
            cand_x = px + dist * math.cos(angle)
            cand_z = pz + dist * math.sin(angle)

            if not (min_x <= cand_x <= max_x and min_z <= cand_z <= max_z):
                continue

            cgx = int((cand_x - min_x) / cell_size)
            cgz = int((cand_z - min_z) / cell_size)

            if cgx < 0 or cgx >= grid_w or cgz < 0 or cgz >= grid_h:
                continue

            # Check 5x5 neighborhood in background grid
            conflict = False
            g_min_x = max(0, cgx - 2)
            g_max_x = min(grid_w - 1, cgx + 2)
            g_min_z = max(0, cgz - 2)
            g_max_z = min(grid_h - 1, cgz + 2)

            for gz_scan in range(g_min_z, g_max_z + 1):
                for gx_scan in range(g_min_x, g_max_x + 1):
                    neighbor_idx = grid[gz_scan, gx_scan]
                    if neighbor_idx >= 0:
                        nx, nz = points[neighbor_idx]
                        d_sq = (cand_x - nx) ** 2 + (cand_z - nz) ** 2
                        if d_sq < r_min_sq:
                            conflict = True
                            break
                if conflict:
                    break

            if not conflict:
                new_idx = len(points)
                points.append((cand_x, cand_z))
                grid[cgz, cgx] = new_idx
                active_list.append(new_idx)
                found = True
                if target_count is not None and len(points) >= target_count:
                    return points[:target_count]
                break

        if not found:
            active_list.pop(rand_idx)

    if target_count is not None and len(points) < target_count:
        # If Poisson disc produced fewer than desired, backfill with relaxed distance
        while len(points) < target_count:
            bx = min_x + rng.uniform(0.0, w_eff)
            bz = min_z + rng.uniform(0.0, l_eff)
            # Find closest
            min_d = min((bx - px)**2 + (bz - pz)**2 for px, pz in points)
            if min_d > (0.4 * r_min) ** 2:
                points.append((bx, bz))

    return points


def _sample_heightmap_bilinear(
    heightmap: np.ndarray,
    world_x: float,
    world_z: float,
    world_width: float,
    world_length: float,
) -> float:
    """Sample continuous world-space coordinate (x, z) from heightmap."""
    res_y, res_x = heightmap.shape
    u = (world_x / world_width) * (res_x - 1)
    v = (world_z / world_length) * (res_y - 1)

    ix = int(math.floor(u))
    iy = int(math.floor(v))

    ix = max(0, min(res_x - 2, ix))
    iy = max(0, min(res_y - 2, iy))

    fu = u - ix
    fv = v - iy

    h00 = heightmap[iy, ix]
    h10 = heightmap[iy, ix + 1]
    h01 = heightmap[iy + 1, ix]
    h11 = heightmap[iy + 1, ix + 1]

    return float((1.0 - fu) * (1.0 - fv) * h00 + fu * (1.0 - fv) * h10 + (1.0 - fu) * fv * h01 + fu * fv * h11)


def generate_zone_footprint_polygon(
    center_x: float,
    center_z: float,
    base_radius: float,
    phi1: float,
    phi2: float,
    num_samples: int = 24,
) -> List[List[float]]:
    """Compute organic deformed radial boundary polygon for a zone:
    R(theta) = base_radius * (1.0 + 0.15*sin(3*theta + phi1) + 0.10*cos(5*theta + phi2))
    """
    polygon: List[List[float]] = []
    for k in range(num_samples):
        theta = (2.0 * math.pi * k) / num_samples
        r = base_radius * (1.0 + 0.15 * math.sin(3.0 * theta + phi1) + 0.10 * math.cos(5.0 * theta + phi2))
        px = center_x + r * math.cos(theta)
        pz = center_z + r * math.sin(theta)
        polygon.append([round(px, 3), round(pz, 3)])
    return polygon


def generate_zones(
    heightmap: np.ndarray,
    terrain_config: TerrainConfig,
    zone_config: Optional[ZoneConfig] = None,
    seed: int = 42,
) -> Tuple[List[Zone], List[Dict[str, Any]]]:
    """Generate military zones using 2D Poisson-disc sampling.

    Returns:
        zones: List of Zone schema models
        zone_internal_data: List of internal dicts with extra mathematical params for plateau blending
    """
    if zone_config is None:
        zone_config = ZoneConfig()

    rng = np.random.RandomState(seed + 200)

    world_w = terrain_config.world_size[0]
    world_l = terrain_config.world_size[2]

    # Sample zone centers
    raw_centers = _poisson_disc_sampling(
        width=world_w,
        length=world_l,
        r_min=zone_config.min_zone_distance,
        margin=max(60.0, zone_config.max_radius + 20.0),
        seed=seed + 300,
        target_count=zone_config.zone_count_target,
    )

    types = [t for t, _ in ZONE_TYPE_PROBS]
    probs = [p for _, p in ZONE_TYPE_PROBS]

    zones: List[Zone] = []
    zone_internal_data: List[Dict[str, Any]] = []

    for i, (cx, cz) in enumerate(raw_centers):
        zone_id = f"zone_{i}"
        nato_name = NATO_PHONETIC[i % len(NATO_PHONETIC)]
        z_type = rng.choice(types, p=probs)
        type_title = ZONE_TYPE_NAMES.get(z_type, "Compound")
        name = f"{type_title} {nato_name}"

        faction = rng.choice(zone_config.default_factions)
        destruction_int = int(rng.randint(1, zone_config.max_destruction + 1))
        destruction_str = f"{destruction_int:02d}"

        density = rng.choice(["low", "medium", "high"], p=[0.25, 0.50, 0.25])
        radius = float(rng.uniform(zone_config.min_radius, zone_config.max_radius))

        phi1 = float(rng.uniform(0.0, 2.0 * math.pi))
        phi2 = float(rng.uniform(0.0, 2.0 * math.pi))

        footprint_poly = generate_zone_footprint_polygon(cx, cz, radius, phi1, phi2, num_samples=24)

        # Sample initial center height
        cy = _sample_heightmap_bilinear(heightmap, cx, cz, world_w, world_l)

        zone_obj = Zone(
            id=zone_id,
            name=name,
            type=z_type,
            faction=str(faction),
            destruction=destruction_str,
            density=str(density),
            center=[round(cx, 2), round(cy, 2), round(cz, 2)],
            radius=round(radius, 2),
            footprint_points=footprint_poly,
            footprint_polygon=footprint_poly,
        )
        zones.append(zone_obj)

        zone_internal_data.append({
            "id": zone_id,
            "center_x": cx,
            "center_z": cz,
            "radius": radius,
            "phi1": phi1,
            "phi2": phi2,
            "faction": faction,
            "destruction": destruction_str,
            "density": density,
            "type": z_type,
        })

    return zones, zone_internal_data


def flatten_zone_footprints(
    heightmap: np.ndarray,
    zones: List[Zone],
    zone_internal_data: List[Dict[str, Any]],
    terrain_config: TerrainConfig,
) -> np.ndarray:
    """Flatten plateau heightmap beneath zones using C1 Hermite smoothstep blending."""
    res_y, res_x = heightmap.shape
    world_w = terrain_config.world_size[0]
    world_l = terrain_config.world_size[2]

    flattened = heightmap.copy()

    # Precalculate world coordinate grid
    xs = np.linspace(0.0, world_w, res_x, dtype=np.float32)
    zs = np.linspace(0.0, world_l, res_y, dtype=np.float32)
    grid_x, grid_z = np.meshgrid(xs, zs)

    for i, zone in enumerate(zones):
        meta = zone_internal_data[i]
        cx = meta["center_x"]
        cz = meta["center_z"]
        base_r = meta["radius"]
        phi1 = meta["phi1"]
        phi2 = meta["phi2"]

        # Find median height inside core footprint
        dx_grid = grid_x - cx
        dz_grid = grid_z - cz
        dist_grid = np.sqrt(dx_grid * dx_grid + dz_grid * dz_grid)
        theta_grid = np.arctan2(dz_grid, dx_grid)

        # Deformed radius field
        r_inner = base_r * (1.0 + 0.15 * np.sin(3.0 * theta_grid + phi1) + 0.10 * np.cos(5.0 * theta_grid + phi2))
        r_outer = r_inner * 1.45

        # Bounding box filter for optimization
        max_reach = base_r * 1.6
        mask_roi = dist_grid <= max_reach

        if not np.any(mask_roi):
            continue

        # Compute median elevation in inner zone
        inner_mask = dist_grid <= r_inner
        if np.any(inner_mask):
            target_elevation = float(np.median(flattened[inner_mask]))
        else:
            target_elevation = _sample_heightmap_bilinear(flattened, cx, cz, world_w, world_l)

        # Update zone center elevation in zone object
        zone.center[1] = round(target_elevation, 2)

        # Smoothstep blending factor t in [0.0, 1.0]
        # t = 0 -> inside inner zone (full target elevation)
        # t = 1 -> outside outer zone (original elevation)
        t = np.clip((dist_grid[mask_roi] - r_inner[mask_roi]) / np.maximum(1e-4, (r_outer[mask_roi] - r_inner[mask_roi])), 0.0, 1.0)
        # Hermite smoothstep w(t) = 3t^2 - 2t^3
        w = t * t * (3.0 - 2.0 * t)

        current_h = flattened[mask_roi]
        blended_h = (1.0 - w) * target_elevation + w * current_h
        flattened[mask_roi] = blended_h.astype(np.float32)

    return flattened
