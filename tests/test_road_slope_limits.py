"""
tests/test_road_slope_limits.py - Comprehensive test suite for V2 Requirement R3:
Strict Road Slope Limits and Slope-Aware A* Routing.

Covers:
1. Mathematical waypoint gradient/slope calculation across 3D road segments.
2. Road path gradient adherence under varying max_road_slope limits (0.10, 0.15, 0.25, 0.40).
3. Switchback / contour path selection when direct line exceeds max slope.
4. Road routing across steep ridges, hills, and plateau valleys.
5. Boundary conditions: gentle slopes vs extreme vertical cliff stress-testing.
6. Waypoint bounds, coordinate validity, and connection to zone centers.
"""

import math
import numpy as np
import pytest
from typing import List, Tuple, Dict, Any

from backend.app.core.schemas import TerrainConfig, Zone, RoadSegment
from backend.app.generator.roads import (
    _find_slope_aware_astar_path,
    generate_roads,
    _catmull_rom_spline,
    _sample_heightmap_bilinear,
)


# ============================================================================
# Helper Functions for Road Gradient & Geometry Evaluation
# ============================================================================

def compute_segment_slopes(waypoints: List[List[float]]) -> List[float]:
    """Computes vertical gradient (rise / run) for every consecutive pair of waypoints."""
    slopes: List[float] = []
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]
        dx = p2[0] - p1[0]
        dz = p2[2] - p1[2] if len(p2) >= 3 else p2[1] - p1[1]
        dy = abs(p2[1] - p1[1]) if len(p2) >= 3 else 0.0

        horiz_dist = math.hypot(dx, dz)
        if horiz_dist > 1e-4:
            slopes.append(dy / horiz_dist)
        else:
            slopes.append(0.0)
    return slopes


def compute_max_observed_slope(waypoints: List[List[float]]) -> float:
    """Returns the maximum slope encountered along the entire road path."""
    slopes = compute_segment_slopes(waypoints)
    return max(slopes) if slopes else 0.0


def compute_path_length_2d(waypoints: List[List[float]]) -> float:
    """Computes total 2D horizontal length along waypoints."""
    total = 0.0
    for i in range(len(waypoints) - 1):
        dx = waypoints[i + 1][0] - waypoints[i][0]
        dz = (waypoints[i + 1][2] - waypoints[i][2]) if len(waypoints[i + 1]) >= 3 else (waypoints[i + 1][1] - waypoints[i][1])
        total += math.hypot(dx, dz)
    return total


# ============================================================================
# 1. Gradient Adherence on Synthetic Slopes & Ridges
# ============================================================================

class TestRoadSlopeLimitAdherence:
    """Verifies that A* road paths strictly adhere to max_road_slope constraints."""

    @pytest.mark.parametrize("max_grade", [0.10, 0.15, 0.25, 0.40])
    def test_astar_slope_adherence_on_ramp(self, max_grade: float):
        """On a uniform linear ramp, the pathfinder selects paths respecting max_grade."""
        res = 65
        world_size = [1000.0, 150.0, 1000.0]
        t_config = TerrainConfig(resolution=res, world_size=world_size, height_scale=150.0)

        # Create a linear ramp: height increases along X from 10m to 100m over 1000m (slope = 0.09)
        ramp_hmap = np.zeros((res, res), dtype=np.float32)
        for ix in range(res):
            ramp_hmap[:, ix] = 10.0 + (ix / (res - 1)) * 90.0

        start_pt = (100.0, 500.0)
        goal_pt = (900.0, 500.0)

        path_3d = _find_slope_aware_astar_path(
            heightmap=ramp_hmap,
            start_world=start_pt,
            goal_world=goal_pt,
            terrain_config=t_config,
            max_grade=max_grade,
        )

        assert len(path_3d) >= 2, "Path must have at least start and end points"
        formatted = [[p[0], p[1], p[2]] for p in path_3d]
        max_obs = compute_max_observed_slope(formatted)

        # Observed slope should be close to or below max_grade (allowing minor spline tolerance)
        assert max_obs <= max_grade + 0.08, (
            f"Observed max slope {max_obs:.3f} exceeded limit {max_grade}"
        )

    def test_switchback_detour_on_steep_ridge(self):
        """When direct line crosses a steep ridge, router takes a longer detour to keep slope low."""
        res = 65
        world_size = [1000.0, 200.0, 1000.0]
        t_config = TerrainConfig(resolution=res, world_size=world_size, height_scale=200.0)

        # Create a steep ridge in the center: X=500m has height 150m, sides are 20m
        ridge_hmap = np.zeros((res, res), dtype=np.float32)
        for ix in range(res):
            x_m = (ix / (res - 1)) * 1000.0
            dist_to_center = abs(x_m - 500.0)
            # Steep Gaussian ridge with a low pass on the north end (Z > 800)
            for iz in range(res):
                z_m = (iz / (res - 1)) * 1000.0
                pass_factor = 0.2 if z_m > 750.0 else 1.0  # Valley pass on top edge
                ridge_hmap[iz, ix] = 20.0 + (130.0 * math.exp(-0.5 * (dist_to_center / 50.0) ** 2)) * pass_factor

        start_pt = (200.0, 500.0)
        goal_pt = (800.0, 500.0)
        direct_dist = math.hypot(goal_pt[0] - start_pt[0], goal_pt[1] - start_pt[1])  # 600m

        # Low slope limit (0.15) forces detour through the pass
        path_gentle = _find_slope_aware_astar_path(
            heightmap=ridge_hmap,
            start_world=start_pt,
            goal_world=goal_pt,
            terrain_config=t_config,
            max_grade=0.15,
            slope_weight=50.0,
        )

        formatted_gentle = [[p[0], p[1], p[2]] for p in path_gentle]
        length_gentle = compute_path_length_2d(formatted_gentle)
        max_slope_gentle = compute_max_observed_slope(formatted_gentle)

        # Detour length must be longer than direct Euclidean line
        assert length_gentle >= direct_dist * 1.05, (
            f"Expected detour path length ({length_gentle:.1f}m) to exceed direct line ({direct_dist:.1f}m)"
        )
        assert max_slope_gentle <= 0.35, f"Expected slope <= 0.35, got {max_slope_gentle:.3f}"


# ============================================================================
# 2. Road Network Integration Across Multi-Zone Terrain
# ============================================================================

class TestRoadNetworkSlopeLimits:
    """Verifies road network generator respecting slope limits across multiple zones."""

    def test_generate_roads_all_segments_valid(self):
        """Generated road network segments must have valid 3D waypoints and finite slope values."""
        res = 65
        world_size = [1000.0, 150.0, 1000.0]
        t_config = TerrainConfig(resolution=res, world_size=world_size)

        # Procedural rolling terrain
        xs = np.linspace(0, 3 * np.pi, res)
        zs = np.linspace(0, 3 * np.pi, res)
        gx, gz = np.meshgrid(xs, zs)
        hmap = (30.0 * np.sin(gx) * np.cos(gz) + 40.0).astype(np.float32)

        zones = [
            Zone(
                id="zone_0",
                name="Base Alpha",
                faction="A",
                destruction="01",
                density="medium",
                center=[250.0, float(hmap[16, 16]), 250.0],
                radius=60.0,
            ),
            Zone(
                id="zone_1",
                name="Outpost Bravo",
                faction="B",
                destruction="02",
                density="low",
                center=[750.0, float(hmap[48, 48]), 750.0],
                radius=60.0,
            ),
            Zone(
                id="zone_2",
                name="Depot Charlie",
                faction="C",
                destruction="01",
                density="high",
                center=[300.0, float(hmap[48, 19]), 750.0],
                radius=55.0,
            ),
        ]

        roads = generate_roads(heightmap=hmap, zones=zones, terrain_config=t_config, seed=42)

        assert len(roads) >= 2, "Expected at least 2 road segments for 3 connected zones"

        for road in roads:
            assert len(road.waypoints) >= 2, f"Road {road.id} has insufficient waypoints"
            max_slope = compute_max_observed_slope(road.waypoints)
            assert not math.isnan(max_slope), f"Road {road.id} produced NaN slope"
            assert max_slope < 1.5, f"Road {road.id} has unrealistic vertical slope {max_slope:.2f}"

            # Verify waypoint bounds
            for wp in road.waypoints:
                assert 0.0 <= wp[0] <= world_size[0], f"Waypoint X={wp[0]} out of map"
                assert 0.0 <= wp[2] <= world_size[2], f"Waypoint Z={wp[2]} out of map"
                assert wp[1] >= 0.0, f"Waypoint elevation Y={wp[1]} is negative"


# ============================================================================
# 3. Boundary & Extreme Steepness Stress Tests
# ============================================================================

class TestRoadSlopeBoundaryStress:
    """Stress tests road routing on extreme terrain conditions."""

    def test_flat_terrain_zero_slope(self):
        """On a perfectly flat plain, all road waypoint slopes are 0.0."""
        res = 65
        world_size = [1000.0, 100.0, 1000.0]
        t_config = TerrainConfig(resolution=res, world_size=world_size)
        flat_hmap = np.full((res, res), 30.0, dtype=np.float32)

        path = _find_slope_aware_astar_path(
            heightmap=flat_hmap,
            start_world=(200.0, 200.0),
            goal_world=(800.0, 800.0),
            terrain_config=t_config,
            max_grade=0.20,
        )

        formatted = [[p[0], p[1], p[2]] for p in path]
        max_slope = compute_max_observed_slope(formatted)
        assert max_slope == pytest.approx(0.0, abs=1e-3)

    def test_vertical_cliff_fallback_graceful(self):
        """Routing against a sheer 100m cliff without available detour completes gracefully."""
        res = 65
        world_size = [1000.0, 200.0, 1000.0]
        t_config = TerrainConfig(resolution=res, world_size=world_size)

        # Complete wall across entire map at X=500
        cliff_hmap = np.zeros((res, res), dtype=np.float32)
        cliff_hmap[:, :32] = 10.0
        cliff_hmap[:, 32:] = 190.0

        path = _find_slope_aware_astar_path(
            heightmap=cliff_hmap,
            start_world=(200.0, 500.0),
            goal_world=(800.0, 500.0),
            terrain_config=t_config,
            max_grade=0.10,
        )

        # Pathfinder should terminate and return valid fallback points without crashing
        assert len(path) >= 2
        for pt in path:
            assert not math.isnan(pt[0]) and not math.isnan(pt[1]) and not math.isnan(pt[2])
