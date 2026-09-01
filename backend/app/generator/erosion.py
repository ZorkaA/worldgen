"""High-Performance Numba JIT Hydraulic Droplet Erosion Simulation."""

import math
import numpy as np
from numba import njit


@njit(fastmath=True)
def _sample_height_and_gradient(
    heightmap: np.ndarray,
    x: float,
    y: float,
    rows: int,
    cols: int,
):
    """Bilinear height and gradient calculation."""
    ix = int(math.floor(x))
    iy = int(math.floor(y))

    if ix < 0:
        ix = 0
    elif ix >= cols - 1:
        ix = cols - 2

    if iy < 0:
        iy = 0
    elif iy >= rows - 1:
        iy = rows - 2

    u = x - ix
    v = y - iy

    h00 = heightmap[iy, ix]
    h10 = heightmap[iy, ix + 1]
    h01 = heightmap[iy + 1, ix]
    h11 = heightmap[iy + 1, ix + 1]

    gx = (h10 - h00) * (1.0 - v) + (h11 - h01) * v
    gy = (h01 - h00) * (1.0 - u) + (h11 - h10) * u
    h = h00 * (1.0 - u) * (1.0 - v) + h10 * u * (1.0 - v) + h01 * (1.0 - u) * v + h11 * u * v

    return h, gx, gy, ix, iy, u, v


@njit(fastmath=True)
def _erode_kernel(
    heightmap: np.ndarray,
    num_droplets: int,
    seed: int,
    inertia: float = 0.05,
    capacity_factor: float = 4.0,
    min_slope: float = 0.01,
    erosion_rate: float = 0.3,
    deposition_rate: float = 0.3,
    evaporation_rate: float = 0.015,
    gravity: float = 4.0,
    max_lifetime: int = 40,
):
    """Core Numba JIT loop for droplet hydraulic erosion."""
    rows, cols = heightmap.shape
    np.random.seed(int(seed) & 0x7FFFFFFF)

    # Pre-generate random initial positions
    start_xs = np.random.uniform(1.0, float(cols - 2), num_droplets)
    start_ys = np.random.uniform(1.0, float(rows - 2), num_droplets)

    for d in range(num_droplets):
        px = start_xs[d]
        py = start_ys[d]
        dir_x = 0.0
        dir_y = 0.0
        speed = 1.0
        water = 1.0
        sediment = 0.0

        for _ in range(max_lifetime):
            h, gx, gy, ix, iy, u, v = _sample_height_and_gradient(heightmap, px, py, rows, cols)

            # Update direction with momentum / inertia
            dir_x = dir_x * inertia - gx * (1.0 - inertia)
            dir_y = dir_y * inertia - gy * (1.0 - inertia)
            d_len = math.sqrt(dir_x * dir_x + dir_y * dir_y)

            if d_len > 1e-6:
                dir_x /= d_len
                dir_y /= d_len
            else:
                # Flat terrain, random perturbation
                ang = np.random.uniform(0.0, 2.0 * math.pi)
                dir_x = math.cos(ang)
                dir_y = math.sin(ang)

            new_px = px + dir_x
            new_py = py + dir_y

            # Check boundaries
            if new_px < 1.0 or new_px >= cols - 2 or new_py < 1.0 or new_py >= rows - 2:
                # Droplet leaves domain; deposit any remaining sediment and terminate
                w00 = (1.0 - u) * (1.0 - v)
                w10 = u * (1.0 - v)
                w01 = (1.0 - u) * v
                w11 = u * v
                heightmap[iy, ix] += sediment * w00
                heightmap[iy, ix + 1] += sediment * w10
                heightmap[iy + 1, ix] += sediment * w01
                heightmap[iy + 1, ix + 1] += sediment * w11
                break

            new_h, _, _, _, _, _, _ = _sample_height_and_gradient(heightmap, new_px, new_py, rows, cols)
            dh = new_h - h

            # Sediment capacity
            capacity = max(-dh, min_slope) * speed * water * capacity_factor

            # Bilinear weights for deposit/erode
            w00 = (1.0 - u) * (1.0 - v)
            w10 = u * (1.0 - v)
            w01 = (1.0 - u) * v
            w11 = u * v

            if sediment > capacity or dh > 0.0:
                # Oversaturated or moving uphill -> deposit
                if dh > 0.0:
                    deposit_amt = min(sediment, dh)
                else:
                    deposit_amt = (sediment - capacity) * deposition_rate

                sediment -= deposit_amt
                heightmap[iy, ix] += deposit_amt * w00
                heightmap[iy, ix + 1] += deposit_amt * w10
                heightmap[iy + 1, ix] += deposit_amt * w01
                heightmap[iy + 1, ix + 1] += deposit_amt * w11
            else:
                # Undersaturated -> erode
                erode_amt = min((capacity - sediment) * erosion_rate, -dh)
                sediment += erode_amt
                heightmap[iy, ix] -= erode_amt * w00
                heightmap[iy, ix + 1] -= erode_amt * w10
                heightmap[iy + 1, ix] -= erode_amt * w01
                heightmap[iy + 1, ix + 1] -= erode_amt * w11

            # Kinematic acceleration and evaporation
            speed_sq = speed * speed + dh * gravity
            if speed_sq < 0.0:
                speed = 0.0
            else:
                speed = math.sqrt(speed_sq)

            water *= (1.0 - evaporation_rate)
            px = new_px
            py = new_py

            if speed < 1e-4 or water < 1e-4:
                # Deposit remaining sediment
                heightmap[iy, ix] += sediment * w00
                heightmap[iy, ix + 1] += sediment * w10
                heightmap[iy + 1, ix] += sediment * w01
                heightmap[iy + 1, ix + 1] += sediment * w11
                break


def simulate_hydraulic_erosion(
    heightmap: np.ndarray,
    droplets: int = 50000,
    seed: int = 42,
    inertia: float = 0.05,
    capacity_factor: float = 4.0,
    min_slope: float = 0.01,
    erosion_rate: float = 0.3,
    deposition_rate: float = 0.3,
    evaporation_rate: float = 0.015,
    gravity: float = 4.0,
    max_lifetime: int = 40,
) -> np.ndarray:
    """Run hydraulic erosion on a copy of the input heightmap.

    Returns the eroded float32 heightmap.
    """
    if droplets <= 0:
        return heightmap.copy()

    eroded = heightmap.astype(np.float32, copy=True)
    _erode_kernel(
        eroded,
        droplets,
        seed,
        inertia=inertia,
        capacity_factor=capacity_factor,
        min_slope=min_slope,
        erosion_rate=erosion_rate,
        deposition_rate=deposition_rate,
        evaporation_rate=evaporation_rate,
        gravity=gravity,
        max_lifetime=max_lifetime,
    )
    return eroded
