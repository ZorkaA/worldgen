import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

# Make sure to import scipy.ndimage
if "import scipy.ndimage" not in content:
    content = content.replace("import numpy as np", "import numpy as np\nimport scipy.ndimage")

new_flatten_function = """def flatten_zone_footprints(
    heightmap: np.ndarray,
    zones: List[Zone],
    zone_internal_data: Optional[List[Dict[str, Any]]],
    terrain_config: TerrainConfig,
) -> np.ndarray:
    \"\"\"Flatten plateau heightmap using Distance Transform and adaptive cut-and-fill grading.\"\"\"
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
            terrace_step = 8.0 # 8 meter vertical steps
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
    
    # 3. Apply maximum allowable slope (e.g. 22% grade)
    max_slope = getattr(terrain_config, "max_road_slope", 0.25) or 0.25
    max_slope = max(0.15, max_slope) # ensure it doesn't get too flat
    
    min_allowed_h = nearest_flat_h - D * max_slope
    max_allowed_h = nearest_flat_h + D * max_slope
    
    # 4. Clip natural terrain so it never exceeds the max_slope from the city edge
    # This pushes the "cliff" backward into the mountain into a natural ramp!
    flattened = np.clip(flattened, min_allowed_h, max_allowed_h)

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
    
    # Let's create an edge mask: 1.0 near edge (D < 10), 0.0 far away
    edge_mask = np.exp(-(D ** 2) / (2.0 * 8.0 ** 2)) 
    # Add inner edge smoothing too (inside the zone, D is 0, so edge_mask is 1.0)
    # We need inner distance
    D_in = scipy.ndimage.distance_transform_edt(is_flat_mask, sampling=[cell_l, cell_w])
    inner_edge_mask = np.exp(-(D_in ** 2) / (2.0 * 6.0 ** 2))
    
    total_edge_mask = np.maximum(edge_mask, inner_edge_mask)
    
    final_terrain = flattened * (1.0 - total_edge_mask) + smoothed * total_edge_mask

    return final_terrain.astype(np.float32)
"""

# Replace the function
import re
pattern = re.compile(r"def flatten_zone_footprints\(.*?\)\s*->\s*np\.ndarray:.*?return flattened", re.DOTALL)
if pattern.search(content):
    content = pattern.sub(new_flatten_function.strip(), content)
    with open("backend/app/generator/zones.py", "w") as f:
        f.write(content)
    print("Patched zones.py")
else:
    print("Could not find flatten_zone_footprints in zones.py")
