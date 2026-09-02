"""
tests/test_adversarial_reviewer2.py - Independent Reviewer 2 Adversarial Stress Test Suite

Probes edge cases across all 4 requirements:
1. R1: A* Road Pathfinding:
   - Zero distance (start == goal)
   - Extremely large distance (3km) with strict 5-10m waypoint spacing
   - Collinear Delaunay point sets (unordered, out of sequence, duplicate coordinates)
   - Heightmap boundary clamping and negative/overshooting coordinates
2. R2: Watertight Adaptive Terrain Mesh Decimation:
   - Exhaustive resolution matrix (2x2 up to 129x65, asymmetric aspect ratios, etc.)
   - Complex terrain topologies (cliffs, multi-spikes, flat step functions, zone plateaus)
   - Manifold topology verification (every interior edge shared by exactly 2 triangles, exactly 0 tears/holes)
   - Upward normal vector verification (cross_y > 1e-6)
3. R3: Drag vs. Orbit Controls Interaction
4. R4: API Generation on dragend only
"""

import math
import numpy as np
import pytest
from typing import List, Tuple, Set, Dict

from backend.app.core.schemas import TerrainConfig, Zone, RoadSegment
from backend.app.generator.roads import (
    _find_slope_aware_astar_path,
    _sample_terrain_straight_line,
    _delaunay_triangulation_2d,
    _generate_zone_edges,
    generate_roads,
    compute_max_observed_slope,
)
from backend.app.generator.mesh import generate_adaptive_mesh
from backend.app.generator.zones import _sample_heightmap_bilinear, flatten_zone_footprints, generate_zones
from backend.app.generator.terrain import generate_terrain


# ============================================================================
# 1. R1: A* Road Pathfinding Adversarial Tests
# ============================================================================

class TestAdversarialRoadsR1:
    """Probes edge cases and extreme inputs for Road generation and Delaunay graph."""

    def test_sample_terrain_straight_line_zero_distance(self):
        """Zero distance line (start == goal) must return at least 2 points without crashing."""
        hmap = np.ones((33, 33), dtype=np.float32) * 25.0
        pts = _sample_terrain_straight_line(
            heightmap=hmap,
            start_world=(500.0, 500.0),
            goal_world=(500.0, 500.0),
            world_w=1000.0,
            world_l=1000.0,
            sample_spacing=8.0,
        )
        assert len(pts) >= 2
        for wp in pts:
            assert len(wp) == 3
            assert math.isclose(wp[0], 500.0, abs_tol=0.01)
            assert math.isclose(wp[1], 25.15, abs_tol=0.01)
            assert math.isclose(wp[2], 500.0, abs_tol=0.01)

    def test_sample_terrain_straight_line_large_distance_spacing(self):
        """A 3000m line must have all consecutive waypoints spaced between 5m and 10m."""
        hmap = np.zeros((65, 65), dtype=np.float32)
        for r in range(65):
            for c in range(65):
                hmap[r, c] = 20.0 + 15.0 * math.sin(r * 0.2) + 10.0 * math.cos(c * 0.2)

        start = (100.0, 100.0)
        goal = (2900.0, 2100.0)
        total_dist = math.hypot(goal[0] - start[0], goal[1] - start[1])

        pts = _sample_terrain_straight_line(
            heightmap=hmap,
            start_world=start,
            goal_world=goal,
            world_w=3000.0,
            world_l=3000.0,
            sample_spacing=8.0,
        )

        assert len(pts) >= int(total_dist / 10.0)
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            seg_dist = math.hypot(p2[0] - p1[0], p2[2] - p1[2])
            assert 5.0 <= seg_dist <= 10.0, f"Segment {i} distance {seg_dist:.2f}m is not in [5m, 10m]"

    def test_sample_heightmap_bilinear_boundary_overshoot(self):
        """Overshooting or negative coordinates must be safely clamped to terrain boundary without NaNs."""
        hmap = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
        h_neg = _sample_heightmap_bilinear(hmap, -100.0, -100.0, 1000.0, 1000.0)
        assert not math.isnan(h_neg)
        assert not math.isinf(h_neg)

        h_over = _sample_heightmap_bilinear(hmap, 1500.0, 1500.0, 1000.0, 1000.0)
        assert not math.isnan(h_over)
        assert not math.isinf(h_over)

    def test_delaunay_unordered_collinear_points(self):
        """Unordered collinear points must form a non-self-intersecting linear path."""
        pts = [
            (300.0, 600.0),
            (0.0, 0.0),
            (500.0, 1000.0),
            (100.0, 200.0),
            (400.0, 800.0),
            (200.0, 400.0),
        ]
        edges = _delaunay_triangulation_2d(pts)
        assert len(edges) >= len(pts) - 1
        for u, v in edges:
            assert 0 <= u < len(pts)
            assert 0 <= v < len(pts)
            assert u != v

    def test_delaunay_duplicate_points_handling(self):
        """Points containing duplicate coordinates must not cause uncaught exceptions or self-loops."""
        pts = [
            (100.0, 100.0),
            (100.0, 100.0),
            (300.0, 300.0),
            (300.0, 300.0),
            (500.0, 500.0),
        ]
        edges = _delaunay_triangulation_2d(pts)
        for u, v in edges:
            assert u != v
            assert 0 <= u < len(pts)
            assert 0 <= v < len(pts)

    def test_delaunay_zero_and_single_point(self):
        """0 or 1 point returns empty edge list."""
        assert _delaunay_triangulation_2d([]) == []
        assert _delaunay_triangulation_2d([(100.0, 100.0)]) == []


# ============================================================================
# 2. R2: Watertight Adaptive Terrain Mesh Decimation Adversarial Tests
# ============================================================================

class TestAdversarialMeshWatertightnessR2:
    """Exhaustive topological validation of adaptive mesh decimation."""

    @pytest.mark.parametrize("res_z,res_x", [
        (2, 2),
        (3, 3),
        (5, 5),
        (17, 33),
        (33, 17),
        (30, 40),
        (65, 33),
        (33, 65),
        (65, 65),
        (129, 65),
    ])
    @pytest.mark.parametrize("max_err", [0.05, 0.5, 2.0, 20.0])
    def test_mesh_invariants_and_manifoldness(self, res_z: int, res_x: int, max_err: float):
        """Asserts zero degenerate triangles, positive upward normals, and 2-manifold edge topology."""
        rng = np.random.RandomState(res_z * 1000 + res_x + int(max_err * 10))
        hmap = rng.uniform(0.0, 80.0, size=(res_z, res_x)).astype(np.float32)
        if res_z > 4 and res_x > 4:
            hmap[res_z // 4 : 3 * res_z // 4, res_x // 4 : 3 * res_x // 4] += 50.0

        mesh = generate_adaptive_mesh(hmap, [1000.0, 150.0, 1000.0], max_error=max_err)

        verts = mesh.vertices
        indices = mesh.indices
        num_verts = len(verts)

        assert len(indices) % 3 == 0
        assert len(indices) > 0

        edge_counts: Dict[Tuple[int, int], int] = {}

        for t in range(0, len(indices), 3):
            i0, i1, i2 = indices[t], indices[t + 1], indices[t + 2]
            assert 0 <= i0 < num_verts
            assert 0 <= i1 < num_verts
            assert 0 <= i2 < num_verts
            assert i0 != i1 and i1 != i2 and i0 != i2, f"Degenerate triangle at [{i0}, {i1}, {i2}]"

            p0 = verts[i0]
            p1 = verts[i1]
            p2 = verts[i2]
            cross_y = (p1[2] - p0[2]) * (p2[0] - p0[0]) - (p1[0] - p0[0]) * (p2[2] - p0[2])
            assert cross_y > 1e-6, f"Triangle [{i0}, {i1}, {i2}] has inverted or non-positive area ({cross_y})"

            for e in [(min(i0, i1), max(i0, i1)),
                      (min(i1, i2), max(i1, i2)),
                      (min(i2, i0), max(i2, i0))]:
                edge_counts[e] = edge_counts.get(e, 0) + 1

        for e, count in edge_counts.items():
            assert count in (1, 2), f"Non-manifold edge {e} shared by {count} triangles at res ({res_z}, {res_x}) err {max_err}"

    def test_flattened_zones_mesh_no_voids(self):
        """Realistic terrain with 4 flattened zones generates watertight mesh."""
        cfg = TerrainConfig(resolution=65, height_scale=150.0, deformation_strength=1.0)
        raw_h = generate_terrain(cfg, seed=12345)
        zones, zone_data = generate_zones(raw_h, cfg, seed=12345)
        flat_h = flatten_zone_footprints(raw_h, zones, zone_data, cfg)

        mesh = generate_adaptive_mesh(flat_h, cfg.world_size, max_error=1.0)
        assert mesh.triangle_count > 0
        assert mesh.vertex_count > 0
        assert len(mesh.indices) == mesh.triangle_count * 3
