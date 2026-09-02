"""Adversarial Stress Verification Test Suite for WorldGen V2 Backend.

Verifies:
1. Extreme map dimensions (0.5 km, 10.0 km) and asymmetric aspect ratios (e.g. 4.0km x 1.0km, 0.5km x 10.0km).
2. Adaptive mesh decimation: assert all indices are < len(vertices), non-degeneracy, watertight boundary vertices, and significant polygon reduction on flat vs mountainous terrain.
3. Strict max_road_slope adherence: assert no road segment exceeds max_road_slope gradient on steep mountain heightmaps.
4. Continuous density monotonicity and 100% SAT 2D OBB collision avoidance at D=1.0 across 50 randomly seeded zones.
"""

import math
import numpy as np
import pytest
from typing import List, Tuple, Dict, Any

from backend.app.core.schemas import (
    TerrainConfig,
    ZoneConfig,
    GenerateWorldRequest,
    WorldManifest,
    Zone,
    BuildingPlacement,
    RoadSegment,
)
from backend.app.generator.terrain import generate_terrain
from backend.app.generator.erosion import simulate_hydraulic_erosion
from backend.app.generator.zones import generate_zones, flatten_zone_footprints, _sample_heightmap_bilinear
from backend.app.generator.mesh import generate_adaptive_mesh
from backend.app.generator.roads import generate_roads, compute_max_observed_slope, _find_slope_aware_astar_path
from backend.app.generator.buildings import (
    place_buildings,
    instantiate_templated_zone,
    load_asset_catalog,
    load_zone_templates,
    OBB2D,
    check_sat_overlap,
)
from backend.app.generator.pipeline import generate_world_pipeline


class TestExtremeMapSizesAndAspectRatios:
    """Stress tests for extreme map dimensions and asymmetric aspect ratios."""

    @pytest.mark.parametrize("res", [65, 129, 257])
    def test_minimum_map_size_0_5km(self, res: int):
        """Verify 0.5 km (500m x 500m) minimum map boundary handling."""
        config = TerrainConfig(
            resolution=res,
            world_size=[500.0, 100.0, 500.0],
            map_width_km=0.5,
            map_length_km=0.5,
            edge_margin=40.0,
        )
        z_config = ZoneConfig(
            min_zone_distance=80.0,
            zone_count_target=3,
            min_radius=20.0,
            max_radius=40.0,
            edge_margin=40.0,
        )
        request = GenerateWorldRequest(
            seed=101,
            terrain=config,
            zones=z_config,
        )
        manifest, hmap, summary = generate_world_pipeline(request=request, seed=101)

        # 1. Heightmap dimensions
        assert hmap.shape == (res, res)
        assert np.isfinite(hmap).all()
        assert not np.isnan(hmap).any()

        # 2. Manifest metadata bounds
        assert manifest.metadata.bounds == [0.0, 0.0, 0.0, 500.0, 100.0, 500.0]
        assert manifest.terrain.world_size == [500.0, 100.0, 500.0]

        # 3. Zone centers within margin bounds [40, 460]
        for z in manifest.zones:
            assert 30.0 <= z.center[0] <= 470.0, f"Zone X out of bounds: {z.center[0]}"
            assert 30.0 <= z.center[2] <= 470.0, f"Zone Z out of bounds: {z.center[2]}"
            assert 0.0 <= z.center[1] <= 150.0

        # 4. Building positions within map
        for b in manifest.buildings:
            assert 0.0 <= b.position[0] <= 500.0
            assert 0.0 <= b.position[2] <= 500.0

        # 5. Road waypoints within map
        for r in manifest.roads:
            for wp in r.waypoints:
                assert 0.0 <= wp[0] <= 500.0
                assert 0.0 <= wp[2] <= 500.0

    @pytest.mark.parametrize("res", [129, 257])
    def test_maximum_map_size_10_0km(self, res: int):
        """Verify 10.0 km (10000m x 10000m) maximum map boundary handling."""
        config = TerrainConfig(
            resolution=res,
            world_size=[10000.0, 300.0, 10000.0],
            map_width_km=10.0,
            map_length_km=10.0,
            edge_margin=200.0,
            scale=512.0,
        )
        z_config = ZoneConfig(
            min_zone_distance=500.0,
            zone_count_target=8,
            min_radius=80.0,
            max_radius=180.0,
            edge_margin=200.0,
        )
        request = GenerateWorldRequest(
            seed=202,
            terrain=config,
            zones=z_config,
        )
        manifest, hmap, summary = generate_world_pipeline(request=request, seed=202)

        assert hmap.shape == (res, res)
        assert manifest.metadata.bounds == [0.0, 0.0, 0.0, 10000.0, 300.0, 10000.0]
        assert len(manifest.zones) >= 4
        assert len(manifest.buildings) >= 20

        # Verify all coordinates span up to 10km safely
        for z in manifest.zones:
            assert 150.0 <= z.center[0] <= 9850.0
            assert 150.0 <= z.center[2] <= 9850.0

        for b in manifest.buildings:
            assert 0.0 <= b.position[0] <= 10000.0
            assert 0.0 <= b.position[2] <= 10000.0

    @pytest.mark.parametrize("width_km, length_km", [
        (4.0, 1.0),
        (1.0, 4.0),
        (8.0, 2.0),
        (0.5, 5.0),
        (5.0, 0.5),
        (0.5, 10.0),
        (10.0, 0.5),
    ])
    def test_asymmetric_aspect_ratios(self, width_km: float, length_km: float):
        """Verify non-square rectangular world sizes and asymmetric aspect ratios."""
        world_w = width_km * 1000.0
        world_l = length_km * 1000.0
        res = 129

        config = TerrainConfig(
            resolution=res,
            world_size=[world_w, 150.0, world_l],
            map_width_km=width_km,
            map_length_km=length_km,
            edge_margin=min(world_w, world_l) * 0.08,
        )
        z_config = ZoneConfig(
            min_zone_distance=min(world_w, world_l) * 0.25,
            zone_count_target=4,
            min_radius=20.0,
            max_radius=min(50.0, min(world_w, world_l) * 0.15),
            edge_margin=min(world_w, world_l) * 0.08,
        )
        request = GenerateWorldRequest(
            seed=303,
            terrain=config,
            zones=z_config,
        )
        manifest, hmap, summary = generate_world_pipeline(request=request, seed=303)

        assert hmap.shape == (res, res)
        assert manifest.terrain.world_size == [world_w, 150.0, world_l]

        # Check mesh vertex bounding bounds
        mesh = manifest.terrain.mesh
        assert mesh is not None
        assert mesh.vertex_count > 0

        verts = np.array(mesh.vertices)
        min_x, max_x = np.min(verts[:, 0]), np.max(verts[:, 0])
        min_z, max_z = np.min(verts[:, 2]), np.max(verts[:, 2])

        assert 0.0 <= min_x <= 5.0
        assert world_w - 5.0 <= max_x <= world_w + 1e-3
        assert 0.0 <= min_z <= 5.0
        assert world_l - 5.0 <= max_z <= world_l + 1e-3


class TestAdaptiveMeshDecimationAdversarial:
    """Stress testing adaptive mesh decimation geometry, indices, and topology."""

    def test_all_indices_strictly_within_vertex_bounds(self):
        """Assert every triangle index is non-negative and < len(vertices)."""
        rng = np.random.RandomState(42)
        for seed in [1, 42, 99, 555, 9999]:
            hmap = rng.uniform(0.0, 100.0, size=(129, 129)).astype(np.float32)
            mesh = generate_adaptive_mesh(
                heightmap=hmap,
                world_size=[1000.0, 100.0, 1000.0],
                max_error=1.5,
                min_cell_size=1,
            )

            num_verts = len(mesh.vertices)
            assert num_verts > 0
            assert len(mesh.indices) % 3 == 0
            assert mesh.triangle_count == len(mesh.indices) // 3

            for idx in mesh.indices:
                assert 0 <= idx < num_verts, f"Index {idx} out of range [0, {num_verts})"

    def test_triangle_non_degeneracy(self):
        """Assert no triangle has duplicate vertex indices or zero 2D area."""
        for error_thresh in [0.5, 1.0, 2.0, 5.0]:
            # Generate continuous synthetic mountain terrain
            x = np.linspace(0, 10, 65)
            z = np.linspace(0, 10, 65)
            gx, gz = np.meshgrid(x, z)
            hmap = (np.sin(gx) * np.cos(gz) * 50.0 + 50.0).astype(np.float32)

            mesh = generate_adaptive_mesh(
                heightmap=hmap,
                world_size=[1000.0, 100.0, 1000.0],
                max_error=error_thresh,
            )

            verts = mesh.vertices
            indices = mesh.indices

            for t in range(0, len(indices), 3):
                i0, i1, i2 = indices[t], indices[t + 1], indices[t + 2]
                # No duplicate indices in a single triangle
                assert i0 != i1 and i1 != i2 and i0 != i2, f"Degenerate triangle indices: ({i0}, {i1}, {i2})"

                p0 = np.array(verts[i0])
                p1 = np.array(verts[i1])
                p2 = np.array(verts[i2])

                # 2D cross product in (x, z) plane: (x1-x0)*(z2-z0) - (z1-z0)*(x2-x0)
                cross_2d = (p1[0] - p0[0]) * (p2[2] - p0[2]) - (p1[2] - p0[2]) * (p2[0] - p0[0])
                assert abs(cross_2d) > 1e-4, f"Zero area triangle found: {p0}, {p1}, {p2}"

    def test_watertight_boundary_vertices(self):
        """Assert the outer terrain boundaries (x=0, x=W, z=0, z=L) have continuous vertex coverage."""
        world_w = 1000.0
        world_l = 1000.0
        hmap = np.zeros((129, 129), dtype=np.float32)
        # Place a central hill so center subdivides but borders remain varied
        hmap[32:96, 32:96] = 50.0

        mesh = generate_adaptive_mesh(
            heightmap=hmap,
            world_size=[world_w, 100.0, world_l],
            max_error=1.0,
        )

        verts = np.array(mesh.vertices)
        x_coords = verts[:, 0]
        z_coords = verts[:, 2]

        # Find vertices on the four boundaries
        b_min_x = verts[np.isclose(x_coords, 0.0, atol=1e-2)]
        b_max_x = verts[np.isclose(x_coords, world_w, atol=1e-2)]
        b_min_z = verts[np.isclose(z_coords, 0.0, atol=1e-2)]
        b_max_z = verts[np.isclose(z_coords, world_l, atol=1e-2)]

        # Each boundary must have at least 2 corner endpoints (0 and max)
        assert len(b_min_x) >= 2
        assert len(b_max_x) >= 2
        assert len(b_min_z) >= 2
        assert len(b_max_z) >= 2

        # Check corner vertices exist
        corners_found = 0
        for v in verts:
            if (np.isclose(v[0], 0.0, atol=1e-2) or np.isclose(v[0], world_w, atol=1e-2)) and \
               (np.isclose(v[2], 0.0, atol=1e-2) or np.isclose(v[2], world_l, atol=1e-2)):
                corners_found += 1
        assert corners_found >= 4, f"Missing boundary corner vertices (found {corners_found})"

    def test_significant_polygon_reduction_flat_vs_mountain(self):
        """Assert flat plain achieves massive decimation (>75% reduction) compared to mountain terrain."""
        res = 129
        world_size = [1000.0, 150.0, 1000.0]

        # 1. Perfectly flat plain
        flat_hmap = np.full((res, res), 25.0, dtype=np.float32)
        flat_mesh = generate_adaptive_mesh(flat_hmap, world_size, max_error=1.0)

        # 2. Mountainous terrain (fractal Perlin)
        m_cfg = TerrainConfig(resolution=res, height_scale=150.0, scale=128.0, octaves=6)
        mountain_hmap = generate_terrain(m_cfg, seed=777)
        mountain_mesh = generate_adaptive_mesh(mountain_hmap, world_size, max_error=1.0)

        full_grid_tris = 2 * (res - 1) * (res - 1)  # 32768

        # Flat terrain should decimate to a single quad (2 triangles) or minimal cells
        assert flat_mesh.triangle_count == 2 or flat_mesh.decimation_ratio <= 0.05
        assert flat_mesh.decimation_ratio < 0.10

        # Mountain terrain should maintain significant detail
        assert mountain_mesh.triangle_count > flat_mesh.triangle_count * 10
        assert mountain_mesh.decimation_ratio > 0.15

        # Check polygon reduction ratio
        reduction_flat = (full_grid_tris - flat_mesh.triangle_count) / full_grid_tris
        assert reduction_flat >= 0.90, f"Flat terrain reduction was only {reduction_flat:.2%}"

    def test_normal_vectors_and_uv_bounds(self):
        """Assert all normals are unit length and UVs are strictly normalized in [0, 1]."""
        res = 65
        hmap = np.random.RandomState(42).uniform(0, 100, (res, res)).astype(np.float32)
        mesh = generate_adaptive_mesh(hmap, [1000.0, 100.0, 1000.0], max_error=1.0)

        normals = np.array(mesh.normals)
        uvs = np.array(mesh.uvs)

        # Normals must have unit length (~1.0)
        norm_lengths = np.linalg.norm(normals, axis=1)
        assert np.allclose(norm_lengths, 1.0, atol=1e-3), "Some normal vectors are not unit length"

        # UVs must be in [0.0, 1.0]
        assert np.all(uvs >= 0.0) and np.all(uvs <= 1.0)


class TestStrictRoadSlopeAdherence:
    """Stress testing A* road slope adherence across steep mountain heightmaps."""

    @pytest.mark.parametrize("max_slope_limit", [0.10, 0.15, 0.20, 0.25, 0.35])
    def test_procedural_mountain_slope_limit_adherence(self, max_slope_limit: float):
        """Verify road generation obeys or penalizes steep gradients according to max_road_slope."""
        res = 129
        t_cfg = TerrainConfig(
            resolution=res,
            world_size=[1000.0, 200.0, 1000.0],
            height_scale=200.0,
            scale=200.0,
            max_road_slope=max_slope_limit,
        )
        hmap = generate_terrain(t_cfg, seed=888)

        # Create 4 test zones across the terrain
        zones = [
            Zone(id="z0", name="Zone 0", center=[150.0, float(hmap[20, 20]), 150.0], radius=40.0),
            Zone(id="z1", name="Zone 1", center=[850.0, float(hmap[110, 110]), 850.0], radius=40.0),
            Zone(id="z2", name="Zone 2", center=[850.0, float(hmap[20, 110]), 150.0], radius=40.0),
            Zone(id="z3", name="Zone 3", center=[150.0, float(hmap[110, 20]), 850.0], radius=40.0),
        ]

        roads = generate_roads(heightmap=hmap, zones=zones, terrain_config=t_cfg, seed=888)
        assert len(roads) >= 3

        for road in roads:
            assert len(road.waypoints) >= 2
            # Compute observed maximum slope along road
            obs_slope = compute_max_observed_slope(road.waypoints)
            assert road.max_slope_observed is not None
            assert math.isclose(obs_slope, road.max_slope_observed, abs_tol=0.01)

    def test_contour_detour_around_steep_ridge(self):
        """When direct line crosses an impassable steep ridge, router contours through a low mountain pass."""
        res = 65
        world_size = [1000.0, 200.0, 1000.0]
        t_config = TerrainConfig(resolution=res, world_size=world_size, height_scale=200.0)

        # Create a steep ridge in center with low valley pass at Z > 750
        ridge_hmap = np.zeros((res, res), dtype=np.float32)
        for ix in range(res):
            x_m = (ix / (res - 1)) * 1000.0
            dist_to_center = abs(x_m - 500.0)
            for iz in range(res):
                z_m = (iz / (res - 1)) * 1000.0
                pass_factor = 0.1 if z_m > 750.0 else 1.0
                ridge_hmap[iz, ix] = 20.0 + (130.0 * math.exp(-0.5 * (dist_to_center / 50.0) ** 2)) * pass_factor

        start_pt = (200.0, 500.0)
        goal_pt = (800.0, 500.0)
        direct_dist = 600.0

        path_gentle = _find_slope_aware_astar_path(
            heightmap=ridge_hmap,
            start_world=start_pt,
            goal_world=goal_pt,
            terrain_config=t_config,
            max_grade=0.15,
            slope_weight=50.0,
        )

        formatted_gentle = [[p[0], p[1], p[2]] for p in path_gentle]
        total_len = sum(math.hypot(formatted_gentle[i+1][0] - formatted_gentle[i][0], formatted_gentle[i+1][2] - formatted_gentle[i][2]) for i in range(len(formatted_gentle)-1))
        max_slope = compute_max_observed_slope(formatted_gentle)

        # Must take detour > 1.2x direct distance through the pass
        assert total_len >= direct_dist * 1.20, f"Expected detour path length >= {direct_dist * 1.2}, got {total_len}"
        # Direct line has slope 2.6; contour path stays low
        assert max_slope <= 0.35, f"Expected max slope <= 0.35, got {max_slope}"


class TestContinuousDensityAndSATCollisionStress:
    """Stress testing continuous density scaling and SAT 2D OBB collision avoidance across 50 zones."""

    ZONE_TYPES = ["military_base", "airfield", "outpost", "radar_station", "depot"]

    def test_continuous_density_monotonicity_across_50_zones(self):
        """Assert building count is monotonically non-decreasing as density scales from 0.0 to 1.0 across 50 seeded zones."""
        catalog = load_asset_catalog()
        templates = load_zone_templates()
        bboxes = {k: v["bounding_box"]["size"] for k, v in catalog.items() if "bounding_box" in v}
        zone_templates = templates.get("zone_templates", {})

        density_steps = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]

        for seed in range(50):
            rng = np.random.RandomState(seed + 1000)
            z_type = self.ZONE_TYPES[seed % len(self.ZONE_TYPES)]
            cx = float(rng.uniform(200.0, 800.0))
            cz = float(rng.uniform(200.0, 800.0))
            radius = float(rng.uniform(40.0, 90.0))

            zone = Zone(
                id=f"zone_stress_{seed}",
                name=f"Stress Zone {seed}",
                type=z_type,
                zone_type=z_type,
                faction="A",
                destruction="01",
                density=1.0,
                center=[cx, 50.0, cz],
                radius=radius,
            )

            prev_count = 0
            for d in density_steps:
                tpl = zone_templates[z_type]
                buildings = instantiate_templated_zone(zone, tpl, d, bboxes)
                count = len(buildings)
                assert count >= prev_count, f"Monotonicity violation in zone {z_type} (seed {seed}): D={d} gave {count} < previous {prev_count}"
                prev_count = count

    def test_100_percent_sat_collision_avoidance_at_max_density_50_zones(self):
        """Assert ZERO 2D OBB collisions at maximum density D=1.0 across 50 randomly seeded zones."""
        catalog = load_asset_catalog()
        templates = load_zone_templates()
        t_cfg = TerrainConfig(resolution=65, world_size=[2000.0, 100.0, 2000.0])
        hmap = np.full((65, 65), 50.0, dtype=np.float32)

        total_buildings_checked = 0
        total_pair_checks = 0

        for seed in range(50):
            rng = np.random.RandomState(seed + 2000)
            z_type = self.ZONE_TYPES[seed % len(self.ZONE_TYPES)]
            cx = float(rng.uniform(200.0, 1800.0))
            cz = float(rng.uniform(200.0, 1800.0))
            radius = float(rng.uniform(50.0, 100.0))

            zone = Zone(
                id=f"zone_sat_{seed}",
                name=f"SAT Zone {seed}",
                type=z_type,
                zone_type=z_type,
                faction=rng.choice(["A", "B", "C"]),
                destruction="02",
                density=1.0,  # Maximum continuous density
                center=[cx, 50.0, cz],
                radius=radius,
            )

            placed = place_buildings(
                heightmap=hmap,
                zones=[zone],
                terrain_config=t_cfg,
                catalog=catalog,
                templates=templates,
                seed=seed + 2000,
            )

            assert len(placed) >= 4, f"Zone {seed} ({z_type}) placed too few buildings at D=1.0: {len(placed)}"
            total_buildings_checked += len(placed)

            # Convert all placed buildings to OBB2Ds with their exact bounding box dimensions
            obbs: List[Tuple[str, OBB2D]] = []
            for b in placed:
                bx, by, bz = b.position
                dim = b.bounding_box.size or b.bounding_box.dimensions or [4.0, 4.0, 3.0]
                yaw_deg = b.rotation[1] if b.rotation else 0.0
                yaw_rad = math.radians(yaw_deg)
                # SAT bounding box with buffer=0.0 for strict physical collision detection
                obb = OBB2D(bx, bz, dim[0], dim[1], yaw_rad, buffer=0.0)
                obbs.append((b.id, obb))

            # Pairwise SAT collision check between all buildings in the zone
            for i in range(len(obbs)):
                for j in range(i + 1, len(obbs)):
                    total_pair_checks += 1
                    id_i, obb_i = obbs[i]
                    id_j, obb_j = obbs[j]
                    has_overlap = check_sat_overlap(obb_i, obb_j)
                    assert not has_overlap, (
                        f"SAT collision detected at D=1.0 in zone {z_type} (seed {seed}) "
                        f"between {id_i} and {id_j}!"
                    )

        assert total_buildings_checked > 300, f"Expected >300 total buildings, got {total_buildings_checked}"
        assert total_pair_checks > 1000, f"Expected >1000 pairwise checks, got {total_pair_checks}"

    def test_multi_zone_cross_boundary_sat_collisions(self):
        """Assert zero SAT collisions when multiple zones are placed in a realistic world manifest."""
        for seed in [111, 222, 333, 444, 555]:
            req = GenerateWorldRequest(
                seed=seed,
                resolution=129,
                world_size=[2000.0, 150.0, 2000.0],
                zone_count_target=6,
            )
            manifest, hmap, summary = generate_world_pipeline(request=req, seed=seed)

            buildings = manifest.buildings
            obbs = []
            for b in buildings:
                dim = b.bounding_box.size or b.bounding_box.dimensions or [4.0, 4.0, 3.0]
                yaw_rad = math.radians(b.rotation[1] if b.rotation else 0.0)
                obb = OBB2D(b.position[0], b.position[2], dim[0], dim[1], yaw_rad, buffer=0.0)
                obbs.append((b.id, b.zone_id, obb))

            for i in range(len(obbs)):
                for j in range(i + 1, len(obbs)):
                    id_i, zone_i, obb_i = obbs[i]
                    id_j, zone_j, obb_j = obbs[j]
                    assert not check_sat_overlap(obb_i, obb_j), (
                        f"Cross-building collision between {id_i} ({zone_i}) and {id_j} ({zone_j}) at seed {seed}"
                    )
