"""Bridson's 2D Poisson-Disc Zone Distribution and Plateau Height Flattening."""

import math
import numpy as np
import scipy.ndimage
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
    rng = np.random.RandomState(int(seed) & 0x7FFFFFFF)

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
    u = (world_x / max(1e-4, world_width)) * (res_x - 1)
    v = (world_z / max(1e-4, world_length)) * (res_y - 1)

    # Strictly clamp to grid boundary to eliminate extrapolation overshoot
    u_clamped = max(0.0, min(float(res_x - 1), u))
    v_clamped = max(0.0, min(float(res_y - 1), v))

    ix = max(0, min(res_x - 2, int(math.floor(u_clamped))))
    iy = max(0, min(res_y - 2, int(math.floor(v_clamped))))

    fu = max(0.0, min(1.0, u_clamped - ix))
    fv = max(0.0, min(1.0, v_clamped - iy))

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

    rng = np.random.RandomState((int(seed) + 200) & 0x7FFFFFFF)

    world_w = terrain_config.world_size[0]
    world_l = terrain_config.world_size[2]

    # Margin constraint (enforcing edge_margin)
    configured_margin = getattr(zone_config, "edge_margin", None)
    if configured_margin is None:
        configured_margin = getattr(terrain_config, "edge_margin", 80.0)
    effective_margin = max(float(configured_margin), zone_config.max_radius + 15.0)

    # Sample zone centers
    raw_centers = _poisson_disc_sampling(
        width=world_w,
        length=world_l,
        r_min=zone_config.min_zone_distance,
        margin=effective_margin,
        seed=(int(seed) + 300) & 0x7FFFFFFF,
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

        if zone_config.density is not None:
            if isinstance(zone_config.density, (float, int)):
                density = float(zone_config.density)
            else:
                density = str(zone_config.density)
        else:
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
            zone_type=z_type,
            faction=str(faction),
            destruction=destruction_str,
            density=density,
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
    zone_internal_data: Optional[List[Dict[str, Any]]],
    terrain_config: TerrainConfig,
) -> np.ndarray:
    """Flatten plateau heightmap using Distance Transform and adaptive cut-and-fill grading."""
    res_y, res_x = heightmap.shape
    world_w = terrain_config.world_size[0]
    world_l = terrain_config.world_size[2]
    
    cell_w = world_w / max(1, res_x - 1)
    cell_l = world_l / max(1, res_y - 1)

    flattened = heightmap.copy()
    target_heights = np.zeros_like(flattened)
    is_flat_mask = np.zeros((res_y, res_x), dtype=bool)

    # Precalculate world coordinate grid
    xs = np.linspace(0.0, world_w, res_x, dtype=np.float32)
    zs = np.linspace(0.0, world_l, res_y, dtype=np.float32)
    grid_x, grid_z = np.meshgrid(xs, zs)

    for i, zone in enumerate(zones):
        if zone_internal_data and i < len(zone_internal_data):
            meta = zone_internal_data[i]
            cx = meta.get("center_x", zone.center[0])
            cz = meta.get("center_z", zone.center[2])
            base_r = meta.get("radius", zone.radius)
            phi1 = meta.get("phi1", 0.0)
            phi2 = meta.get("phi2", 0.0)
        else:
            cx = zone.center[0]
            cz = zone.center[2]
            base_r = zone.radius
            phi1 = 0.0
            phi2 = 0.0

        dx_grid = grid_x - cx
        dz_grid = grid_z - cz
        dist_grid = np.sqrt(dx_grid * dx_grid + dz_grid * dz_grid)
        theta_grid = np.arctan2(dz_grid, dx_grid)

        # Deformed radius field
        r_inner = base_r * (1.0 + 0.15 * np.sin(3.0 * theta_grid + phi1) + 0.10 * np.cos(5.0 * theta_grid + phi2))
        inner_mask = dist_grid <= r_inner

        if not np.any(inner_mask):
            continue

        zone_elevations = flattened[inner_mask]
        min_elev = float(np.min(zone_elevations))
        max_elev = float(np.max(zone_elevations))
        median_elev = float(np.median(zone_elevations))
        
        # Update zone center elevation in zone object for buildings
        zone.center[1] = round(median_elev, 2)

        is_flat_mask[inner_mask] = True
        
        # Terracing threshold: if elevation variance across the footprint > 15m, apply terracing
        if (max_elev - min_elev) > 15.0:
            terrace_step = 20.0 # 20 meter vertical steps (wider horizontal plateaus)
            # Calculate terraced heights for the inner mask based on original terrain
            stepped = np.round((flattened[inner_mask] - median_elev) / terrace_step) * terrace_step + median_elev
            target_heights[inner_mask] = stepped
        else:
            target_heights[inner_mask] = median_elev

    if not np.any(is_flat_mask):
        return flattened

    # Apply Target Heights
    flattened[is_flat_mask] = target_heights[is_flat_mask]

    # Adaptive Cut-and-Fill Grading via Distance Transform
    # 1. Calculate distance from every pixel to the nearest flat zone, and get indices
    D, indices = scipy.ndimage.distance_transform_edt(
        ~is_flat_mask, 
        sampling=[cell_l, cell_w],
        return_indices=True
    )
    
    # 2. Look up the flat elevation of the nearest edge pixel
    nearest_flat_h = target_heights[indices[0], indices[1]]
    
    # Smooth the target heights to eliminate Voronoi boundary "gashes" 
    # created by the discrete terrace steps projecting radially outward.
    nearest_flat_h_smoothed = scipy.ndimage.gaussian_filter(nearest_flat_h, sigma=2.5)
    nearest_flat_h = np.where(is_flat_mask, target_heights, nearest_flat_h_smoothed)
    
    # 3. Apply maximum allowable slope with parabolic curvature
    # The further from the city, the steeper the allowed slope, so the ramp curves naturally 
    # to intersect the mountain instead of shooting out infinitely.
    max_slope = getattr(terrain_config, "max_road_slope", 0.25) or 0.25
    max_slope = max(0.15, max_slope)
    
    curvature = 0.025 # steeper curvature so the ramp terminates quickly into natural terrain
    drop = D * max_slope + (D ** 2) * curvature
    
    min_allowed_h = nearest_flat_h - drop
    max_allowed_h = nearest_flat_h + drop

    
    
    # 4. Clip natural terrain so it never exceeds the max_slope from the city edge
    # This pushes the "cliff" backward into the mountain into a natural ramp!
    clipped_h = np.clip(flattened, min_allowed_h, max_allowed_h)

    # 4b. To make the ramp look natural, re-inject the high-frequency detail (roughness) of the original terrain!
    # original high frequency = original - smooth(original)
    smoothed_orig = scipy.ndimage.gaussian_filter(flattened, sigma=5.0)
    high_freq_noise = flattened - smoothed_orig
    
    # Apply noise only to areas that were significantly modified (the artificial ramp)
    # The more it was clipped, the more we want to retain the original's texture.
    diff = np.abs(clipped_h - flattened)
    noise_mask = np.clip(diff / 5.0, 0.0, 1.0)
    
    flattened = clipped_h + high_freq_noise * noise_mask * 0.8
    
    # Optional: Parabolic curvature to prevent ramps from extending infinitely.
    # At D=0, allowed slope is max_slope. As D increases, the allowed slope becomes steeper, 
    # forcing it to merge with the mountain faster.
    # We did that simply by adding noise, which makes it look less like an artificial pyramid.
    # But let's also restrict the distance transform by curving the limit:
    # We can actually just let the noise do the visual work first.

    # 5. Smooth the mathematically sharp corners
    smoothed = scipy.ndimage.gaussian_filter(flattened, sigma=1.5)

    
    # Blend smoothed result heavily near the boundary (Distance < 15m) to round off sharp cuts
    # D == 0 (inside zone): full sharp target height to keep it flat
    # D > 0: blend with smooth to soften the retaining walls
    blend_factor = np.clip(D / 15.0, 0.0, 1.0)
    
    # For distance > 15m, it becomes 100% the clipped terrain (blend_factor=1)
    # Inside the zone (D=0), we don't want it smoothed so buildings sit perfectly flat (blend_factor=1 for original target? No wait, if blend_factor=0, we should use flattened)
    # Actually, we ONLY want to smooth the gradient transitions, not the whole map.
    # The gaussian filter softens everything. We just want to use the smoothed map near D < 15m and D > 0.
    
    # Create an edge mask: 1.0 near edge (D < 10), 0.0 far away
    # D is distance outside the zone (0 inside)
    edge_mask_out = np.exp(-(D ** 2) / (2.0 * 8.0 ** 2))
    
    # D_in is distance inside the zone (0 outside)
    D_in = scipy.ndimage.distance_transform_edt(is_flat_mask, sampling=[cell_l, cell_w])
    edge_mask_in = np.exp(-(D_in ** 2) / (2.0 * 6.0 ** 2))
    
    # We only want edge_mask_in to apply INSIDE the zone, and edge_mask_out OUTSIDE.
    # Since D=0 inside, edge_mask_out=1 inside. Since D_in=0 outside, edge_mask_in=1 outside.
    # We mask them so they only apply to their respective domains!
    edge_mask = np.where(is_flat_mask, edge_mask_in, edge_mask_out)
    
    final_terrain = flattened * (1.0 - edge_mask) + smoothed * edge_mask

    return final_terrain.astype(np.float32)
