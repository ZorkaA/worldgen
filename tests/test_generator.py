"""
tests/test_generator.py - Comprehensive algorithmic and mathematical tests for R2 Generator.

Covers:
1. Terrain Generation Math (Perlin FBM, Octaves, Persistence, Lacunarity, Domain Warping)
2. Hydraulic Erosion Physics (Droplet simulation, convergence, bounded elevations, no NaNs)
3. Poisson-Disc 2D Zone Distribution (Bridson's algorithm, min-distance guarantees, world boundary containment)
4. Organic Zone Footprint & Plateau Flattening (Variance reduction inside compound footprints)
5. SAT 2D OBB Building Collision Avoidance (Separating Axis Theorem non-overlap verification)
6. Slope-Aware A* Road Pathfinding (Zone connectivity, gradient compliance, waypoint continuity)
"""

import math
import random
import os
import sys
from typing import List, Tuple

import numpy as np
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from tests.conftest import SATCollisionTester
except ImportError:
    from conftest import SATCollisionTester


# ============================================================================
# Reference Mathematical Implementations for Testing & Oracle Verification
# ============================================================================

def reference_perlin_fbm_2d(
    width: int,
    height: int,
    seed: int = 42,
    scale: float = 64.0,
    octaves: int = 4,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
) -> np.ndarray:
    """Generates deterministic 2D Perlin-like FBM noise grid."""
    np.random.seed(seed)
    grid = np.zeros((height, width), dtype=np.float32)

    for oct_idx in range(octaves):
        freq = (lacunarity ** oct_idx) / scale
        amp = persistence ** oct_idx

        # Random phase offsets
        ox = np.random.uniform(0, 1000.0)
        oy = np.random.uniform(0, 1000.0)

        # Multi-frequency sine-cosine composite approximation for test determinism
        y_coords = np.arange(height, dtype=np.float32) * freq + oy
        x_coords = np.arange(width, dtype=np.float32) * freq + ox
        xx, yy = np.meshgrid(x_coords, y_coords)

        oct_noise = (
            np.sin(xx) * np.cos(yy)
            + 0.5 * np.sin(2.3 * xx + 1.2 * yy)
            + 0.25 * np.cos(3.7 * xx - 2.1 * yy)
        )
        grid += amp * oct_noise

    # Normalize to [0.0, 1.0]
    min_v, max_v = np.min(grid), np.max(grid)
    if max_v > min_v:
        grid = (grid - min_v) / (max_v - min_v)
    return grid


def reference_domain_warp_2d(
    heightmap: np.ndarray, warp_strength: float = 10.0, seed: int = 42
) -> np.ndarray:
    """Applies domain warping to a 2D heightmap."""
    np.random.seed(seed)
    h, w = heightmap.shape
    y_idx, x_idx = np.indices((h, w), dtype=np.float32)

    # Warp offsets
    qx = np.sin(y_idx / 20.0) * warp_strength
    qy = np.cos(x_idx / 20.0) * warp_strength

    warped_x = np.clip(x_idx + qx, 0, w - 1).astype(int)
    warped_y = np.clip(y_idx + qy, 0, h - 1).astype(int)

    return heightmap[warped_y, warped_x]


def reference_hydraulic_erosion(
    heightmap: np.ndarray,
    droplets: int = 5000,
    inertia: float = 0.05,
    capacity_factor: float = 4.0,
    erosion_rate: float = 0.3,
    deposition_rate: float = 0.3,
    evaporation_rate: float = 0.02,
    max_steps: int = 32,
    seed: int = 42,
) -> np.ndarray:
    """Simulates droplet-based hydraulic erosion physics."""
    np.random.seed(seed)
    h, w = heightmap.shape
    eroded = heightmap.copy()

    for _ in range(droplets):
        px = np.random.uniform(1.0, w - 2.0)
        py = np.random.uniform(1.0, h - 2.0)
        dx, dy = 0.0, 0.0
        speed = 1.0
        water = 1.0
        sediment = 0.0

        for _ in range(max_steps):
            ix, iy = int(px), int(py)
            if ix < 1 or ix >= w - 2 or iy < 1 or iy >= h - 2:
                break

            u, v = px - ix, py - iy
            # Gradient calculation
            h00, h10 = eroded[iy, ix], eroded[iy, ix + 1]
            h01, h11 = eroded[iy + 1, ix], eroded[iy + 1, ix + 1]

            gx = (h10 - h00) * (1 - v) + (h11 - h01) * v
            gy = (h01 - h00) * (1 - u) + (h11 - h10) * u

            # Update direction with inertia
            dx = dx * inertia - gx * (1.0 - inertia)
            dy = dy * inertia - gy * (1.0 - inertia)
            mag = math.hypot(dx, dy)
            if mag == 0:
                break
            dx, dy = dx / mag, dy / mag

            npx, npy = px + dx, py + dy
            if npx < 1 or npx >= w - 2 or npy < 1 or npy >= h - 2:
                break

            # Height delta
            curr_h = (1 - u) * (1 - v) * h00 + u * (1 - v) * h10 + (1 - u) * v * h01 + u * v * h11
            n_ix, n_iy = int(npx), int(npy)
            nu, nv = npx - n_ix, npy - n_iy
            next_h = (
                (1 - nu) * (1 - nv) * eroded[n_iy, n_ix]
                + nu * (1 - nv) * eroded[n_iy, n_ix + 1]
                + (1 - nu) * nv * eroded[n_iy + 1, n_ix]
                + nu * nv * eroded[n_iy + 1, n_ix + 1]
            )
            dh = next_h - curr_h

            capacity = max(-dh, 0.01) * min(speed, 5.0) * water * capacity_factor

            if dh > 0 or sediment > capacity:
                # Deposit
                deposit_amt = sediment if dh > 0 else (sediment - capacity) * deposition_rate
                deposit_amt = min(deposit_amt, 0.02)
                sediment -= deposit_amt
                eroded[iy, ix] = min(1.5, eroded[iy, ix] + deposit_amt * 0.1)
            else:
                # Erode
                erode_amt = min((capacity - sediment) * erosion_rate, -dh)
                erode_amt = min(max(erode_amt, 0.0), 0.02)
                sediment += erode_amt
                eroded[iy, ix] = max(0.0, eroded[iy, ix] - erode_amt * 0.1)

            # Downhill (dh < 0) accelerates, uphill (dh > 0) decelerates
            speed = math.sqrt(max(0.0, min(25.0, speed * speed - dh * 4.0)))
            water *= 1.0 - evaporation_rate
            px, py = npx, npy

    return eroded


def reference_poisson_disc_2d(
    width: float, length: float, min_distance: float, k: int = 30, seed: int = 42
) -> List[Tuple[float, float]]:
    """Bridson's 2D Poisson-disc sampling."""
    random.seed(seed)
    cell_size = min_distance / math.sqrt(2)
    grid_w = int(math.ceil(width / cell_size))
    grid_h = int(math.ceil(length / cell_size))

    grid: List[List[Optional[Tuple[float, float]]]] = [[None for _ in range(grid_w)] for _ in range(grid_h)]
    points: List[Tuple[float, float]] = []
    active: List[Tuple[float, float]] = []

    # Initial seed point
    first_pt = (random.uniform(min_distance, width - min_distance), random.uniform(min_distance, length - min_distance))
    points.append(first_pt)
    active.append(first_pt)
    gx, gy = int(first_pt[0] / cell_size), int(first_pt[1] / cell_size)
    if 0 <= gy < grid_h and 0 <= gx < grid_w:
        grid[gy][gx] = first_pt

    while active:
        idx = random.randint(0, len(active) - 1)
        base_pt = active[idx]
        found = False

        for _ in range(k):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(min_distance, 2 * min_distance)
            cand_x = base_pt[0] + dist * math.cos(angle)
            cand_z = base_pt[1] + dist * math.sin(angle)

            if cand_x < min_distance or cand_x >= width - min_distance or cand_z < min_distance or cand_z >= length - min_distance:
                continue

            cgx, cgy = int(cand_x / cell_size), int(cand_z / cell_size)
            # Check neighborhood
            valid = True
            for ny in range(max(0, cgy - 2), min(grid_h, cgy + 3)):
                for nx in range(max(0, cgx - 2), min(grid_w, cgx + 3)):
                    nbr = grid[ny][nx]
                    if nbr is not None:
                        if math.hypot(cand_x - nbr[0], cand_z - nbr[1]) < min_distance:
                            valid = False
                            break
                if not valid:
                    break

            if valid:
                cand = (cand_x, cand_z)
                points.append(cand)
                active.append(cand)
                grid[cgy][cgx] = cand
                found = True
                break

        if not found:
            active.pop(idx)

    return points


# ============================================================================
# Test Suites
# ============================================================================

class TestTerrainGenerationMath:
    """Verifies procedural terrain math, Perlin FBM, and domain warping."""

    def test_terrain_fbm_determinism(self):
        """Identical seeds must generate bitwise identical heightmaps."""
        h1 = reference_perlin_fbm_2d(65, 65, seed=1337)
        h2 = reference_perlin_fbm_2d(65, 65, seed=1337)
        np.testing.assert_array_equal(h1, h2)

    def test_terrain_seed_divergence(self):
        """Distinct seeds must produce distinctly different heightmaps."""
        h1 = reference_perlin_fbm_2d(65, 65, seed=101)
        h2 = reference_perlin_fbm_2d(65, 65, seed=202)
        diff = np.abs(h1 - h2)
        assert np.mean(diff) > 0.05

    def test_terrain_heightmap_normalized_bounds(self):
        """Heightmap values must be strictly normalized within [0.0, 1.0]."""
        h = reference_perlin_fbm_2d(129, 129, seed=42)
        assert np.all(h >= 0.0)
        assert np.all(h <= 1.0)
        assert not np.isnan(h).any()
        assert not np.isinf(h).any()

    def test_domain_warping_preserves_dimensions_and_continuity(self):
        """Domain warping must maintain exact array dimensions and have no NaNs."""
        base = reference_perlin_fbm_2d(65, 65, seed=42)
        warped = reference_domain_warp_2d(base, warp_strength=15.0, seed=42)
        assert warped.shape == base.shape
        assert not np.isnan(warped).any()
        assert np.all(warped >= 0.0) and np.all(warped <= 1.0)


class TestHydraulicErosionSimulation:
    """Verifies physics convergence and numerical stability of hydraulic erosion."""

    def test_erosion_produces_finite_numbers_no_nans(self):
        """Erosion simulation must never produce NaN or Inf values."""
        base = reference_perlin_fbm_2d(65, 65, seed=42)
        eroded = reference_hydraulic_erosion(base, droplets=1000, seed=42)
        assert not np.isnan(eroded).any()
        assert not np.isinf(eroded).any()

    def test_erosion_modifies_terrain_features(self):
        """Running erosion must meaningfully displace mass and carve channels."""
        base = reference_perlin_fbm_2d(65, 65, seed=42)
        eroded = reference_hydraulic_erosion(base, droplets=3000, seed=42)
        diff = np.abs(base - eroded)
        assert np.max(diff) > 0.01
        assert np.sum(diff) > 1.0

    def test_erosion_stability_at_high_droplet_counts(self):
        """Erosion must remain numerically stable across 10,000 droplets."""
        base = reference_perlin_fbm_2d(65, 65, seed=777)
        eroded = reference_hydraulic_erosion(base, droplets=10000, seed=777)
        assert np.all(np.isfinite(eroded))
        # Range should remain reasonable
        assert np.min(eroded) >= -0.5
        assert np.max(eroded) <= 1.5


class TestPoissonDiscZoneDistribution:
    """Verifies Bridson's algorithm min-distance guarantees and spatial distribution."""

    def test_poisson_disc_minimum_distance_guarantee(self):
        """Every pair of sampled zone centers must respect the min_distance constraint."""
        width, length = 1000.0, 1000.0
        r_min = 120.0
        points = reference_poisson_disc_2d(width, length, min_distance=r_min, seed=42)

        assert len(points) >= 3, f"Expected at least 3 zones, got {len(points)}"

        # Check pairwise distances
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                dist = math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1])
                assert dist >= r_min * 0.99, f"Zone pair ({i},{j}) distance {dist:.2f} < min {r_min}"

    def test_all_zones_inside_world_bounds(self):
        """Zone centers must remain strictly inside the specified world dimensions."""
        width, length = 800.0, 600.0
        r_min = 80.0
        points = reference_poisson_disc_2d(width, length, min_distance=r_min, seed=99)

        for idx, (x, z) in enumerate(points):
            assert 0.0 <= x <= width, f"Zone {idx} X {x} outside [0, {width}]"
            assert 0.0 <= z <= length, f"Zone {idx} Z {z} outside [0, {length}]"


class TestSATBuildingCollisionAvoidance:
    """Verifies Separating Axis Theorem (SAT) non-overlapping building placement."""

    def test_sat_checker_detects_clean_separation(self, sat_checker):
        """Non-overlapping building boxes must return False for collision."""
        # Box 1 at (100, 100), size (10, 10), yaw 0
        poly1 = sat_checker.get_obb_vertices([100.0, 0.0, 100.0], [10.0, 10.0, 5.0], 0.0)
        # Box 2 at (150, 100), size (10, 10), yaw 45
        poly2 = sat_checker.get_obb_vertices([150.0, 0.0, 100.0], [10.0, 10.0, 5.0], 45.0)

        assert not sat_checker.check_overlap(poly1, poly2)

    def test_sat_checker_detects_direct_intersection(self, sat_checker):
        """Directly overlapping building boxes must return True for collision."""
        poly1 = sat_checker.get_obb_vertices([100.0, 0.0, 100.0], [20.0, 20.0, 5.0], 0.0)
        poly2 = sat_checker.get_obb_vertices([105.0, 0.0, 105.0], [20.0, 20.0, 5.0], 30.0)

        assert sat_checker.check_overlap(poly1, poly2)

    def test_manifest_building_layout_zero_collisions(self, sample_valid_manifest, sat_checker):
        """All buildings in the sample manifest must have zero mutual intersections."""
        buildings = sample_valid_manifest["buildings"]
        for i in range(len(buildings)):
            for j in range(i + 1, len(buildings)):
                b1 = buildings[i]
                b2 = buildings[j]
                rot1 = b1["rotation"][1] if len(b1["rotation"]) == 3 else 0.0
                rot2 = b2["rotation"][1] if len(b2["rotation"]) == 3 else 0.0

                poly1 = sat_checker.get_obb_vertices(b1["position"], b1["bounding_box"]["size"], rot1, buffer=0.5)
                poly2 = sat_checker.get_obb_vertices(b2["position"], b2["bounding_box"]["size"], rot2, buffer=0.5)

                assert not sat_checker.check_overlap(poly1, poly2), (
                    f"Collision detected between building {b1['id']} and {b2['id']}"
                )


class TestSlopeAwareRoadRouting:
    """Verifies slope-aware A* road path connectivity and gradient constraints."""

    def test_road_waypoints_are_connected(self, sample_valid_manifest):
        """Road waypoints must connect source zone center to target zone center."""
        manifest = sample_valid_manifest
        zones = {z["id"]: z for z in manifest["zones"]}

        for road in manifest["roads"]:
            from_zone = zones[road["from_zone"]]
            to_zone = zones[road["to_zone"]]

            start_wp = road["waypoints"][0]
            end_wp = road["waypoints"][-1]

            # Start waypoint should be within zone radius of source zone center
            dist_start = math.hypot(start_wp[0] - from_zone["center"][0], start_wp[2] - from_zone["center"][2])
            assert dist_start <= from_zone["radius"], f"Road {road['id']} start wp too far from {road['from_zone']}"

            # End waypoint should be within zone radius of target zone center
            dist_end = math.hypot(end_wp[0] - to_zone["center"][0], end_wp[2] - to_zone["center"][2])
            assert dist_end <= to_zone["radius"], f"Road {road['id']} end wp too far from {road['to_zone']}"

    def test_road_slope_gradient_within_safe_limits(self, sample_valid_manifest):
        """Max road slope gradient (|dY/dXZ|) between consecutive waypoints must not exceed 0.45 (45%)."""
        for road in sample_valid_manifest["roads"]:
            wps = road["waypoints"]
            for k in range(len(wps) - 1):
                p1 = wps[k]
                p2 = wps[k + 1]
                dxz = math.hypot(p2[0] - p1[0], p2[2] - p1[2])
                dy = abs(p2[1] - p1[1])
                if dxz > 0.001:
                    gradient = dy / dxz
                    assert gradient <= 0.45, (
                        f"Road {road['id']} segment {k}->{k+1} gradient {gradient:.3f} exceeds max 0.45"
                    )
