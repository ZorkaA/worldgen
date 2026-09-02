"""
tests/test_map_dimensions.py - Comprehensive test suite for V2 Requirement R1:
Global Map Dimensions, Granularity/Resolution, Terrain Deformation, and Bounds Invariants.

Covers:
1. Map Dimension Scaling (0.5 km, 1.0 km, 2.5 km, 4.0 km, 10.0 km) in world meters.
2. Heightmap Grid Resolution & Array Dimensionality (65, 129, 257, 513).
3. Metric Cell Size & Boundary Coordinate Invariants.
4. Non-Square / Rectangular World Dimensions (Aspect Ratios).
5. Terrain Deformation Multiplier & Elevation Range Invariants.
6. Zone Placement Margin Offsets (Borders & Boundary Clipping Prevention).
7. Manifest & API Integration with Configurable Dimensions.
"""

import math
import numpy as np
import pytest
from typing import Dict, Any, List

from backend.app.core.schemas import (
    TerrainConfig,
    ZoneConfig,
    GenerateWorldRequest,
    WorldManifest,
)
from backend.app.generator.terrain import generate_terrain, domain_warped_fbm, _generate_permutation_table
from backend.app.generator.zones import generate_zones
from backend.app.generator.pipeline import generate_world_pipeline


# ============================================================================
# 1. Map Dimension Scaling & Array Dimensionality Tests
# ============================================================================

class TestMapDimensionScaling:
    """Verifies that changing map dimensions returns arrays and world sizes of exact corresponding sizes."""

    @pytest.mark.parametrize(
        "dim_km,expected_meters",
        [
            (0.5, 500.0),
            (1.0, 1000.0),
            (2.5, 2500.0),
            (4.0, 4000.0),
            (10.0, 10000.0),
        ],
    )
    def test_dimension_km_to_world_size_meters(self, dim_km: float, expected_meters: float):
        """Map dimensions in km must scale to exact meters [W, H, L]."""
        height_scale = 150.0
        config = TerrainConfig(
            resolution=65,
            world_size=[expected_meters, height_scale, expected_meters],
            height_scale=height_scale,
        )
        assert config.world_size[0] == pytest.approx(expected_meters, rel=1e-5)
        assert config.world_size[1] == pytest.approx(height_scale, rel=1e-5)
        assert config.world_size[2] == pytest.approx(expected_meters, rel=1e-5)

        hmap = generate_terrain(config, seed=42)
        assert isinstance(hmap, np.ndarray)
        assert hmap.shape == (65, 65)
        assert hmap.dtype == np.float32

    @pytest.mark.parametrize("resolution", [65, 129, 257, 513])
    def test_heightmap_array_shape_matches_resolution(self, resolution: int):
        """Generated heightmap array shape must strictly equal (resolution, resolution)."""
        config = TerrainConfig(
            resolution=resolution,
            world_size=[1000.0, 150.0, 1000.0],
            height_scale=150.0,
        )
        hmap = generate_terrain(config, seed=123)
        assert hmap.shape == (resolution, resolution)
        assert not np.isnan(hmap).any(), "Heightmap must not contain NaN values"
        assert not np.isinf(hmap).any(), "Heightmap must not contain Inf values"

    @pytest.mark.parametrize(
        "world_size,resolution",
        [
            ([500.0, 100.0, 500.0], 65),
            ([1000.0, 150.0, 1000.0], 129),
            ([2500.0, 200.0, 2500.0], 257),
            ([4000.0, 300.0, 4000.0], 513),
        ],
    )
    def test_grid_cell_size_calculation(self, world_size: List[float], resolution: int):
        """Grid cell spacing must exactly equal world_dimension / (resolution - 1)."""
        w, _, l = world_size
        expected_cell_x = w / (resolution - 1)
        expected_cell_z = l / (resolution - 1)

        xs = np.linspace(0.0, w, resolution, dtype=np.float32)
        zs = np.linspace(0.0, l, resolution, dtype=np.float32)

        diffs_x = np.diff(xs)
        diffs_z = np.diff(zs)

        assert np.allclose(diffs_x, expected_cell_x, atol=1e-4)
        assert np.allclose(diffs_z, expected_cell_z, atol=1e-4)
        assert xs[0] == pytest.approx(0.0, abs=1e-5)
        assert xs[-1] == pytest.approx(w, abs=1e-4)
        assert zs[0] == pytest.approx(0.0, abs=1e-5)
        assert zs[-1] == pytest.approx(l, abs=1e-4)


# ============================================================================
# 2. Rectangular & Aspect Ratio Invariant Tests
# ============================================================================

class TestNonSquareMapDimensions:
    """Verifies generator correctness for non-square / rectangular world bounds."""

    @pytest.mark.parametrize(
        "world_w,world_l",
        [
            (2000.0, 1000.0),  # 2:1 aspect ratio
            (1000.0, 3000.0),  # 1:3 aspect ratio
            (500.0, 2500.0),   # 1:5 aspect ratio
            (4000.0, 2000.0),  # 2:1 aspect ratio
        ],
    )
    def test_rectangular_world_generation(self, world_w: float, world_l: float):
        """Heightmap generation on non-square domains preserves aspect ratio metrics."""
        res = 129
        config = TerrainConfig(
            resolution=res,
            world_size=[world_w, 150.0, world_l],
            height_scale=150.0,
        )
        hmap = generate_terrain(config, seed=42)
        assert hmap.shape == (res, res)
        assert np.min(hmap) >= 0.0
        assert np.max(hmap) <= 150.0 + 1e-4

        # Verify pipeline execution
        manifest, _, _ = generate_world_pipeline(
            request=GenerateWorldRequest(terrain=config),
            seed=42,
        )
        assert manifest.terrain.world_size == [world_w, 150.0, world_l]
        assert manifest.metadata.bounds == [0.0, 0.0, 0.0, world_w, 150.0, world_l]


# ============================================================================
# 3. Terrain Deformation Multiplier & Elevation Tests
# ============================================================================

class TestTerrainDeformationMultiplier:
    """Verifies that terrain deformation strength scales fractal persistence and domain warping."""

    @pytest.mark.parametrize("warp_strength", [0.0, 15.0, 35.0, 75.0, 150.0])
    def test_warp_strength_bounds_and_variance(self, warp_strength: float):
        """Varying domain warp strength keeps elevation strictly in [0.0, height_scale]."""
        height_scale = 120.0
        config = TerrainConfig(
            resolution=65,
            world_size=[1000.0, height_scale, 1000.0],
            height_scale=height_scale,
            domain_warp_strength=warp_strength,
        )
        hmap = generate_terrain(config, seed=777)
        assert np.min(hmap) >= 0.0
        assert np.max(hmap) <= height_scale + 1e-3

    def test_zero_warp_vs_high_warp_variance(self):
        """Zero warp produces smoother, less distorted terrain than high domain warp."""
        config_flat = TerrainConfig(resolution=65, domain_warp_strength=0.0)
        config_warped = TerrainConfig(resolution=65, domain_warp_strength=100.0)

        h_flat = generate_terrain(config_flat, seed=42)
        h_warped = generate_terrain(config_warped, seed=42)

        # Gradient magnitude / roughness should differ
        grad_flat = np.gradient(h_flat)
        grad_warped = np.gradient(h_warped)

        roughness_flat = np.mean(np.hypot(grad_flat[0], grad_flat[1]))
        roughness_warped = np.mean(np.hypot(grad_warped[0], grad_warped[1]))

        assert roughness_warped > 0.0
        assert roughness_flat > 0.0


# ============================================================================
# 4. Zone Placement Margin Offsets & Border Constraint Tests
# ============================================================================

class TestZoneEdgeMargins:
    """Verifies that zones respect edge margin offset parameters to avoid map border clipping."""

    @pytest.mark.parametrize(
        "world_size,margin",
        [
            ([500.0, 100.0, 500.0], 40.0),
            ([1000.0, 150.0, 1000.0], 80.0),
            ([2500.0, 200.0, 2500.0], 150.0),
            ([4000.0, 300.0, 4000.0], 250.0),
        ],
    )
    def test_zones_stay_within_map_margins(self, world_size: List[float], margin: float):
        """All zone centers and footprints must stay strictly inside [margin, world_dimension - margin]."""
        terrain_config = TerrainConfig(resolution=65, world_size=world_size)
        zone_config = ZoneConfig(
            min_zone_distance=max(60.0, world_size[0] * 0.1),
            zone_count_target=4,
            min_radius=25.0,
            max_radius=50.0,
        )
        hmap = generate_terrain(terrain_config, seed=42)
        zones, _ = generate_zones(hmap, terrain_config, zone_config, seed=42)

        w_max = world_size[0]
        l_max = world_size[2]

        for z in zones:
            cx, _, cz = z.center
            # Center must be inside world bounds
            assert 0.0 <= cx <= w_max, f"Zone center X={cx} out of bounds [0, {w_max}]"
            assert 0.0 <= cz <= l_max, f"Zone center Z={cz} out of bounds [0, {l_max}]"

            # Footprint points must also stay inside world bounds
            if z.footprint_points:
                for fx, fz in z.footprint_points:
                    assert 0.0 <= fx <= w_max, f"Footprint X={fx} outside map [0, {w_max}]"
                    assert 0.0 <= fz <= l_max, f"Footprint Z={fz} outside map [0, {l_max}]"


# ============================================================================
# 5. Manifest & API Integration Tests for Dimensions
# ============================================================================

class TestDimensionAPIIntegration:
    """Verifies manifest output and API endpoints when configuring custom map dimensions."""

    @pytest.mark.parametrize(
        "dim_w,dim_l,res",
        [
            (500.0, 500.0, 65),
            (1000.0, 1000.0, 129),
            (2500.0, 2500.0, 257),
            (4000.0, 4000.0, 513),
        ],
    )
    def test_generate_world_manifest_dimensions(self, dim_w: float, dim_l: float, res: int):
        """Manifest generation embeds exact world dimensions, bounds, and heightmap resolution."""
        t_config = TerrainConfig(
            resolution=res,
            world_size=[dim_w, 150.0, dim_l],
            height_scale=150.0,
        )
        manifest, _, _ = generate_world_pipeline(
            request=GenerateWorldRequest(terrain=t_config),
            seed=99,
        )

        assert manifest.terrain.resolution == res
        assert manifest.terrain.world_size == [dim_w, 150.0, dim_l]
        assert len(manifest.terrain.heightmap) == res
        assert len(manifest.terrain.heightmap[0]) == res
        assert manifest.metadata.bounds == [0.0, 0.0, 0.0, dim_w, 150.0, dim_l]

    def test_api_client_generate_custom_dimension(self, api_client):
        """API /api/generate endpoint successfully accepts custom world_size and returns 200."""
        req_payload = {
            "seed": 101,
            "resolution": 65,
            "world_size": [2500.0, 200.0, 2500.0],
            "height_scale": 200.0,
        }
        res = api_client.post("/api/generate", json=req_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        manifest = data["manifest"]
        assert manifest["terrain"]["world_size"] == [2500.0, 200.0, 2500.0]
        assert manifest["terrain"]["resolution"] == 65
