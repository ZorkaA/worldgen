import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

replacement = """    
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
"""

content = content.replace("""    # 4. Clip natural terrain so it never exceeds the max_slope from the city edge
    # This pushes the "cliff" backward into the mountain into a natural ramp!
    flattened = np.clip(flattened, min_allowed_h, max_allowed_h)

    # 5. Smooth the mathematically sharp corners
    smoothed = scipy.ndimage.gaussian_filter(flattened, sigma=1.5)""", replacement)

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Added terrain noise to ramps")
