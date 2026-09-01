"""
tests/test_catalog_builder_unit.py - Unit tests for backend.app.catalog package.
"""

import os
import json
import pytest
from typing import Dict, Any

from backend.app.catalog.vlm_enrich import (
    clean_vlm_json_string,
    parse_vlm_response,
    heuristic_enrich_asset,
    enrich_asset_vlm
)
from backend.app.catalog.builder import (
    compute_file_hash,
    validate_catalog_data,
    load_cached_catalog,
    get_catalog
)


class TestVLMEnrichModule:
    """Unit tests for VLM enrichment parsing and heuristics."""

    def test_clean_vlm_json_string_markdown_blocks(self):
        raw = "```json\n{\"category\": \"structures\", \"tags\": [\"tent\"]}\n```"
        cleaned = clean_vlm_json_string(raw)
        assert cleaned == "{\"category\": \"structures\", \"tags\": [\"tent\"]}"
        parsed = json.loads(cleaned)
        assert parsed["category"] == "structures"

    def test_clean_vlm_json_string_with_reasoning_preamble(self):
        raw = "Here is my analysis of the 3D model:\n```json\n{\"category\": \"vehicles\", \"placement_role\": \"vehicle\"}\n```\nHope this helps!"
        cleaned = clean_vlm_json_string(raw)
        parsed = json.loads(cleaned)
        assert parsed["category"] == "vehicles"
        assert parsed["placement_role"] == "vehicle"

    def test_parse_vlm_response_from_message_content(self):
        resp = {
            "message": {
                "role": "assistant",
                "content": "```json\n{\"category\": \"structures\", \"placement_role\": \"barracks\", \"tags\": [\"tent\", \"military\"]}\n```"
            }
        }
        parsed = parse_vlm_response(resp)
        assert parsed is not None
        assert parsed["category"] == "structures"
        assert parsed["placement_role"] == "barracks"
        assert "tent" in parsed["tags"]

    def test_parse_vlm_response_from_thinking_field(self):
        resp = {
            "thinking": "Reasoning trace...\n```json\n{\"category\": \"defenses\", \"placement_role\": \"fence\", \"tags\": [\"barrier\", \"wire\"]}\n```",
            "response": ""
        }
        parsed = parse_vlm_response(resp)
        assert parsed is not None
        assert parsed["category"] == "defenses"
        assert parsed["placement_role"] == "fence"

    def test_heuristic_enrichment_tent(self):
        data = heuristic_enrich_asset("SM_Bld_Tent_01", [7.8, 12.0, 4.1])
        assert data["category"] == "structures"
        assert data["placement_role"] == "building"
        assert "tent" in data["tags"]
        assert "military" in data["tags"]
        assert "military_base" in data["affinities"]
        assert data["footprint_type"] == "rectangular"
        assert data["max_destruction_level"] == 3

    def test_heuristic_enrichment_destroyed_tent(self):
        data = heuristic_enrich_asset("SM_Bld_Tent_Destroyed_01", [7.8, 12.0, 4.1])
        assert "destroyed" in data["tags"]
        assert "ruins" in data["tags"]
        assert data["max_destruction_level"] == 4

    def test_heuristic_enrichment_tower(self):
        data = heuristic_enrich_asset("SM_Bld_ControlTower_01", [8.0, 8.0, 25.0])
        assert data["category"] == "structures"
        assert data["placement_role"] == "defensive_structure"
        assert "tower" in data["tags"]
        assert data["footprint_type"] == "circular"

    def test_heuristic_enrichment_vehicle_tank(self):
        data = heuristic_enrich_asset("SM_Veh_Tank_01", [4.0, 8.0, 3.2])
        assert data["category"] == "vehicles"
        assert data["placement_role"] == "vehicle"
        assert "tank" in data["tags"]
        assert "armor" in data["tags"]

    def test_heuristic_enrichment_vehicle_heli(self):
        data = heuristic_enrich_asset("SM_Veh_Heli_01", [14.0, 18.0, 5.0])
        assert data["category"] == "vehicles"
        assert data["placement_role"] == "vehicle"
        assert "helicopter" in data["tags"]
        assert "airfield" in data["affinities"]

    def test_heuristic_enrichment_prop_sandbags(self):
        data = heuristic_enrich_asset("SM_Prop_Sandbags_01", [2.0, 1.0, 1.2])
        assert data["category"] == "defenses"
        assert data["placement_role"] == "defensive_structure"
        assert "sandbag" in data["tags"]
        assert "defense" in data["tags"]


class TestCatalogBuilderValidation:
    """Unit tests for catalog validation logic."""

    def test_validate_catalog_data_valid(self):
        valid_catalog = {
            "version": "1.0.0",
            "assets": {
                "SM_Bld_Tent_01": {
                    "name": "SM_Bld_Tent_01",
                    "category": "structures",
                    "placement_role": "building",
                    "tags": ["tent", "military"],
                    "description": "Tent description",
                    "bounding_box": {
                        "min": [-3.899, -6.015, 0.0],
                        "max": [3.899, 6.015, 4.072],
                        "size": [7.799, 12.030, 4.072],
                        "dimensions": [7.799, 12.030, 4.072],
                        "center": [0.0, 0.0, 2.036]
                    },
                    "affinities": ["military_base"],
                    "suggested_density": "medium"
                }
            }
        }
        is_valid, errors = validate_catalog_data(valid_catalog)
        assert is_valid
        assert len(errors) == 0

    def test_validate_catalog_data_missing_tags(self):
        bad_catalog = {
            "version": "1.0.0",
            "assets": {
                "SM_Bld_Tent_01": {
                    "name": "SM_Bld_Tent_01",
                    "category": "structures",
                    "placement_role": "building",
                    "tags": [],
                    "bounding_box": {
                        "min": [0.0, 0.0, 0.0],
                        "max": [1.0, 1.0, 1.0],
                        "size": [1.0, 1.0, 1.0],
                        "center": [0.5, 0.5, 0.5]
                    }
                }
            }
        }
        is_valid, errors = validate_catalog_data(bad_catalog)
        assert not is_valid
        assert any("tags" in e for e in errors)

    def test_validate_catalog_data_invalid_bbox_dimension(self):
        bad_catalog = {
            "version": "1.0.0",
            "assets": {
                "SM_Bld_Tent_01": {
                    "name": "SM_Bld_Tent_01",
                    "category": "structures",
                    "placement_role": "building",
                    "tags": ["tent"],
                    "bounding_box": {
                        "min": [0.0, 0.0, 0.0],
                        "max": [1.0, 1.0, 1.0],
                        "size": [1.0, -1.0, 1.0],  # Negative dimension
                        "center": [0.5, 0.5, 0.5]
                    }
                }
            }
        }
        is_valid, errors = validate_catalog_data(bad_catalog)
        assert not is_valid
        assert any("dimensions" in e or "size" in e for e in errors)
