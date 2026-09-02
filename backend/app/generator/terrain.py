"""Multifractal Perlin Noise and Chained Domain Warping Terrain Generator."""

import numpy as np
from typing import Tuple, Optional
from ..core.schemas import TerrainConfig


def _generate_permutation_table(seed: int) -> np.ndarray:
    """Generate a 512-element permutation table from seed."""
    rng = np.random.RandomState(int(seed) & 0x7FFFFFFF)
    p = np.arange(256, dtype=np.int32)
    rng.shuffle(p)
    return np.tile(p, 2)


def _fade(t: np.ndarray) -> np.ndarray:
    """Quintic polynomial fade curve: 6t^5 - 15t^4 + 10t^3."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _grad(hash_val: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Compute dot product of pseudorandom gradient vector and distance vector."""
    h = hash_val & 7
    # 8 gradient directions: (1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1) / sqrt(2)
    # Using integer bit tricks for speed
    u = np.where(h < 4, x, y)
    v = np.where(h < 4, y, x)
    g1 = np.where((h & 1) == 0, u, -u)
    g2 = np.where((h & 2) == 0, v, -v)
    return g1 + g2


def perlin_noise_2d(
    coords_x: np.ndarray,
    coords_y: np.ndarray,
    perm: np.ndarray,
) -> np.ndarray:
    """Vectorized 2D Perlin gradient noise."""
    xi = np.floor(coords_x).astype(np.int32) & 255
    yi = np.floor(coords_y).astype(np.int32) & 255

    xf = coords_x - np.floor(coords_x)
    yf = coords_y - np.floor(coords_y)

    u = _fade(xf)
    v = _fade(yf)

    aa = perm[perm[xi] + yi]
    ab = perm[perm[xi] + yi + 1]
    ba = perm[perm[xi + 1] + yi]
    bb = perm[perm[xi + 1] + yi + 1]

    g_aa = _grad(aa, xf, yf)
    g_ba = _grad(ba, xf - 1.0, yf)
    g_ab = _grad(ab, xf, yf - 1.0)
    g_bb = _grad(bb, xf - 1.0, yf - 1.0)

    x1 = g_aa + u * (g_ba - g_aa)
    x2 = g_ab + u * (g_bb - g_ab)

    return x1 + v * (x2 - x1)


def fbm_2d(
    coords_x: np.ndarray,
    coords_y: np.ndarray,
    perm: np.ndarray,
    octaves: int = 6,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    base_scale: float = 256.0,
    offsets: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Fractional Brownian Motion (FBM) combining multiple octaves of Perlin noise."""
    total = np.zeros_like(coords_x, dtype=np.float32)
    frequency = 1.0 / max(base_scale, 1e-4)
    amplitude = 1.0
    max_amp = 0.0

    if offsets is None:
        offsets = np.zeros((octaves, 2), dtype=np.float32)

    for i in range(octaves):
        ox = offsets[i, 0]
        oy = offsets[i, 1]
        nx = coords_x * frequency + ox
        ny = coords_y * frequency + oy
        val = perlin_noise_2d(nx, ny, perm)
        total += val * amplitude
        max_amp += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    if max_amp > 0:
        total /= max_amp
    return total


def domain_warped_fbm(
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    perm: np.ndarray,
    octaves: int = 6,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    base_scale: float = 256.0,
    warp_strength: float = 35.0,
    seed: int = 42,
) -> np.ndarray:
    """Chained Domain Warping:
    q(x) = (FBM(x + c_q1), FBM(x + c_q2))
    r(x) = (FBM(x + 4.0*q(x) + c_r1), FBM(x + 4.0*q(x) + c_r2))
    H(x) = FBM(x + warp_strength * r(x))
    """
    rng = np.random.RandomState((int(seed) + 100) & 0x7FFFFFFF)
    octave_offsets = rng.uniform(-1000.0, 1000.0, size=(octaves, 2)).astype(np.float32)

    if warp_strength <= 0.001:
        return fbm_2d(
            grid_x,
            grid_y,
            perm,
            octaves=octaves,
            persistence=persistence,
            lacunarity=lacunarity,
            base_scale=base_scale,
            offsets=octave_offsets,
        )

    # Decorrelation constants
    cq1_x, cq1_y = 0.0, 0.0
    cq2_x, cq2_y = 5.2, 1.3
    cr1_x, cr1_y = 1.7, 9.2
    cr2_x, cr2_y = 8.3, 2.8

    # First warp stage: q
    qx = fbm_2d(
        grid_x + cq1_x * base_scale,
        grid_y + cq1_y * base_scale,
        perm,
        octaves=min(4, octaves),
        persistence=persistence,
        lacunarity=lacunarity,
        base_scale=base_scale,
        offsets=octave_offsets,
    )
    qy = fbm_2d(
        grid_x + cq2_x * base_scale,
        grid_y + cq2_y * base_scale,
        perm,
        octaves=min(4, octaves),
        persistence=persistence,
        lacunarity=lacunarity,
        base_scale=base_scale,
        offsets=octave_offsets,
    )

    # Second warp stage: r
    rx = fbm_2d(
        grid_x + 4.0 * qx * (warp_strength * 0.5) + cr1_x * base_scale,
        grid_y + 4.0 * qy * (warp_strength * 0.5) + cr1_y * base_scale,
        perm,
        octaves=min(4, octaves),
        persistence=persistence,
        lacunarity=lacunarity,
        base_scale=base_scale,
        offsets=octave_offsets,
    )
    ry = fbm_2d(
        grid_x + 4.0 * qx * (warp_strength * 0.5) + cr2_x * base_scale,
        grid_y + 4.0 * qy * (warp_strength * 0.5) + cr2_y * base_scale,
        perm,
        octaves=min(4, octaves),
        persistence=persistence,
        lacunarity=lacunarity,
        base_scale=base_scale,
        offsets=octave_offsets,
    )

    # Final warped evaluation
    warped_h = fbm_2d(
        grid_x + rx * warp_strength,
        grid_y + ry * warp_strength,
        perm,
        octaves=octaves,
        persistence=persistence,
        lacunarity=lacunarity,
        base_scale=base_scale,
        offsets=octave_offsets,
    )

    return warped_h


def generate_terrain(
    config: Optional[TerrainConfig] = None,
    seed: int = 42,
) -> np.ndarray:
    """Generate 2D procedural heightmap array of shape (resolution, resolution).

    Returns a 2D float32 NumPy array with height values in meters [0.0, height_scale].
    """
    if config is None:
        config = TerrainConfig()

    res = config.resolution
    perm = _generate_permutation_table(seed)

    # Create coordinate grid in world meters
    world_width = config.world_size[0]
    world_length = config.world_size[2]

    xs = np.linspace(0.0, world_width, res, dtype=np.float32)
    ys = np.linspace(0.0, world_length, res, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)

    # Scale domain warp and persistence by deformation_strength
    deform = getattr(config, "deformation_strength", 1.0)
    effective_warp = config.domain_warp_strength * deform
    effective_persistence = float(np.clip(config.persistence * (0.8 + 0.2 * deform), 0.01, 0.99)) if deform != 1.0 else config.persistence

    # Generate domain warped FBM
    raw_h = domain_warped_fbm(
        grid_x,
        grid_y,
        perm,
        octaves=config.octaves,
        persistence=effective_persistence,
        lacunarity=config.lacunarity,
        base_scale=config.scale,
        warp_strength=effective_warp,
        seed=seed,
    )

    # Normalize to [0.0, 1.0]
    h_min = float(np.min(raw_h))
    h_max = float(np.max(raw_h))
    if h_max > h_min:
        norm_h = (raw_h - h_min) / (h_max - h_min)
    else:
        norm_h = np.zeros_like(raw_h)

    # Power redistribution for natural terrain (steep mountains, wide valleys)
    gamma = config.power_redistribution
    redistributed_h = np.power(norm_h, gamma)

    # Scale to world elevation
    final_h = (redistributed_h * config.height_scale).astype(np.float32)

    return final_h
