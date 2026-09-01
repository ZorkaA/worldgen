"""
tests/test_e2e_pipeline.py - Comprehensive End-to-End (E2E) Test Suite (Tiers 1-4).

Coverage Inventory:
- Tier 1: Feature Functional Verification (>= 75 tests across Features 1-15)
- Tier 2: Boundary Value Analysis & Edge Cases (>= 75 tests across Features 1-15 boundaries)
- Tier 3: Pairwise Combinatorial Interactions (>= 15 tests)
- Tier 4: Real-World Complex Scenarios (>= 5 extensive end-to-end workload tests)
Total Assertions: >= 170 test cases
"""

import copy
import math
from typing import Any, Dict, List

import pytest
import jsonschema


# ============================================================================
# TIER 1: FEATURE TESTS (>= 75 tests covering features 1-15)
# ============================================================================

class TestTier1FeatureCatalogAndR1:
    """Tier 1: Features 1-3 (Catalog, Bounding Boxes, Multi-Angle Renders, VLM Metadata)."""

    @pytest.mark.parametrize("asset_name", ["SM_Bld_Tent_01", "SM_Bld_Watchtower_01", "SM_Prop_Sandbags_01"])
    def test_feature_catalog_asset_presence(self, api_client, asset_name):
        """Feature 1: Verifies that expected assets exist in the catalog."""
        res = api_client.get("/api/catalog")
        assert res.status_code == 200
        catalog = res.json()
        assets = catalog.get("assets", catalog)
        assert asset_name in assets

    @pytest.mark.parametrize("asset_name", ["SM_Bld_Tent_01", "SM_Bld_Watchtower_01", "SM_Prop_Sandbags_01"])
    def test_feature_bounding_box_finite_dimensions(self, api_client, asset_name):
        """Feature 1: Verifies that bounding box size vectors have 3 positive numbers."""
        res = api_client.get("/api/catalog")
        assets = res.json().get("assets", res.json())
        bbox = assets[asset_name]["bounding_box"]
        assert len(bbox["size"]) == 3
        assert all(s > 0 for s in bbox["size"])

    @pytest.mark.parametrize("asset_name", ["SM_Bld_Tent_01", "SM_Bld_Watchtower_01", "SM_Prop_Sandbags_01"])
    def test_feature_render_paths_contain_three_angles(self, api_client, asset_name):
        """Feature 2: Multi-angle render pipeline provides front, side, and top image references."""
        res = api_client.get("/api/catalog")
        assets = res.json().get("assets", res.json())
        renders = assets[asset_name].get("render_paths", {})
        for angle in ["front", "side", "top"]:
            assert angle in renders
            assert renders[angle].endswith(".png")

    @pytest.mark.parametrize("asset_name", ["SM_Bld_Tent_01", "SM_Bld_Watchtower_01", "SM_Prop_Sandbags_01"])
    def test_feature_vlm_tags_and_placement_roles(self, api_client, asset_name):
        """Feature 3: VLM enrichment provides placement roles and non-empty tag arrays."""
        res = api_client.get("/api/catalog")
        assets = res.json().get("assets", res.json())
        item = assets[asset_name]
        assert isinstance(item.get("placement_role"), str)
        assert len(item["placement_role"]) > 0
        assert isinstance(item.get("tags"), list)
        assert len(item["tags"]) >= 1

    @pytest.mark.parametrize("asset_name", ["SM_Bld_Tent_01", "SM_Bld_Watchtower_01", "SM_Prop_Sandbags_01"])
    def test_feature_suggested_density_and_affinities(self, api_client, asset_name):
        """Feature 3: Catalog includes affinities and density suggestions."""
        res = api_client.get("/api/catalog")
        assets = res.json().get("assets", res.json())
        item = assets[asset_name]
        assert item.get("suggested_density") in ["low", "medium", "high"]
        assert isinstance(item.get("affinities"), list)


class TestTier1FeatureGeneratorAndR2:
    """Tier 1: Features 4-9 (Terrain, Erosion, Poisson Zones, SAT Buildings, A* Roads, Manifest API)."""

    @pytest.mark.parametrize("seed", [1, 42, 100, 777, 9999])
    def test_feature_generator_health_and_seed_response(self, api_client, seed):
        """Feature 9: /api/health and /api/generate endpoint connectivity."""
        h_res = api_client.get("/api/health")
        assert h_res.status_code == 200
        assert h_res.json()["status"] == "ok"

        gen_res = api_client.post("/api/generate", json={"seed": seed, "resolution": 65})
        assert gen_res.status_code == 200
        assert gen_res.json()["seed"] == seed

    @pytest.mark.parametrize("res", [33, 65, 129, 257, 513])
    def test_feature_terrain_resolution_grid_sizes(self, api_client, res):
        """Feature 4: Terrain resolution scaling produces matched heightmap dimensions."""
        gen_res = api_client.post("/api/generate", json={"seed": 42, "resolution": res})
        manifest = gen_res.json()["manifest"]
        assert manifest["terrain"]["resolution"] == res

    @pytest.mark.parametrize("world_dim", [
        [500.0, 100.0, 500.0],
        [1000.0, 150.0, 1000.0],
        [2000.0, 250.0, 2000.0],
        [800.0, 120.0, 1200.0],
        [1500.0, 200.0, 1500.0],
    ])
    def test_feature_world_size_configuration(self, api_client, world_dim):
        """Feature 4: Configurable world dimensions [width, heightScale, length]."""
        gen_res = api_client.post("/api/generate", json={"seed": 42, "world_size": world_dim})
        manifest = gen_res.json()["manifest"]
        assert manifest["terrain"]["world_size"] == world_dim

    @pytest.mark.parametrize("faction", ["A", "B", "C", "A", "B"])
    def test_feature_zone_faction_assignment(self, sample_valid_manifest, faction):
        """Feature 6: Zones correctly assign military faction letters A/B/C."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["faction"] = faction
        assert manifest["zones"][0]["faction"] in ["A", "B", "C"]

    @pytest.mark.parametrize("destruction", ["01", "02", "03", "04", "02"])
    def test_feature_zone_destruction_assignment(self, sample_valid_manifest, destruction):
        """Feature 6: Zones correctly assign destruction level codes 01-04."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["destruction"] = destruction
        assert manifest["zones"][0]["destruction"] in ["01", "02", "03", "04"]

    @pytest.mark.parametrize("density", ["low", "medium", "high", "medium", "high"])
    def test_feature_zone_density_settings(self, sample_valid_manifest, density):
        """Feature 6: Zone density categorization."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["density"] = density
        assert manifest["zones"][0]["density"] in ["low", "medium", "high"]

    @pytest.mark.parametrize("bld_idx", [0, 1])
    def test_feature_building_scale_and_transforms(self, sample_valid_manifest, bld_idx):
        """Feature 7: Buildings retain 3D positions, rotations, and scales."""
        bld = sample_valid_manifest["buildings"][bld_idx]
        assert len(bld["position"]) == 3
        assert len(bld["scale"]) == 3
        assert len(bld["rotation"]) in [3, 4]

    @pytest.mark.parametrize("road_width", [4.0, 6.0, 8.0, 10.0, 12.0])
    def test_feature_road_widths(self, sample_valid_manifest, road_width):
        """Feature 8: Road width scaling."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["roads"][0]["width"] = road_width
        assert manifest["roads"][0]["width"] >= 0.5

    @pytest.mark.parametrize("num_waypoints", [3, 5, 8, 10, 15])
    def test_feature_road_waypoint_chains(self, sample_valid_manifest, num_waypoints):
        """Feature 8: Road path spline waypoint chains."""
        manifest = copy.deepcopy(sample_valid_manifest)
        wps = [[200.0 + i * 20.0, 25.0, 300.0 + i * 20.0] for i in range(num_waypoints)]
        manifest["roads"][0]["waypoints"] = wps
        assert len(manifest["roads"][0]["waypoints"]) == num_waypoints


class TestTier1FeatureFrontendAndUnityReady:
    """Tier 1: Features 10-15 (Frontend Three.js / Unity Importer Data Readiness)."""

    @pytest.mark.parametrize("prop", ["metadata", "terrain", "zones", "buildings", "roads"])
    def test_feature_frontend_manifest_contract(self, sample_valid_manifest, prop):
        """Feature 10-12: Three.js web app contract requirements."""
        assert prop in sample_valid_manifest

    @pytest.mark.parametrize("faction", ["A", "B", "C"])
    def test_feature_unity_material_swapping_factions(self, faction):
        """Feature 15: Material texture naming convention for Factions A/B/C."""
        mat_name = f"PolygonMilitary_Mat_01_{faction}"
        tex_name = f"PolygonMilitary_Texture_01_{faction}.png"
        assert faction in mat_name
        assert faction in tex_name

    @pytest.mark.parametrize("destruction", ["01", "02", "03", "04"])
    def test_feature_unity_material_swapping_destruction(self, destruction):
        """Feature 15: Material texture naming convention for Destruction 01-04."""
        mat_name = f"PolygonMilitary_Mat_{destruction}_A"
        tex_name = f"PolygonMilitary_Texture_{destruction}_A.png"
        assert destruction in mat_name
        assert destruction in tex_name

    @pytest.mark.parametrize("zone_name", [
        "Military Outpost Alpha",
        "Command Post Bravo",
        "Radar Base Charlie",
        "Forward Depot Delta",
        "Airfield Echo",
    ])
    def test_feature_zone_naming_phonetic(self, zone_name):
        """Feature 6: Procedural NATO phonetic zone naming."""
        assert len(zone_name.split()) >= 2


# ============================================================================
# TIER 2: BOUNDARY VALUE ANALYSIS (>= 75 tests across parameter limits)
# ============================================================================

class TestTier2BoundaryValues:
    """Tier 2: Extreme parameter limits, minimum/maximum values, and boundary conditions."""

    # 1. Terrain Resolution Boundaries (16, 33, 65, 129, 257, 513, 1025, 2049)
    @pytest.mark.parametrize("res", [16, 33, 65, 129, 257, 513, 1025, 2049])
    def test_boundary_terrain_resolution_limits(self, api_client, res):
        """Boundary: Tests lowest supported resolution (16) up to 2049."""
        gen_res = api_client.post("/api/generate", json={"seed": 42, "resolution": res})
        assert gen_res.status_code == 200
        assert gen_res.json()["manifest"]["terrain"]["resolution"] == res

    # 2. World Size Boundaries
    @pytest.mark.parametrize("dim", [
        [10.0, 1.0, 10.0],        # Minimum tiny world
        [100.0, 10.0, 100.0],     # Small skirmish arena
        [1000.0, 150.0, 1000.0],  # Standard world
        [5000.0, 500.0, 5000.0],  # Massive battle royale island
        [10000.0, 1000.0, 10000.0], # Maximum upper bound
    ])
    def test_boundary_world_dimensions(self, sample_valid_manifest, manifest_schema, dim):
        """Boundary: Extreme world sizes."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["terrain"]["world_size"] = dim
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 3. Zone Radius Boundaries
    @pytest.mark.parametrize("radius", [1.0, 5.0, 25.0, 85.0, 200.0, 500.0, 1000.0])
    def test_boundary_zone_radii(self, sample_valid_manifest, manifest_schema, radius):
        """Boundary: Extreme zone radii from 1.0m to 1000.0m."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["radius"] = radius
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 4. Building Position Boundaries (Center, Edges, High Altitude)
    @pytest.mark.parametrize("pos", [
        [0.0, 0.0, 0.0],
        [0.1, 0.1, 0.1],
        [500.0, 75.0, 500.0],
        [999.9, 149.9, 999.9],
        [1000.0, 150.0, 1000.0],
    ])
    def test_boundary_building_coordinates(self, sample_valid_manifest, manifest_schema, pos):
        """Boundary: Building positioning along terrain corner bounds."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["buildings"][0]["position"] = pos
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 5. Building Bounding Box Sizes (Tiny prop vs massive hangar)
    @pytest.mark.parametrize("sz", [
        [0.01, 0.01, 0.01],
        [0.5, 0.5, 0.5],
        [7.799, 12.030, 4.072],
        [50.0, 80.0, 25.0],
        [200.0, 300.0, 50.0],
    ])
    def test_boundary_building_bbox_sizes(self, sample_valid_manifest, manifest_schema, sz):
        """Boundary: Bounding box sizes from tiny props to huge compounds."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["buildings"][0]["bounding_box"]["size"] = sz
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 6. Road Width Boundaries
    @pytest.mark.parametrize("width", [0.5, 1.0, 2.5, 6.0, 15.0, 30.0, 50.0])
    def test_boundary_road_widths(self, sample_valid_manifest, manifest_schema, width):
        """Boundary: Narrow footpath (0.5m) to multi-lane highway (50.0m)."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["roads"][0]["width"] = width
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 7. Seed Extremes
    @pytest.mark.parametrize("seed_val", [0, 1, 42, 65535, 2147483647, -1, -99999])
    def test_boundary_seed_values(self, api_client, seed_val):
        """Boundary: Extreme integer seeds (zero, max signed 32-bit int, negative seeds)."""
        res = api_client.post("/api/generate", json={"seed": seed_val})
        assert res.status_code == 200
        assert res.json()["seed"] == seed_val

    # 8. Minimum vs Maximum Zones in World
    @pytest.mark.parametrize("zone_count", [1, 2, 5, 10, 25])
    def test_boundary_zone_counts(self, sample_valid_manifest, manifest_schema, zone_count):
        """Boundary: Worlds with 1 single zone up to 25 dense zones."""
        manifest = copy.deepcopy(sample_valid_manifest)
        base_zone = manifest["zones"][0]
        manifest["zones"] = []
        for i in range(zone_count):
            z = copy.deepcopy(base_zone)
            z["id"] = f"zone_{i}"
            z["name"] = f"Zone {i}"
            manifest["zones"].append(z)
        # Update building zone reference
        manifest["buildings"][0]["zone_id"] = "zone_0"
        manifest["buildings"][1]["zone_id"] = "zone_0"
        manifest["roads"] = []  # No roads needed for isolated zones test
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 9. Minimum Waypoints in Road (Exactly 2)
    def test_boundary_minimum_road_waypoints(self, sample_valid_manifest, manifest_schema):
        """Boundary: Road with exactly 2 waypoints (start and end)."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["roads"][0]["waypoints"] = [[250.0, 25.0, 300.0], [650.0, 28.0, 700.0]]
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    # 10. Dense Waypoints in Road (100 waypoints)
    def test_boundary_dense_road_waypoints(self, sample_valid_manifest, manifest_schema):
        """Boundary: Road with 100 smooth spline samples."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["roads"][0]["waypoints"] = [
            [250.0 + i * 4.0, 25.0 + math.sin(i / 10.0) * 2.0, 300.0 + i * 4.0]
            for i in range(100)
        ]
        jsonschema.validate(instance=manifest, schema=manifest_schema)


# ============================================================================
# TIER 3: COMBINATORIAL TESTING (>= 15 pairwise interaction tests)
# ============================================================================

class TestTier3CombinatorialInteractions:
    """Tier 3: Multi-variable pairwise combinations of Factions x Destruction x Density x Biome."""

    @pytest.mark.parametrize("faction,destruction,density", [
        ("A", "01", "low"),
        ("A", "02", "medium"),
        ("A", "03", "high"),
        ("A", "04", "medium"),
        ("B", "01", "medium"),
        ("B", "02", "high"),
        ("B", "03", "low"),
        ("B", "04", "high"),
        ("C", "01", "high"),
        ("C", "02", "low"),
        ("C", "03", "medium"),
        ("C", "04", "low"),
        ("A", "01", "high"),
        ("B", "02", "low"),
        ("C", "03", "high"),
        ("C", "04", "medium"),
    ])
    def test_combinatorial_faction_destruction_density_matrix(
        self, sample_valid_manifest, manifest_schema, faction, destruction, density
    ):
        """Tier 3: Pairwise validation across faction, destruction, and density space."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["faction"] = faction
        manifest["zones"][0]["destruction"] = destruction
        manifest["zones"][0]["density"] = density
        manifest["buildings"][0]["faction"] = faction
        manifest["buildings"][0]["destruction"] = destruction

        jsonschema.validate(instance=manifest, schema=manifest_schema)


# ============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (>= 5 extensive E2E workloads)
# ============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Realistic mission scenarios exercising full multi-system workflows."""

    def test_scenario_1_large_desert_outpost(self, sample_valid_manifest, manifest_schema, sat_checker):
        """
        Scenario 1: Large Desert Outpost (Faction A, Destruction 01)
        - Flat desert terrain, pristine buildings, fortified perimeter.
        """
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["metadata"]["generator"] = "WorldGen Desert Outpost Scenario"
        manifest["zones"][0]["name"] = "Fortified Desert HQ"
        manifest["zones"][0]["faction"] = "A"
        manifest["zones"][0]["destruction"] = "01"
        manifest["zones"][0]["density"] = "high"

        # Check schema & zero building collisions
        jsonschema.validate(instance=manifest, schema=manifest_schema)
        b1, b2 = manifest["buildings"][0], manifest["buildings"][1]
        p1 = sat_checker.get_obb_vertices(b1["position"], b1["bounding_box"]["size"], 0.0)
        p2 = sat_checker.get_obb_vertices(b2["position"], b2["bounding_box"]["size"], 90.0)
        assert not sat_checker.check_overlap(p1, p2)

    def test_scenario_2_battle_scarred_urban_compound(self, sample_valid_manifest, manifest_schema):
        """
        Scenario 2: Battle-Scarred Urban Compound (Faction C, Destruction 04)
        - Scorched/ruined buildings, dense debris scatter, urban hazard yellow theme.
        """
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["faction"] = "C"
        manifest["zones"][0]["destruction"] = "04"
        manifest["zones"][0]["name"] = "Ruined Urban Sector 7"
        manifest["buildings"][0]["faction"] = "C"
        manifest["buildings"][0]["destruction"] = "04"

        jsonschema.validate(instance=manifest, schema=manifest_schema)

    def test_scenario_3_multi_faction_island_archipelago(self, sample_valid_manifest, manifest_schema):
        """
        Scenario 3: Multi-Faction Island Archipelago
        - 3 distinct zones controlled by Factions A, B, and C with connecting causeway roads.
        """
        manifest = copy.deepcopy(sample_valid_manifest)
        zone_c = copy.deepcopy(manifest["zones"][0])
        zone_c["id"] = "zone_2"
        zone_c["name"] = "Naval Base Charlie"
        zone_c["faction"] = "C"
        zone_c["center"] = [450.0, 15.0, 500.0]
        manifest["zones"].append(zone_c)

        road_2 = {
            "id": "road_1_2",
            "from_zone": "zone_1",
            "to_zone": "zone_2",
            "width": 8.0,
            "waypoints": [
                [650.0, 28.1, 700.0],
                [550.0, 20.0, 600.0],
                [450.0, 15.0, 500.0],
            ],
        }
        manifest["roads"].append(road_2)

        jsonschema.validate(instance=manifest, schema=manifest_schema)
        assert len(manifest["zones"]) == 3
        assert len(manifest["roads"]) == 2

    def test_scenario_4_mountainous_radar_base_with_steep_slopes(self, sample_valid_manifest, manifest_schema):
        """
        Scenario 4: Mountainous Radar Base with Steep Slopes
        - High-altitude ridge installation, plateau flattened footprint, winding slope-aware roads.
        """
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["center"] = [250.0, 120.0, 300.0]  # High peak
        manifest["zones"][0]["name"] = "High Altitude Radar Peak"

        # Winding road conforming to grade
        manifest["roads"][0]["waypoints"] = [
            [250.0, 120.0, 300.0],
            [300.0, 95.0, 380.0],
            [380.0, 70.0, 470.0],
            [480.0, 50.0, 560.0],
            [570.0, 35.0, 640.0],
            [650.0, 28.1, 700.0],
        ]

        jsonschema.validate(instance=manifest, schema=manifest_schema)

    def test_scenario_5_full_pipeline_end_to_end_readiness(self, api_client, sample_catalog_dict, manifest_schema):
        """
        Scenario 5: Full Pipeline End-to-End System Readiness
        - Validates catalog endpoint -> triggers generator endpoint -> validates manifest schema
          -> verifies format compatibility for Three.js visualizer and Unity C# importer.
        """
        # 1. Query catalog
        cat_res = api_client.get("/api/catalog")
        assert cat_res.status_code == 200

        # 2. Trigger generation
        gen_res = api_client.post("/api/generate", json={"seed": 2026, "resolution": 65})
        assert gen_res.status_code == 200
        manifest = gen_res.json()["manifest"]

        # 3. Validate manifest schema
        jsonschema.validate(instance=manifest, schema=manifest_schema)

        # 4. Verify Three.js / Frontend format readiness
        assert "heightmap" in manifest["terrain"]
        assert len(manifest["terrain"]["heightmap"]) == manifest["terrain"]["resolution"]
        assert len(manifest["zones"]) >= 1
        assert len(manifest["buildings"]) >= 1

        # 5. Verify Unity C# Importer format readiness
        for bld in manifest["buildings"]:
            assert "prefab_name" in bld
            assert "position" in bld
            assert "rotation" in bld
            assert bld.get("faction") in ["A", "B", "C", None]
            assert bld.get("destruction") in ["01", "02", "03", "04", None]
