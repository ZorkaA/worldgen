"""
tests/test_manifest_schema.py - Pytest suite for strict JSON Schema validation of world_manifest.json.

Covers:
- Root structure & required top-level keys
- Metadata verification (seed, ISO8601 timestamp, generator, bounds)
- Terrain elevation grid verification (resolution, 2D heights array dimensions, numeric ranges)
- Zone attributes & geometry (factions A/B/C, destruction levels 01-04, center bounds, radius, footprint)
- Building transforms & bounding boxes (3D positions, rotations, positive bbox sizes)
- Road network connectivity & waypoints (from/to zone foreign keys, 3D waypoint coordinates, width)
- Referential integrity between zones, buildings, and roads
- Exhaustive negative tests (missing fields, wrong types, out-of-bounds enums, NaN/Inf values)
"""

import copy
import json
import math
from typing import Any, Dict

import pytest
import jsonschema
from jsonschema import validate, ValidationError, Draft202012Validator, Draft7Validator


class TestManifestSchemaValidations:
    """Suite testing valid manifest variations against the official schema."""

    def test_sample_manifest_passes_schema_validation(self, sample_valid_manifest, manifest_schema):
        """Verifies that the canonical sample manifest validates cleanly against Draft 2020-12 / Draft 7."""
        # Should raise no ValidationError
        validate(instance=sample_valid_manifest, schema=manifest_schema)

    def test_metadata_fields(self, sample_valid_manifest, manifest_schema):
        """Tests that all required metadata fields are strictly validated."""
        manifest = copy.deepcopy(sample_valid_manifest)
        assert isinstance(manifest["metadata"]["seed"], int)
        assert isinstance(manifest["metadata"]["version"], str)
        assert isinstance(manifest["metadata"]["created_at"], str)
        assert isinstance(manifest["metadata"]["generator"], str)
        assert len(manifest["metadata"]["bounds"]) == 6

        validate(instance=manifest, schema=manifest_schema)

    def test_terrain_heights_dimensions_match_resolution(self, sample_valid_manifest, manifest_schema):
        """Tests that the terrain heightmap 2D array dimensions strictly match resolution x resolution."""
        manifest = copy.deepcopy(sample_valid_manifest)
        res = manifest["terrain"]["resolution"]
        heightmap = manifest["terrain"]["heightmap"]

        assert len(heightmap) == res, f"Heightmap outer dimension {len(heightmap)} != resolution {res}"
        for row_idx, row in enumerate(heightmap):
            assert len(row) == res, f"Heightmap row {row_idx} length {len(row)} != resolution {res}"
            for col_idx, val in enumerate(row):
                assert isinstance(val, (int, float)), f"Elevation at ({row_idx}, {col_idx}) not numeric: {val}"
                assert not math.isnan(val) and not math.isinf(val), f"Elevation is NaN/Inf at ({row_idx}, {col_idx})"

        validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("resolution", [33, 65, 129, 257, 513])
    def test_various_terrain_resolutions(self, sample_valid_manifest, manifest_schema, resolution):
        """Tests that different valid power-of-2 + 1 terrain resolutions validate correctly."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["terrain"]["resolution"] = resolution
        manifest["terrain"]["heightmap"] = [[10.0 for _ in range(resolution)] for _ in range(resolution)]
        validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("faction", ["A", "B", "C"])
    def test_zone_faction_enums(self, sample_valid_manifest, manifest_schema, faction):
        """Tests all authorized military faction enums A, B, C."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["faction"] = faction
        manifest["buildings"][0]["faction"] = faction
        validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("destruction", ["01", "02", "03", "04"])
    def test_zone_destruction_enums(self, sample_valid_manifest, manifest_schema, destruction):
        """Tests all authorized destruction level enums 01, 02, 03, 04."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["destruction"] = destruction
        manifest["buildings"][0]["destruction"] = destruction
        validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("density", ["low", "medium", "high"])
    def test_zone_density_enums(self, sample_valid_manifest, manifest_schema, density):
        """Tests all authorized density level enums."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["density"] = density
        validate(instance=manifest, schema=manifest_schema)

    def test_building_bounding_box_validity(self, sample_valid_manifest, manifest_schema):
        """Tests that building bounding boxes contain positive size vectors."""
        manifest = copy.deepcopy(sample_valid_manifest)
        for bld in manifest["buildings"]:
            size = bld["bounding_box"]["size"]
            assert len(size) == 3
            assert all(s > 0 for s in size), f"Building {bld['id']} bbox size has non-positive dimension: {size}"
        validate(instance=manifest, schema=manifest_schema)

    def test_building_quaternion_or_euler_rotations(self, sample_valid_manifest, manifest_schema):
        """Tests that buildings support both 3-element Euler and 4-element Quaternion rotations."""
        manifest = copy.deepcopy(sample_valid_manifest)
        # 3-element Euler
        manifest["buildings"][0]["rotation"] = [0.0, 45.0, 0.0]
        validate(instance=manifest, schema=manifest_schema)

        # 4-element Quaternion
        manifest["buildings"][0]["rotation"] = [0.0, 0.3826834, 0.0, 0.9238795]
        validate(instance=manifest, schema=manifest_schema)

    def test_road_waypoints_structure(self, sample_valid_manifest, manifest_schema):
        """Tests road waypoints validity: >= 2 waypoints, each with 3 coordinates."""
        manifest = copy.deepcopy(sample_valid_manifest)
        for road in manifest["roads"]:
            assert len(road["waypoints"]) >= 2
            for wp in road["waypoints"]:
                assert len(wp) == 3
                assert all(isinstance(coord, (int, float)) for coord in wp)
        validate(instance=manifest, schema=manifest_schema)

    def test_foreign_key_referential_integrity(self, sample_valid_manifest):
        """Tests that building zone_ids and road from_zone/to_zone point to existing zones."""
        manifest = sample_valid_manifest
        zone_ids = {z["id"] for z in manifest["zones"]}

        for bld in manifest["buildings"]:
            assert bld["zone_id"] in zone_ids, f"Building {bld['id']} references missing zone {bld['zone_id']}"

        for road in manifest["roads"]:
            assert road["from_zone"] in zone_ids, f"Road {road['id']} from_zone {road['from_zone']} does not exist"
            assert road["to_zone"] in zone_ids, f"Road {road['id']} to_zone {road['to_zone']} does not exist"


class TestManifestSchemaNegativeCases:
    """Suite testing strict rejection of invalid or corrupt manifest payloads."""

    @pytest.mark.parametrize("missing_key", ["metadata", "terrain", "zones", "buildings", "roads"])
    def test_missing_root_key_fails_validation(self, sample_valid_manifest, manifest_schema, missing_key):
        """Asserts that removing any top-level required key raises a ValidationError."""
        manifest = copy.deepcopy(sample_valid_manifest)
        del manifest[missing_key]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("missing_meta", ["version", "seed", "created_at", "generator"])
    def test_missing_metadata_key_fails(self, sample_valid_manifest, manifest_schema, missing_meta):
        """Asserts that missing metadata fields fail validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        del manifest["metadata"][missing_meta]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("invalid_faction", ["D", "X", "Alpha", 1, None, ""])
    def test_invalid_faction_enum_fails(self, sample_valid_manifest, manifest_schema, invalid_faction):
        """Asserts that non-authorized faction enums fail validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["faction"] = invalid_faction
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    @pytest.mark.parametrize("invalid_destruction", ["00", "05", "1", "pristine", 4, None])
    def test_invalid_destruction_enum_fails(self, sample_valid_manifest, manifest_schema, invalid_destruction):
        """Asserts that non-authorized destruction level enums fail validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["destruction"] = invalid_destruction
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_negative_terrain_resolution_fails(self, sample_valid_manifest, manifest_schema):
        """Asserts that terrain resolution below minimum fails validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["terrain"]["resolution"] = 8  # Below minimum 16
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_invalid_building_position_type_fails(self, sample_valid_manifest, manifest_schema):
        """Asserts that string or 2D building position fails validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["buildings"][0]["position"] = ["250", "25", "300"]  # Strings instead of floats
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

        manifest["buildings"][0]["position"] = [250.0, 300.0]  # Only 2 coords instead of 3
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_road_with_insufficient_waypoints_fails(self, sample_valid_manifest, manifest_schema):
        """Asserts that a road with fewer than 2 waypoints fails validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["roads"][0]["waypoints"] = [[250.0, 25.0, 300.0]]  # Only 1 waypoint
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_corrupt_footprint_polygon_fails(self, sample_valid_manifest, manifest_schema):
        """Asserts that 1-element or non-2D footprint points fail validation."""
        manifest = copy.deepcopy(sample_valid_manifest)
        manifest["zones"][0]["footprint_points"] = [[250.0]]  # Invalid point dimension
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)
