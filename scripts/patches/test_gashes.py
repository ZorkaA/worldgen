import numpy as np
import scipy.ndimage

res = 200
cell = 5.0
heightmap = np.zeros((res, res))
is_flat = np.zeros((res, res), dtype=bool)

# Create a stepped edge
target_h = np.zeros((res, res))
for i in range(res):
    for j in range(res):
        if i < 100:
            is_flat[i, j] = True
            # Step every 20 pixels
            target_h[i, j] = (j // 20) * 8.0
            heightmap[i, j] = target_h[i, j]

D, indices = scipy.ndimage.distance_transform_edt(
    ~is_flat, 
    return_indices=True
)

nearest_flat_h = target_h[indices[0], indices[1]]

# The problem: nearest_flat_h has sharp steps in the ~is_flat region
print("Before smoothing, step difference at boundary D=10:", nearest_flat_h[110, 39] - nearest_flat_h[110, 41])

# If we smooth nearest_flat_h
smoothed_nearest = scipy.ndimage.gaussian_filter(nearest_flat_h, sigma=5.0)
print("After smoothing sigma 5, step difference at D=10:", smoothed_nearest[110, 39] - smoothed_nearest[110, 41])

