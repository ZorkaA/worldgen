import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

old_terracing = """        # Terracing threshold: if elevation variance across the footprint > 15m, apply terracing
        if (max_elev - min_elev) > 15.0:
            terrace_step = 20.0 # 20 meter vertical steps (wider horizontal plateaus)
            # Calculate terraced heights for the inner mask based on original terrain
            stepped = np.round((flattened[inner_mask] - median_elev) / terrace_step) * terrace_step + median_elev
            target_heights[inner_mask] = stepped
        else:
            target_heights[inner_mask] = median_elev"""

new_terracing = """        # Terracing threshold: if elevation variance across the footprint > 15m, apply terracing
        if (max_elev - min_elev) > 15.0:
            terrace_step = 12.0 # 12 meter vertical steps
            # To get sweeping cohesive plateaus rather than fragmented pillars, 
            # we must terrace based on the SMOOTHED macro-terrain, ignoring high-frequency noise.
            # We create a local smoothed patch for the zone.
            y_min, y_max = max(0, int((cz - base_r - 20) / cell_l)), min(res_y, int((cz + base_r + 20) / cell_l))
            x_min, x_max = max(0, int((cx - base_r - 20) / cell_w)), min(res_x, int((cx + base_r + 20) / cell_w))
            local_patch = flattened[y_min:y_max, x_min:x_max]
            
            if local_patch.size > 0:
                smoothed_patch = scipy.ndimage.gaussian_filter(local_patch, sigma=15.0)
                macro_terrain = flattened.copy()
                macro_terrain[y_min:y_max, x_min:x_max] = smoothed_patch
            else:
                macro_terrain = scipy.ndimage.gaussian_filter(flattened, sigma=15.0)
            
            # Calculate terraced heights based on the macro contours!
            stepped = np.round((macro_terrain[inner_mask] - median_elev) / terrace_step) * terrace_step + median_elev
            target_heights[inner_mask] = stepped
        else:
            target_heights[inner_mask] = median_elev"""

content = content.replace(old_terracing, new_terracing)

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Patched terracing properly")
