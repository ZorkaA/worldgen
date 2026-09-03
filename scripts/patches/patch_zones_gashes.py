import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

# 1. Increase terracing threshold
content = content.replace("if (max_elev - min_elev) > 15.0:", "if (max_elev - min_elev) > 28.0:")

# 2. Smooth nearest_flat_h
old_block = """    # 2. Look up the flat elevation of the nearest edge pixel
    nearest_flat_h = target_heights[indices[0], indices[1]]
    
    
    # 3. Apply maximum allowable slope with parabolic curvature"""

new_block = """    # 2. Look up the flat elevation of the nearest edge pixel
    nearest_flat_h = target_heights[indices[0], indices[1]]
    
    # Smooth the target heights to eliminate Voronoi boundary "gashes" 
    # created by the discrete terrace steps projecting radially outward.
    nearest_flat_h_smoothed = scipy.ndimage.gaussian_filter(nearest_flat_h, sigma=5.0)
    nearest_flat_h = np.where(is_flat_mask, target_heights, nearest_flat_h_smoothed)
    
    # 3. Apply maximum allowable slope with parabolic curvature"""

content = content.replace(old_block, new_block)

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Patched gashes in zones.py")
