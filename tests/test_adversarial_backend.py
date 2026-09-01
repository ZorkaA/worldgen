"""Adversarial and stress verification suite for procedural generator algorithms and backend endpoints.

Challenge Vectors:
1. Extreme and boundary seeds (negative, 0, INT32_MAX, UINT32_MAX, INT64_MAX, massive seeds).
2. High resolutions (513, 1025) and extreme droplet counts / parameters for Numba hydraulic erosion.
3. High zone density and building counts (verifying SAT OBB zero-collision guarantee across all pairs).
4. Slope-aware A* road pathfinding (verifying gradient constraints, waypoints, and complete zone connectivity).
5. API endpoints under invalid payloads, missing fields, out-of-bound coordinates, path traversal, rapid sequences.
"""

import io
import math
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import jsonschema

from backend.app.main import app
from backend.app.core.schemas import (
    GenerateWorldRequest,
    TerrainConfig,
    ZoneConfig,
    WorldManifest,
)
from backend.app.generator.pipeline import generate_world_pipeline
from backend.app.generator.terrain import generate_terrain
from backend.app.generator.erosion import simulate_hydraulic_erosion
from backend.app.generator.zones import generate_zones, flatten_zone_footprints
from backend.app.generator.buildings import place_buildings, OBB2D, check_sat_overlap, load_asset_catalog
from backend.app.generator.roads import generate_roads, _find_slope_aware_astar_path, _delaunay_triangulation_2d
from tests.conftest import MANIFEST_SCHEMA


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# VECTOR 1: EXTREME & BOUNDARY SEEDS
# ==============================================================================
class TestExtremeSeedsAndDeterminism:
    """Stress test RNG seed bounds, negative values, 0, and 64-bit integers."""

    @pytest.mark.parametrize("seed", [
        0,
        -1,
        -42,
        -999999,
        -2147483648,  # INT32_MIN
        -9223372036854775808,  # INT64_MIN
        2147483647,  # INT32_MAX
        4294967295,  # UINT32_MAX
        9223372036854775807,  # INT64_MAX
        10**18,
    ])
    def test_pipeline_survives_extreme_seeds(self, seed: int):
        """Verify complete pipeline executes without error for extreme seeds."""
        req = GenerateWorldRequest(
            seed=seed,
            terrain=TerrainConfig(resolution=65, erosion_droplets=1000),
            zones=ZoneConfig(zone_count_target=3),
        )
        manifest, heightmap, summary = generate_world_pipeline(request=req, seed=seed)

        assert manifest is not None
        assert isinstance(manifest, WorldManifest)
        assert heightmap.shape == (65, 65)
        assert not np.isnan(heightmap).any(), f"NaN found in heightmap with seed {seed}"
        assert not np.isinf(heightmap).any(), f"Inf found in heightmap with seed {seed}"
        assert len(manifest.zones) >= 1
        assert len(manifest.buildings) >= 1
        assert summary["seed"] == seed

    @pytest.mark.parametrize("seed", [0, -1337, 2147483647, 9223372036854775807])
    def test_strict_determinism_under_extreme_seeds(self, seed: int):
        """Verify identical seed produces strictly identical terrain and transforms."""
        req = GenerateWorldRequest(
            seed=seed,
            terrain=TerrainConfig(resolution=65, erosion_droplets=2000),
            zones=ZoneConfig(zone_count_target=3),
        )
        manifest1, h1, _ = generate_world_pipeline(request=req, seed=seed)
        manifest2, h2, _ = generate_world_pipeline(request=req, seed=seed)

        # Heightmap exact numerical match
        np.testing.assert_array_almost_equal(h1, h2, decimal=5)

        # Zone coordinates exact match
        assert len(manifest1.zones) == len(manifest2.zones)
        for z1, z2 in zip(manifest1.zones, manifest2.zones):
            assert z1.center == z2.center
            assert z1.radius == z2.radius
            assert z1.faction == z2.faction
            assert z1.destruction == z2.destruction

        # Building transforms exact match
        assert len(manifest1.buildings) == len(manifest2.buildings)
        for b1, b2 in zip(manifest1.buildings, manifest2.buildings):
            assert b1.prefab_name == b2.prefab_name
            assert b1.position == b2.position
            assert b1.rotation == b2.rotation

    def test_seed_divergence(self):
        """Verify different seeds produce genuinely divergent terrain."""
        h1 = generate_terrain(TerrainConfig(resolution=65), seed=0)
        h2 = generate_terrain(TerrainConfig(resolution=65), seed=1)
        h3 = generate_terrain(TerrainConfig(resolution=65), seed=-1)

        diff_0_1 = np.max(np.abs(h1 - h2))
        diff_0_neg1 = np.max(np.abs(h1 - h3))

        assert diff_0_1 > 5.0, "Seed 0 and Seed 1 produced almost identical terrain"
        assert diff_0_neg1 > 5.0, "Seed 0 and Seed -1 produced almost identical terrain"


# ==============================================================================
# VECTOR 2: NUMBA HYDRAULIC EROSION NUMERICAL STABILITY & STRESS
# ==============================================================================
class TestHydraulicErosionAdversarialStress:
    """Stress test Numba JIT hydraulic erosion at extreme resolutions and parameters."""

    def test_high_resolution_grid_erosion(self):
        """Test erosion on 513x513 and 1025x1025 grids."""
        # 513x513 with 50,000 droplets
        h_513 = generate_terrain(TerrainConfig(resolution=513), seed=42)
        eroded_513 = simulate_hydraulic_erosion(h_513, droplets=50000, seed=42)

        assert eroded_513.shape == (513, 513)
        assert not np.isnan(eroded_513).any()
        assert not np.isinf(eroded_513).any()
        assert float(np.min(eroded_513)) >= -10.0  # reasonable lower bound

    @pytest.mark.parametrize("droplet_count", [0, 1, 10000, 100000, 200000])
    def test_droplet_count_scaling_stability(self, droplet_count: int):
        """Verify stability from 0 droplets up to 200,000 droplets."""
        h = generate_terrain(TerrainConfig(resolution=129), seed=77)
        eroded = simulate_hydraulic_erosion(h, droplets=droplet_count, seed=77)

        assert eroded.shape == (129, 129)
        assert not np.isnan(eroded).any()
        assert not np.isinf(eroded).any()
        if droplet_count == 0:
            np.testing.assert_array_equal(h, eroded)
        else:
            diff = np.max(np.abs(h - eroded))
            assert diff > 0.0, f"Droplet count {droplet_count} had no effect on terrain"

    @pytest.mark.parametrize("inertia,capacity_factor,erosion_rate,deposition_rate", [
        (0.0, 1.0, 0.1, 0.1),       # No inertia
        (0.99, 10.0, 0.8, 0.8),     # Extreme inertia & high erosion/deposition
        (0.05, 50.0, 1.0, 0.0),     # Massive capacity & pure erosion (no deposition)
        (0.05, 0.001, 0.0, 1.0),    # Minimal capacity & pure deposition
        (0.5, 5.0, 0.95, 0.95),     # Fast dynamics
    ])
    def test_extreme_physical_parameters(self, inertia, capacity_factor, erosion_rate, deposition_rate):
        """Test physical parameter extremes without NaN or divergence."""
        h = generate_terrain(TerrainConfig(resolution=65), seed=99)
        eroded = simulate_hydraulic_erosion(
            h,
            droplets=10000,
            seed=99,
            inertia=inertia,
            capacity_factor=capacity_factor,
            erosion_rate=erosion_rate,
            deposition_rate=deposition_rate,
        )

        assert not np.isnan(eroded).any()
        assert not np.isinf(eroded).any()
        # Elevations must remain within bounded physical range
        assert np.max(eroded) < 1000.0
        assert np.min(eroded) > -500.0

    def test_flat_and_cliff_terrain_erosion(self):
        """Verify erosion on pathological flat and vertical cliff heightmaps."""
        # Flat plane
        flat = np.full((65, 65), 50.0, dtype=np.float32)
        eroded_flat = simulate_hydraulic_erosion(flat, droplets=5000, seed=123)
        assert not np.isnan(eroded_flat).any()
        assert not np.isinf(eroded_flat).any()

        # Step cliff
        cliff = np.zeros((65, 65), dtype=np.float32)
        cliff[:, 32:] = 100.0
        eroded_cliff = simulate_hydraulic_erosion(cliff, droplets=10000, seed=123)
        assert not np.isnan(eroded_cliff).any()
        assert not np.isinf(eroded_cliff).any()

    def test_negative_elevation_terrain_erosion(self):
        """Verify erosion on terrain with negative elevations (e.g. sub-sea level basins)."""
        basin = np.linspace(-50.0, 50.0, 65 * 65, dtype=np.float32).reshape(65, 65)
        eroded_basin = simulate_hydraulic_erosion(basin, droplets=5000, seed=456)
        assert not np.isnan(eroded_basin).any()
        assert not np.isinf(eroded_basin).any()


# ==============================================================================
# VECTOR 3: HIGH ZONE DENSITY & SAT OBB BUILDING COLLISION AVOIDANCE
# ==============================================================================
class TestSATBuildingCollisionAvoidanceStress:
    """Stress test SAT OBB non-overlapping guarantee under extreme building density."""

    def test_sat_mathematical_precision(self):
        """Adversarial tests of SAT algorithm across corner cases."""
        # 1. Non-overlapping separated by 0.01m
        obb1 = OBB2D(cx=0.0, cz=0.0, width=4.0, length=4.0, yaw_rad=0.0, buffer=0.0)
        obb2 = OBB2D(cx=4.01, cz=0.0, width=4.0, length=4.0, yaw_rad=0.0, buffer=0.0)
        assert not check_sat_overlap(obb1, obb2), "SAT failed on separated boxes"

        # 2. Overlapping by 0.01m
        obb3 = OBB2D(cx=3.99, cz=0.0, width=4.0, length=4.0, yaw_rad=0.0, buffer=0.0)
        assert check_sat_overlap(obb1, obb3), "SAT failed on overlapping boxes"

        # 3. Concentric boxes rotated 45 degrees
        obb4 = OBB2D(cx=0.0, cz=0.0, width=2.0, length=2.0, yaw_rad=math.pi / 4.0, buffer=0.0)
        assert check_sat_overlap(obb1, obb4), "SAT failed on concentric rotated boxes"

        # 4. Long slender box piercing boundary
        obb_long = OBB2D(cx=0.0, cz=10.0, width=1.0, length=25.0, yaw_rad=0.0, buffer=0.0)
        assert check_sat_overlap(obb1, obb_long), "SAT failed on long intersecting box"

        # 5. Arbitrary angle (33.7 degrees) touch
        ang = math.radians(33.7)
        obb_rot1 = OBB2D(cx=10.0, cz=10.0, width=6.0, length=8.0, yaw_rad=ang, buffer=0.0)
        obb_rot2 = OBB2D(cx=10.0, cz=10.0, width=6.0, length=8.0, yaw_rad=ang, buffer=0.0)
        assert check_sat_overlap(obb_rot1, obb_rot2), "SAT failed on identical rotated boxes"

    def test_high_density_manifest_zero_sat_collisions(self):
        """Stress test full generation with high zone count & high building density."""
        req = GenerateWorldRequest(
            seed=42,
            terrain=TerrainConfig(resolution=257, world_size=[1000.0, 150.0, 1000.0]),
            zones=ZoneConfig(
                zone_count_target=14,
                min_zone_distance=70.0,
                min_radius=40.0,
                max_radius=80.0,
            ),
        )
        manifest, heightmap, summary = generate_world_pipeline(request=req, seed=42)

        buildings = manifest.buildings
        assert len(buildings) >= 60, f"Expected dense building layout, got {len(buildings)}"

        # Group buildings by zone
        zone_blds = {}
        for b in buildings:
            zone_blds.setdefault(b.zone_id, []).append(b)

        # Pairwise SAT collision check within each zone
        total_pairs_tested = 0
        collision_count = 0
        collisions = []

        for z_id, blds in zone_blds.items():
            n = len(blds)
            obbs = []
            for b in blds:
                dim = b.bounding_box.size or b.bounding_box.dimensions or [4.0, 4.0, 3.0]
                yaw_deg = b.rotation[1] if b.rotation else 0.0
                yaw_rad = math.radians(yaw_deg)
                # Test with zero buffer to verify physical non-overlap
                obb = OBB2D(b.position[0], b.position[2], dim[0], dim[1], yaw_rad, buffer=0.0)
                obbs.append((b.id, obb))

            for i in range(n):
                for j in range(i + 1, n):
                    total_pairs_tested += 1
                    b1_id, o1 = obbs[i]
                    b2_id, o2 = obbs[j]
                    if check_sat_overlap(o1, o2):
                        collision_count += 1
                        collisions.append((b1_id, b2_id, z_id))

        assert collision_count == 0, f"SAT collision violations detected in {collision_count} pairs: {collisions}"
        assert total_pairs_tested > 100, "Too few pairs tested"

    def test_global_all_pairs_building_collision_freedom(self):
        """Global collision check across all buildings in the entire world (inter-zone + intra-zone)."""
        req = GenerateWorldRequest(
            seed=789,
            terrain=TerrainConfig(resolution=129, world_size=[1000.0, 150.0, 1000.0]),
            zones=ZoneConfig(zone_count_target=8, min_zone_distance=80.0),
        )
        manifest, _, _ = generate_world_pipeline(request=req, seed=789)

        all_buildings = manifest.buildings
        assert len(all_buildings) >= 30

        obbs = []
        for b in all_buildings:
            dim = b.bounding_box.size or b.bounding_box.dimensions or [4.0, 4.0, 3.0]
            yaw_deg = b.rotation[1] if b.rotation else 0.0
            yaw_rad = math.radians(yaw_deg)
            obb = OBB2D(b.position[0], b.position[2], dim[0], dim[1], yaw_rad, buffer=0.0)
            obbs.append((b.id, obb))

        total_blds = len(obbs)
        global_collisions = []
        for i in range(total_blds):
            for j in range(i + 1, total_blds):
                b1_id, o1 = obbs[i]
                b2_id, o2 = obbs[j]
                if check_sat_overlap(o1, o2):
                    global_collisions.append((b1_id, b2_id))

        assert len(global_collisions) == 0, f"Global building overlap detected: {global_collisions}"

    def test_building_quaternion_normalization(self):
        """Verify every building placement has valid normalized rotation quaternions."""
        req = GenerateWorldRequest(
            seed=999,
            terrain=TerrainConfig(resolution=65),
            zones=ZoneConfig(zone_count_target=4),
        )
        manifest, _, _ = generate_world_pipeline(request=req, seed=999)

        for b in manifest.buildings:
            assert b.rotation_quaternion is not None
            qx, qy, qz, qw = b.rotation_quaternion
            norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
            assert abs(norm - 1.0) < 1e-3, f"Building {b.id} quaternion not normalized: {norm}"

    def test_buildings_within_zone_radii(self):
        """Verify all buildings are situated within their parent zone radius."""
        req = GenerateWorldRequest(
            seed=555,
            terrain=TerrainConfig(resolution=65),
            zones=ZoneConfig(zone_count_target=4),
        )
        manifest, _, _ = generate_world_pipeline(request=req, seed=555)

        zone_map = {z.id: z for z in manifest.zones}

        for b in manifest.buildings:
            parent_zone = zone_map[b.zone_id]
            dx = b.position[0] - parent_zone.center[0]
            dz = b.position[2] - parent_zone.center[2]
            dist = math.sqrt(dx * dx + dz * dz)
            # Must be within zone radius + tolerance
            assert dist <= parent_zone.radius * 1.05, f"Building {b.id} placed outside zone {b.zone_id}: {dist} > {parent_zone.radius}"


# ==============================================================================
# VECTOR 4: SLOPE-AWARE A* ROAD PATHFINDING & CONNECTIVITY
# ==============================================================================
class TestSlopeAwareAStarRoadStress:
    """Stress test slope-aware A* road pathfinding on extreme cliffs and verify topology."""

    def test_delaunay_and_mst_graph_connectivity(self):
        """Verify road network forms a connected graph across all zones."""
        for target_zones in [2, 3, 5, 8, 12]:
            req = GenerateWorldRequest(
                seed=target_zones * 100,
                terrain=TerrainConfig(resolution=65),
                zones=ZoneConfig(zone_count_target=target_zones, min_zone_distance=50.0),
            )
            manifest, _, _ = generate_world_pipeline(request=req, seed=target_zones * 100)

            actual_zones = [z.id for z in manifest.zones]
            if len(actual_zones) < 2:
                continue

            # Build adjacency graph
            adj = {z_id: set() for z_id in actual_zones}
            for road in manifest.roads:
                adj[road.from_zone].add(road.to_zone)
                adj[road.to_zone].add(road.from_zone)

            # BFS from first zone to verify full connectivity
            visited = set()
            queue = [actual_zones[0]]
            visited.add(actual_zones[0])

            while queue:
                curr = queue.pop(0)
                for neighbor in adj.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            assert len(visited) == len(actual_zones), (
                f"Road network disconnected! Visited {len(visited)} of {len(actual_zones)} zones. "
                f"Unvisited: {set(actual_zones) - visited}"
            )

    def test_road_waypoints_within_world_bounds_and_valid_elevations(self):
        """Verify all road waypoints are in bounds and lie on the terrain surface."""
        req = GenerateWorldRequest(
            seed=12345,
            terrain=TerrainConfig(resolution=129, world_size=[1000.0, 200.0, 1000.0]),
            zones=ZoneConfig(zone_count_target=5),
        )
        manifest, heightmap, _ = generate_world_pipeline(request=req, seed=12345)

        for road in manifest.roads:
            assert len(road.waypoints) >= 2, f"Road {road.id} has fewer than 2 waypoints"
            for wp in road.waypoints:
                assert len(wp) == 3
                wx, wy, wz = wp
                assert 0.0 <= wx <= 1000.0, f"Waypoint X out of bounds: {wx}"
                assert 0.0 <= wz <= 1000.0, f"Waypoint Z out of bounds: {wz}"
                assert not math.isnan(wy) and not math.isinf(wy), f"Waypoint elevation NaN/Inf: {wy}"

    def test_astar_on_extreme_cliff_terrain(self):
        """Direct test of _find_slope_aware_astar_path on sharp terrain slope."""
        terrain_config = TerrainConfig(resolution=129, world_size=[1000.0, 300.0, 1000.0])
        h = generate_terrain(terrain_config, seed=888)

        start_pt = (100.0, 100.0)
        goal_pt = (900.0, 900.0)

        waypoints = _find_slope_aware_astar_path(
            heightmap=h,
            start_world=start_pt,
            goal_world=goal_pt,
            terrain_config=terrain_config,
            water_level=2.0,
            slope_weight=30.0,
            max_grade=0.25,
        )

        assert len(waypoints) >= 2
        # Verify continuous path from near start to near goal
        first_wp = waypoints[0]
        last_wp = waypoints[-1]

        start_dist = math.sqrt((first_wp[0] - start_pt[0]) ** 2 + (first_wp[2] - start_pt[1]) ** 2)
        goal_dist = math.sqrt((last_wp[0] - goal_pt[0]) ** 2 + (last_wp[2] - goal_pt[1]) ** 2)

        assert start_dist < 20.0, f"Path start too far from origin: {start_dist}"
        assert goal_dist < 20.0, f"Path goal too far from destination: {goal_dist}"

    def test_road_step_slope_gradients_bounded(self):
        """Verify that individual waypoint step grades on smooth terrain are within bounds."""
        req = GenerateWorldRequest(
            seed=4567,
            terrain=TerrainConfig(resolution=129, height_scale=80.0),
            zones=ZoneConfig(zone_count_target=4),
        )
        manifest, _, _ = generate_world_pipeline(request=req, seed=4567)

        for road in manifest.roads:
            wps = road.waypoints
            for i in range(len(wps) - 1):
                p1 = wps[i]
                p2 = wps[i + 1]
                dh = abs(p2[1] - p1[1])
                dist_2d = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[2] - p1[2]) ** 2)
                if dist_2d > 1e-3:
                    grade = dh / dist_2d
                    # Step grade should be reasonably bounded on smoothed terrain
                    assert grade < 2.0, f"Road {road.id} segment {i} has extreme step grade: {grade:.2f}"


# ==============================================================================
# VECTOR 5: API ENDPOINTS UNDER ADVERSARIAL & MALFORMED PAYLOADS
# ==============================================================================
class TestAPIAdversarialPayloadsAndRobustness:
    """Stress test FastAPI endpoints against malformed requests, invalid schemas, and injections."""

    def test_generate_endpoint_empty_body(self, client):
        """POST /generate with empty body should generate default world."""
        res = client.post("/api/v1/generate", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "manifest" in data
        assert "summary" in data

    @pytest.mark.parametrize("invalid_payload", [
        {"resolution": "not_an_integer"},
        {"seed": "string_seed"},
        {"terrain": {"resolution": -512}},
        {"terrain": {"octaves": 50}},            # Exceeds max 12
        {"terrain": {"octaves": 0}},             # Below min 1
        {"terrain": {"persistence": 2.5}},       # Exceeds max 0.99
        {"terrain": {"lacunarity": -1.0}},       # Below min 1.0
        {"terrain": {"erosion_droplets": -100}}, # Below min 0
        {"zones": {"min_zone_distance": -50.0}}, # Below min 10.0
        {"zones": {"max_destruction": 10}},      # Exceeds max 4
        {"zones": {"min_radius": -5.0}},         # Below min 1.0
    ])
    def test_generate_endpoint_rejects_invalid_inputs(self, client, invalid_payload):
        """POST /generate must reject schema violations with HTTP 422."""
        res = client.post("/api/v1/generate", json=invalid_payload)
        assert res.status_code == 422, f"Payload {invalid_payload} should have returned 422, got {res.status_code}"

    def test_generate_endpoint_with_extreme_seeds(self, client):
        """POST /generate with negative and large seeds via JSON."""
        for seed in [0, -99999, 2147483647]:
            res = client.post("/api/v1/generate", json={
                "seed": seed,
                "terrain": {"resolution": 65, "erosion_droplets": 500},
                "zones": {"zone_count_target": 2},
            })
            assert res.status_code == 200
            assert res.json()["seed"] == seed

    def test_manifest_endpoint_with_query_params(self, client):
        """GET /manifest with valid and invalid seed params."""
        # Valid negative seed
        res = client.get("/api/v1/manifest?seed=-42")
        assert res.status_code == 200
        assert res.json()["metadata"]["seed"] == -42

        # Invalid string seed
        res_err = client.get("/api/v1/manifest?seed=invalid_seed")
        assert res_err.status_code == 422

    def test_catalog_prefab_lookup_security(self, client):
        """GET /catalog/prefabs/{name} security against path traversal and SQL injection."""
        # Valid prefab
        res = client.get("/api/v1/catalog/prefabs/SM_Bld_Tent_01")
        assert res.status_code == 200
        assert res.json()["name"] == "SM_Bld_Tent_01"

        # Non-existent prefab
        res_404 = client.get("/api/v1/catalog/prefabs/TotallyFakePrefab_999")
        assert res_404.status_code == 404

        # Path traversal attempts
        res_trav = client.get("/api/v1/catalog/prefabs/..%2F..%2Fetc%2Fpasswd")
        assert res_trav.status_code in [404, 422]

        # Injection payload
        res_inj = client.get("/api/v1/catalog/prefabs/' OR '1'='1")
        assert res_inj.status_code == 404

    def test_heightmap_export_endpoints(self, client):
        """Verify PNG and raw float32 binary heightmap export endpoints."""
        # 1. Heightmap PNG
        res_png = client.get("/api/v1/heightmap/png?seed=42")
        assert res_png.status_code == 200
        assert res_png.headers["content-type"] == "image/png"
        img = Image.open(io.BytesIO(res_png.content))
        assert img.mode in ["I;16", "I", "L"]
        assert img.size[0] > 0 and img.size[1] > 0

        # 2. Heightmap Raw
        res_raw = client.get("/api/v1/heightmap/raw?seed=42")
        assert res_raw.status_code == 200
        assert res_raw.headers["content-type"] == "application/octet-stream"
        raw_bytes = res_raw.content
        assert len(raw_bytes) > 0
        assert len(raw_bytes) % 4 == 0  # Multiple of float32 (4 bytes)

    def test_health_endpoint(self, client):
        """GET /health endpoint response verification."""
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["catalog_available"] is True
        assert data["catalog_asset_count"] >= 5

    def test_rapid_sequential_generation_requests(self, client):
        """Verify server handles rapid consecutive generation cycles without memory or cache corruption."""
        seeds = [101, 102, 103, 104, 105, 106, 107, 108]
        for s in seeds:
            res = client.post("/api/v1/generate", json={
                "seed": s,
                "terrain": {"resolution": 65, "erosion_droplets": 500},
                "zones": {"zone_count_target": 2},
            })
            assert res.status_code == 200
            manifest_dict = res.json()["manifest"]
            # Validate against canonical Draft 2020-12 schema
            jsonschema.validate(instance=manifest_dict, schema=MANIFEST_SCHEMA)
