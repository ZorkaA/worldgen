import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

# Revert threshold to 15
content = content.replace("if (max_elev - min_elev) > 28.0:", "if (max_elev - min_elev) > 15.0:")

# Update sigma to 2.5
content = content.replace("nearest_flat_h_smoothed = scipy.ndimage.gaussian_filter(nearest_flat_h, sigma=5.0)", "nearest_flat_h_smoothed = scipy.ndimage.gaussian_filter(nearest_flat_h, sigma=2.5)")

# Update curvature to 0.025
content = content.replace("curvature = 0.003 # steepens by 0.3% per meter", "curvature = 0.025 # steeper curvature so the ramp terminates quickly into natural terrain")

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Patched zones.py curvature and threshold")
