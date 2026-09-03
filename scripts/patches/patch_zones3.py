import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

replacement = """    
    # 3. Apply maximum allowable slope with parabolic curvature
    # The further from the city, the steeper the allowed slope, so the ramp curves naturally 
    # to intersect the mountain instead of shooting out infinitely.
    max_slope = getattr(terrain_config, "max_road_slope", 0.25) or 0.25
    max_slope = max(0.15, max_slope)
    
    curvature = 0.003 # steepens by 0.3% per meter
    drop = D * max_slope + (D ** 2) * curvature
    
    min_allowed_h = nearest_flat_h - drop
    max_allowed_h = nearest_flat_h + drop
"""

content = content.replace("""    # 3. Apply maximum allowable slope (e.g. 22% grade)
    max_slope = getattr(terrain_config, "max_road_slope", 0.25) or 0.25
    max_slope = max(0.15, max_slope) # ensure it doesn't get too flat
    
    min_allowed_h = nearest_flat_h - D * max_slope
    max_allowed_h = nearest_flat_h + D * max_slope""", replacement)

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Added curvature to ramps")
