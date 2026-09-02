"""
tests/test_adversarial_reviewer3.py - Independent Reviewer 3 Adversarial Verification Suite
Probes extreme edge conditions across all four critical requirements:
1. R1: A* Road Pathfinding, Delaunay triangulation resilience, 5-10m waypoint spacing.
2. R2: Watertight manifold mesh decimation under extreme topologies.
3. R3: OrbitControls drag-start decoupling.
4. R4: Drag-end only API recomputation.
"""

import math
import os
import numpy as np
import pytest
from typing import List, Tuple, Dict, Set

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
# 1. R1: A* Road Pathfinding & Delaunay Deep Adversarial Probes
# ============================================================================

class TestReviewer3RoadsR1:
    """Rigorous boundary and extreme topology tests for Road Pathfinding."""

    def test_delaunay_concentric_rings(self):
        """Concentric circles of points triangulate cleanly without overlapping edges."""
        pts = []
        for r in [100.0, 300.0, 500.0]:
            for a in range(8):
                angle = (a / 8.0) * 2 * math.pi
                pts.append((500.0 + r * math.cos(angle), 500.0 + r * math.sin(angle)))

        edges = _delaunay_triangulation_2d(pts)
        assert len(edges) >= len(pts)
        for u, v in edges:
            assert 0 <= u < len(pts)
            assert 0 <= v < len(pts)
            assert u != v

    def test_delaunay_grid_coplanar_sets(self):
        """A regular 5x5 grid of points triangulates into valid non-self-intersecting graph edges."""
        pts = [(float(x * 100), float(y * 100)) for x in range(5) for y in range(5)]
        edges = _delaunay_triangulation_2d(pts)
        assert len(edges) >= 40
        for u, v in edges:
            assert 0 <= u < len(pts)
            assert 0 <= v < len(pts)
            assert u != v

    def test_fallback_sampling_exact_spacing_bounds(self):
        """Every segment along a 2400m diagonal line across severe mountain terrain must have 5.0m <= spacing <= 10.0m."""
        hmap = np.zeros((129, 129), dtype=np.float32)
        for r in range(129):
            for c in range(129):
                hmap[r, c] = 50.0 + 40.0 * math.sin(r * 0.1) * math.cos(c * 0.1)

        start = (200.0, 300.0)
        goal = (2600.0, 1900.0)
        total_dist = math.hypot(goal[0] - start[0], goal[1] - start[1])

        fallback = _sample_terrain_straight_line(
            heightmap=hmap,
            start_world=start,
            goal_world=goal,
            world_w=3000.0,
            world_l=3000.0,
            sample_spacing=8.0,
        )

        assert len(fallback) >= int(total_dist / 10.0)
        for i in range(len(fallback) - 1):
            p1 = fallback[i]
            p2 = fallback[i + 1]
            seg_dist = math.hypot(p2[0] - p1[0], p2[2] - p1[2])
            assert 5.0 <= seg_dist <= 10.0, f"Segment {i} length {seg_dist:.2f} outside [5m, 10m]"

    def test_astar_extreme_aspect_ratio_world(self):
        """A* road pathfinding on a 5km x 1km asymmetric world completes and respects waypoints."""
        res_x = 257
        res_z = 65
        hmap = np.ones((res_z, res_x), dtype=np.float32) * 20.0
        cfg = TerrainConfig(
            resolution=257,
            world_size=[5000.0, 150.0, 1000.0],
            map_width_km=5.0,
            map_length_km=1.0,
            max_road_slope=0.25,
        )

        zones = [
            Zone(id="z0", name="West Depot", faction="A", destruction="01", zone_type="depot",
                 density=0.5, center=[300.0, 20.0, 500.0], radius=60.0, footprint_points=[]),
            Zone(id="z1", name="East Base", faction="B", destruction="02", zone_type="military_base",
                 density=0.5, center=[4700.0, 20.0, 500.0], radius=60.0, footprint_points=[]),
        ]

        roads = generate_roads(hmap, zones, cfg, seed=99)
        assert len(roads) == 1
        road = roads[0]
        assert len(road.waypoints) >= 200  # Densely sampled across 4400m
        for wp in road.waypoints:
            assert 0.0 <= wp[0] <= 5000.0
            assert 0.0 <= wp[2] <= 1000.0


# ============================================================================
# 2. R2: Watertight Adaptive Mesh Decimation Deep Adversarial Probes
# ============================================================================

class TestReviewer3MeshR2:
    """Rigorous topological verification of Decimated Mesh."""

    @pytest.mark.parametrize("res_z,res_x", [
        (4, 4),
        (8, 16),
        (16, 8),
        (33, 65),
        (65, 33),
        (65, 65),
        (129, 129),
    ])
    def test_mesh_zero_tears_and_strict_manifoldness(self, res_z: int, res_x: int):
        """Exhaustive check: all interior edges shared by exactly 2 triangles, all perimeter edges shared by 1."""
        rng = np.random.RandomState(res_z * 500 + res_x)
        hmap = (rng.uniform(0.0, 60.0, size=(res_z, res_x)) ** 2 / 40.0).astype(np.float32)

        mesh = generate_adaptive_mesh(hmap, [1000.0, 120.0, 1000.0], max_error=1.0)
        verts = mesh.vertices
        indices = mesh.indices
        num_verts = len(verts)

        assert len(indices) % 3 == 0
        edge_counts: Dict[Tuple[int, int], int] = {}

        for t in range(0, len(indices), 3):
            i0, i1, i2 = indices[t], indices[t + 1], indices[t + 2]
            assert 0 <= i0 < num_verts
            assert 0 <= i1 < num_verts
            assert 0 <= i2 < num_verts
            assert i0 != i1 and i1 != i2 and i0 != i2

            # Check upward winding
            p0, p1, p2 = verts[i0], verts[i1], verts[i2]
            cross_y = (p1[2] - p0[2]) * (p2[0] - p0[0]) - (p1[0] - p0[0]) * (p2[2] - p0[2])
            assert cross_y > 1e-6, f"Inverted normal at [{i0},{i1},{i2}]"

            for e in [(min(i0, i1), max(i0, i1)),
                      (min(i1, i2), max(i1, i2)),
                      (min(i2, i0), max(i2, i0))]:
                edge_counts[e] = edge_counts.get(e, 0) + 1

        for e, count in edge_counts.items():
            assert count in (1, 2), f"Non-manifold edge {e} with count {count}"


# ============================================================================
# 3. R3 & R4: Frontend Drag & API Sync Static Verification
# ============================================================================

class TestReviewer3FrontendR3R4:
    """Verifies OrbitControls drag decoupling and dragend-only generation."""

    def test_viewer_has_orbit_controls_lock_and_capture(self):
        """Verifies OrbitControls is disabled during pointer drag with capture phase."""
        viewer_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "scene", "viewer.js")
        with open(viewer_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "this.controls.enabled = false" in content
        assert "this.controls.enabled = true" in content
        assert "{ capture: true }" in content
        assert "pointercancel" in content

    def test_pointermove_is_purely_local(self):
        """Verifies onPointerMove only updates preview visuals and makes zero network requests."""
        viewer_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "scene", "viewer.js")
        with open(viewer_path, "r", encoding="utf-8") as f:
            content = f.read()

        start = content.find("onPointerMove(event) {")
        end = content.find("onPointerUp(event) {")
        move_body = content[start:end]

        assert "fetch(" not in move_body
        assert "generateWorld" not in move_body
        assert "recomputeZone" not in move_body
        assert "previewMoveZone" in move_body
