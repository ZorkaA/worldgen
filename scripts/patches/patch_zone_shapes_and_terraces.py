import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

# 1. Unique phi1 and phi2
old_phi = """        if zone_internal_data and i < len(zone_internal_data):
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
            phi2 = 0.0"""

new_phi = """        if zone_internal_data and i < len(zone_internal_data):
            meta = zone_internal_data[i]
            cx = meta.get("center_x", zone.center[0])
            cz = meta.get("center_z", zone.center[2])
            base_r = meta.get("radius", zone.radius)
            phi1 = meta.get("phi1") if meta.get("phi1") is not None else (cx * 0.137) % (2 * 3.14159)
            phi2 = meta.get("phi2") if meta.get("phi2") is not None else (cz * 0.219) % (2 * 3.14159)
        else:
            cx = zone.center[0]
            cz = zone.center[2]
            base_r = zone.radius
            phi1 = (cx * 0.137) % (2 * 3.14159)
            phi2 = (cz * 0.219) % (2 * 3.14159)"""

content = content.replace(old_phi, new_phi)


# 2. Smooth macro contours for terracing
old_terracing = """        # Terracing threshold: if elevation variance across the footprint > 15.0m, apply terracing
        if (max_elev - min_elev) > 15.0:
            terrace_step = 20.0 # 20 meter vertical steps (wider horizontal plateaus)
            # Calculate terraced heights for the inner mask based on original terrain
            stepped = np.round((flattened[inner_mask] - median_elev) / terrace_step) * terrace_step + median_elev
            target_heights[inner_mask] = stepped
        else:
            target_heights[inner_mask] = median_elev"""

new_terracing = """        # Terracing threshold: if elevation variance across the footprint > 15.0m, apply terracing
        if (max_elev - min_elev) > 15.0:
            terrace_step = 12.0 # 12 meter vertical steps
            # To get sweeping cohesive plateaus rather than fragmented pillars, 
            # we must terrace based on the SMOOTHED macro-terrain, ignoring high-frequency noise.
            # We create a local smoothed patch for the zone.
            y_min, y_max = max(0, int(cz - base_r - 20)), min(res_y, int(cz + base_r + 20))
            x_min, x_max = max(0, int(cx - base_r - 20)), min(res_x, int(cx + base_r + 20))
            local_patch = flattened[y_min:y_max, x_min:x_max]
            smoothed_patch = scipy.ndimage.gaussian_filter(local_patch, sigma=10.0)
            
            # Create a full-size macro_terrain array padded with the original terrain
            macro_terrain = flattened.copy()
            macro_terrain[y_min:y_max, x_min:x_max] = smoothed_patch
            
            # Calculate terraced heights based on the macro contours!
            stepped = np.round((macro_terrain[inner_mask] - median_elev) / terrace_step) * terrace_step + median_elev
            target_heights[inner_mask] = stepped
        else:
            target_heights[inner_mask] = median_elev"""

content = content.replace(old_terracing, new_terracing)

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Patched zone shapes and macro terracing")
