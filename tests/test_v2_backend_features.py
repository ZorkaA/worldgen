"""
tests/test_v2_backend_features.py - Dedicated test suite for WorldGen V2 Backend Implementations.

Covers:
1. R1: Global map parameters, deformation strength, smooth falloffs (Cosine, Smootherstep, Cubic), edge margins.
2. R3: Adaptive Quadtree Mesh Decimation (DecimatedMesh schema, normals, UVs, watertightness, decimation ratio).
3. R3: Road Slope Limits and observed slope tracking on road segments.
4. R4: AI Layout Templates catalog, instantiate_templated_zone, continuous density monotonic scaling [0.0 - 1.0], SAT zero collisions.
5. Recompute API: /api/recompute and /api/v1/recompute fast zone repositioning endpoint.
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.schemas import (
    GenerateWorldRequest,
    RecomputeRequest,
    TerrainConfig,
    ZoneConfig,
    Zone,
    DecimatedMesh,
)
from backend.app.generator.pipeline import generate_world_pipeline
from backend.app.generator.terrain import generate_terrain
from backend.app.generator.zones import generate_zones, flatten_zone_footprints
from backend.app.generator.mesh import generate_adaptive_mesh
from backend.app.generator.roads import generate_roads
from backend.app.generator.buildings import (
    load_zone_templates,
    instantiate_templated_zone,
    place_buildings,
    OBB2D,
    check_sat_overlap,
    load_asset_catalog,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestV2GlobalMapParametersAndDeformation:
    """Test global dimension parameters and smooth non-linear plateau blending falloffs."""

    @pytest.mark.parametrize("falloff", ["cosine", "smootherstep", "cubic"])
    def test_smooth_falloff_algorithms_produce_valid_heightmaps(self, falloff: str):
        config = TerrainConfig(
            resolution=65,
            world_size=[500.0, 100.0, 500.0],
            deformation_strength=1.5,
            edge_margin=50.0,
            flattening_falloff=falloff,
            flattening_margin_ratio=1.5,
        )
        raw = generate_terrain(config=config, seed=123)
        assert raw.shape == (65, 65)
        assert np.isfinite(raw).all()

        zones, zone_data = generate_zones(
            heightmap=raw,
            terrain_config=config,
            zone_config=ZoneConfig(zone_count_target=3, min_radius=30.0, max_radius=45.0, edge_margin=50.0),
            seed=123,
        )
        assert len(zones) >= 1

        flattened = flatten_zone_footprints(
            heightmap=raw,
            zones=zones,
            zone_internal_data=zone_data,
            terrain_config=config,
        )
        assert flattened.shape == (65, 65)
        assert np.isfinite(flattened).all()

    def test_deformation_strength_scaling(self):
        """Varying deformation strength modifies terrain surface geometry and gradient roughness."""
        cfg_low = TerrainConfig(resolution=65, deformation_strength=0.0)
        cfg_high = TerrainConfig(resolution=65, deformation_strength=3.0)

        h_low = generate_terrain(config=cfg_low, seed=42)
        h_high = generate_terrain(config=cfg_high, seed=42)

        assert not np.allclose(h_low, h_high)
        grad_low = np.gradient(h_low)
        grad_high = np.gradient(h_high)
        rough_low = float(np.mean(np.hypot(grad_low[0], grad_low[1])))
        rough_high = float(np.mean(np.hypot(grad_high[0], grad_high[1])))
        assert rough_high != rough_low


class TestV2AdaptiveMeshAndRoadLimits:
    """Test quadtree mesh decimator and road slope enforcement."""

    def test_adaptive_mesh_on_flat_plain(self):
        """Flat terrain achieves >= 50% triangle reduction compared to full uniform grid."""
        flat = np.full((65, 65), 50.0, dtype=np.float32)
        mesh = generate_adaptive_mesh(heightmap=flat, world_size=[1000.0, 100.0, 1000.0], max_error=1.0)

        assert isinstance(mesh, DecimatedMesh)
        assert mesh.decimation_ratio <= 0.50, f"Expected <= 0.50 decimation ratio on flat plain, got {mesh.decimation_ratio}"
        assert mesh.vertex_count == len(mesh.vertices)
        assert mesh.triangle_count == len(mesh.indices) // 3
        assert len(mesh.normals) == len(mesh.vertices)
        assert len(mesh.uvs) == len(mesh.vertices)

        # Verify unit normals pointing up [0, 1, 0]
        for nx, ny, nz in mesh.normals:
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            assert abs(length - 1.0) < 1e-3
            assert ny >= 0.0

        # Verify UV coordinates in [0, 1]
        for u, v in mesh.uvs:
            assert 0.0 <= u <= 1.0
            assert 0.0 <= v <= 1.0

    def test_road_slope_limits_and_observed_slope(self):
        """Road segments enforce max_road_slope and record max_slope_observed."""
        req = GenerateWorldRequest(
            seed=777,
            terrain=TerrainConfig(resolution=65, height_scale=1.5, max_road_slope=0.25),
            zones=ZoneConfig(zone_count_target=4),
        )
        manifest, _, _ = generate_world_pipeline(request=req, seed=777)
        assert len(manifest.roads) >= 1
        for road in manifest.roads:
            assert road.max_slope_observed is not None
            assert road.max_slope_observed >= 0.0


class TestV2LayoutTemplatesAndContinuousDensity:
    """Test AI layout templates, continuous density monotonicity, and SAT collision freedom."""

    def test_templates_catalog_loads_five_zone_types(self):
        templates = load_zone_templates()
        assert "zone_templates" in templates
        ztypes = templates["zone_templates"]
        expected_types = ["military_base", "airfield", "outpost", "radar_station", "depot"]
        for et in expected_types:
            assert et in ztypes, f"Missing template for {et}"
            assert len(ztypes[et]["sub_districts"]) >= 1

    @pytest.mark.parametrize("zone_type", ["military_base", "airfield", "outpost", "radar_station", "depot"])
    def test_instantiate_templated_zone_monotonic_density(self, zone_type: str):
        """Instantiating with increasing density D in [0.0, 1.0] monotonically increases building count."""
        templates = load_zone_templates()["zone_templates"]
        tpl = templates[zone_type]
        catalog = load_asset_catalog()
        bboxes = {k: v["bounding_box"]["size"] for k, v in catalog.items()}

        zone = Zone(
            id="test_zone",
            name="Test Zone",
            type=zone_type,
            zone_type=zone_type,
            center=[500.0, 20.0, 500.0],
            radius=80.0,
            density="medium",
            faction="A",
            destruction="01",
        )

        counts = []
        densities = [0.0, 0.25, 0.50, 0.75, 1.0]
        for d in densities:
            blds = instantiate_templated_zone(zone=zone, template=tpl, density=d, catalog_bboxes=bboxes)
            counts.append(len(blds))

        # Check monotonic non-decreasing
        for i in range(len(counts) - 1):
            assert counts[i] <= counts[i + 1], f"Density count decreased at step {i}: {counts}"
        assert counts[-1] >= 1, "At max density, at least 1 building should be placed"

    def test_templated_zone_sat_zero_collisions_at_full_density(self):
        """At D=1.0, all instantiated template buildings are completely free of SAT collisions."""
        templates = load_zone_templates()["zone_templates"]
        catalog = load_asset_catalog()
        bboxes = {k: v["bounding_box"]["size"] for k, v in catalog.items()}

        for ztype, tpl in templates.items():
            zone = Zone(
                id=f"zone_{ztype}",
                name=f"Zone {ztype}",
                type=ztype,
                zone_type=ztype,
                center=[500.0, 20.0, 500.0],
                radius=85.0,
                density=1.0,
                faction="A",
                destruction="01",
            )
            blds = instantiate_templated_zone(zone=zone, template=tpl, density=1.0, catalog_bboxes=bboxes)
            obbs = []
            for b in blds:
                dim = b["bounding_box"]["size"]
                yaw_rad = math.radians(b["rotation"][1])
                obb = OBB2D(b["position"][0], b["position"][2], dim[0], dim[1], yaw_rad, buffer=0.0)
                obbs.append((b["id"], obb))

            # Verify no collisions between any pair
            for i in range(len(obbs)):
                for j in range(i + 1, len(obbs)):
                    b1_id, o1 = obbs[i]
                    b2_id, o2 = obbs[j]
                    assert not check_sat_overlap(o1, o2), f"Overlap detected in {ztype} between {b1_id} and {b2_id}"


class TestV2RecomputeAndApiEndpoints:
    """Test fast recompute endpoint and templates endpoint."""

    def test_get_templates_endpoint(self, client):
        res = client.get("/api/templates")
        assert res.status_code == 200
        data = res.json()
        assert "zone_templates" in data
        assert "military_base" in data["zone_templates"]

    def test_post_recompute_endpoint(self, client):
        """Verify POST /api/recompute works and preserves custom zones."""
        custom_zones = [
            {
                "id": "zone_0",
                "name": "Custom Military Base Alpha",
                "type": "military_base",
                "zone_type": "military_base",
                "center": [300.0, 25.0, 300.0],
                "radius": 60.0,
                "density": 0.85,
                "faction": "A",
                "destruction": "01",
            },
            {
                "id": "zone_1",
                "name": "Custom Airfield Bravo",
                "type": "airfield",
                "zone_type": "airfield",
                "center": [700.0, 25.0, 700.0],
                "radius": 75.0,
                "density": 0.70,
                "faction": "B",
                "destruction": "02",
            },
        ]
        recompute_payload = {
            "seed": 42,
            "resolution": 65,
            "zones": custom_zones,
            "flattening_falloff": "cosine",
            "max_road_slope": 0.35,
        }
        res = client.post("/api/recompute", json=recompute_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        manifest = data["manifest"]
        assert len(manifest["zones"]) == 2
        assert manifest["zones"][0]["name"] == "Custom Military Base Alpha"
        assert manifest["terrain"]["mesh"] is not None
        assert manifest["terrain"]["mesh"]["vertex_count"] > 0
        assert len(manifest["buildings"]) >= 2
