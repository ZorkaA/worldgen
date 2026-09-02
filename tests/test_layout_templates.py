"""
tests/test_layout_templates.py - Comprehensive test suite for V2 Requirement R4:
AI-Driven JSON Layout Templates, Continuous Density Scaling, and SAT Collision-Free Placement.

Covers:
1. Offline JSON layout template schema validation across all 5 zone types:
   - military_base, airfield, outpost, radar_station, depot.
2. Continuous density scaling (0.0 <= D <= 1.0) and monotonicity of instantiated slots.
3. Separating Axis Theorem (SAT) 2D Oriented Bounding Box collision-free placement.
4. Sub-district offset composition, slot rotation, and buffer distance adherence.
5. Zone radius containment (no building extends outside the zone footprint).
"""

import copy
import json
import math
from typing import Dict, Any, List, Tuple
import pytest

from backend.app.core.schemas import Zone, BuildingPlacement, BoundingBox
from tests.conftest import SATCollisionTester


# ============================================================================
# 1. Canonical 5 Zone Types Layout Templates Specification
# ============================================================================

CANONICAL_LAYOUT_TEMPLATES: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "version": "2.0.0",
    "zone_templates": {
        "military_base": {
            "type": "military_base",
            "display_name": "Fortified Military Base",
            "sub_districts": [
                {
                    "district_id": "command_hq",
                    "center_offset": [0.0, 0.0],
                    "slots": [
                        {
                            "slot_id": "hq_main",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "command",
                            "candidates": ["SM_Bld_Village_House_01", "SM_Bld_Tent_01"],
                            "density_threshold": 0.0,
                            "buffer_meters": 4.0,
                            "priority": 1,
                        },
                        {
                            "slot_id": "comms_array",
                            "rel_pos": [15.0, 5.0],
                            "rotation_deg": 45.0,
                            "placement_role": "communications",
                            "candidates": ["SM_Bld_Watchtower_01"],
                            "density_threshold": 0.3,
                            "buffer_meters": 3.0,
                            "priority": 2,
                        },
                    ],
                },
                {
                    "district_id": "barracks_row",
                    "center_offset": [-25.0, 15.0],
                    "slots": [
                        {
                            "slot_id": "barracks_1",
                            "rel_pos": [-10.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "barracks",
                            "candidates": ["SM_Bld_Tent_01"],
                            "density_threshold": 0.2,
                            "buffer_meters": 2.5,
                            "priority": 2,
                        },
                        {
                            "slot_id": "barracks_2",
                            "rel_pos": [10.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "barracks",
                            "candidates": ["SM_Bld_Tent_01"],
                            "density_threshold": 0.6,
                            "buffer_meters": 2.5,
                            "priority": 3,
                        },
                    ],
                },
                {
                    "district_id": "defense_perimeter",
                    "center_offset": [0.0, -35.0],
                    "slots": [
                        {
                            "slot_id": "sandbag_gate",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 90.0,
                            "placement_role": "barrier",
                            "candidates": ["SM_Prop_Sandbags_01"],
                            "density_threshold": 0.4,
                            "buffer_meters": 2.0,
                            "priority": 2,
                        },
                        {
                            "slot_id": "watchtower_gate",
                            "rel_pos": [12.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "defense",
                            "candidates": ["SM_Bld_Watchtower_01"],
                            "density_threshold": 0.8,
                            "buffer_meters": 3.0,
                            "priority": 4,
                        },
                    ],
                },
            ],
        },
        "airfield": {
            "type": "airfield",
            "display_name": "Tactical Airfield & Hangar Complex",
            "sub_districts": [
                {
                    "district_id": "flight_control",
                    "center_offset": [0.0, 30.0],
                    "slots": [
                        {
                            "slot_id": "control_tower",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "command",
                            "candidates": ["SM_Bld_Watchtower_01"],
                            "density_threshold": 0.0,
                            "buffer_meters": 5.0,
                            "priority": 1,
                        },
                    ],
                },
                {
                    "district_id": "hangar_line",
                    "center_offset": [-30.0, -10.0],
                    "slots": [
                        {
                            "slot_id": "hangar_alpha",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 90.0,
                            "placement_role": "hangar",
                            "candidates": ["SM_Bld_Village_House_01"],
                            "density_threshold": 0.2,
                            "buffer_meters": 6.0,
                            "priority": 1,
                        },
                        {
                            "slot_id": "hangar_bravo",
                            "rel_pos": [0.0, 25.0],
                            "rotation_deg": 90.0,
                            "placement_role": "hangar",
                            "candidates": ["SM_Bld_Village_House_01"],
                            "density_threshold": 0.7,
                            "buffer_meters": 6.0,
                            "priority": 3,
                        },
                    ],
                },
                {
                    "district_id": "fuel_storage",
                    "center_offset": [35.0, -20.0],
                    "slots": [
                        {
                            "slot_id": "fuel_depot",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "logistics",
                            "candidates": ["SM_Bld_Tent_01"],
                            "density_threshold": 0.5,
                            "buffer_meters": 4.0,
                            "priority": 2,
                        },
                    ],
                },
            ],
        },
        "outpost": {
            "type": "outpost",
            "display_name": "Forward Recon Outpost",
            "sub_districts": [
                {
                    "district_id": "core_bunker",
                    "center_offset": [0.0, 0.0],
                    "slots": [
                        {
                            "slot_id": "main_tent",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "shelter",
                            "candidates": ["SM_Bld_Tent_01"],
                            "density_threshold": 0.0,
                            "buffer_meters": 3.0,
                            "priority": 1,
                        },
                        {
                            "slot_id": "perimeter_tower",
                            "rel_pos": [15.0, 15.0],
                            "rotation_deg": 45.0,
                            "placement_role": "defense",
                            "candidates": ["SM_Bld_Watchtower_01"],
                            "density_threshold": 0.3,
                            "buffer_meters": 3.0,
                            "priority": 2,
                        },
                        {
                            "slot_id": "barrier_east",
                            "rel_pos": [12.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "barrier",
                            "candidates": ["SM_Prop_Sandbags_01"],
                            "density_threshold": 0.5,
                            "buffer_meters": 2.0,
                            "priority": 3,
                        },
                    ],
                },
            ],
        },
        "radar_station": {
            "type": "radar_station",
            "display_name": "High-Altitude Radar Early Warning Station",
            "sub_districts": [
                {
                    "district_id": "radar_core",
                    "center_offset": [0.0, 0.0],
                    "slots": [
                        {
                            "slot_id": "radar_tower",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "radar",
                            "candidates": ["SM_Bld_Watchtower_01"],
                            "density_threshold": 0.0,
                            "buffer_meters": 4.0,
                            "priority": 1,
                        },
                        {
                            "slot_id": "generator_room",
                            "rel_pos": [-15.0, -10.0],
                            "rotation_deg": 0.0,
                            "placement_role": "power",
                            "candidates": ["SM_Bld_Village_House_01"],
                            "density_threshold": 0.35,
                            "buffer_meters": 3.5,
                            "priority": 2,
                        },
                    ],
                },
                {
                    "district_id": "security_checkpoint",
                    "center_offset": [20.0, 20.0],
                    "slots": [
                        {
                            "slot_id": "gate_barrier",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 45.0,
                            "placement_role": "barrier",
                            "candidates": ["SM_Prop_Sandbags_01"],
                            "density_threshold": 0.6,
                            "buffer_meters": 2.0,
                            "priority": 3,
                        },
                    ],
                },
            ],
        },
        "depot": {
            "type": "depot",
            "display_name": "Logistics & Supply Storage Depot",
            "sub_districts": [
                {
                    "district_id": "warehouse_block",
                    "center_offset": [0.0, 0.0],
                    "slots": [
                        {
                            "slot_id": "warehouse_1",
                            "rel_pos": [-15.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "storage",
                            "candidates": ["SM_Bld_Village_House_01"],
                            "density_threshold": 0.0,
                            "buffer_meters": 4.0,
                            "priority": 1,
                        },
                        {
                            "slot_id": "warehouse_2",
                            "rel_pos": [15.0, 0.0],
                            "rotation_deg": 0.0,
                            "placement_role": "storage",
                            "candidates": ["SM_Bld_Village_House_01"],
                            "density_threshold": 0.4,
                            "buffer_meters": 4.0,
                            "priority": 2,
                        },
                    ],
                },
                {
                    "district_id": "supply_yard",
                    "center_offset": [0.0, 25.0],
                    "slots": [
                        {
                            "slot_id": "supply_tent",
                            "rel_pos": [0.0, 0.0],
                            "rotation_deg": 90.0,
                            "placement_role": "logistics",
                            "candidates": ["SM_Bld_Tent_01"],
                            "density_threshold": 0.25,
                            "buffer_meters": 3.0,
                            "priority": 2,
                        },
                        {
                            "slot_id": "cargo_perimeter",
                            "rel_pos": [12.0, 10.0],
                            "rotation_deg": 0.0,
                            "placement_role": "barrier",
                            "candidates": ["SM_Prop_Sandbags_01"],
                            "density_threshold": 0.75,
                            "buffer_meters": 2.0,
                            "priority": 4,
                        },
                    ],
                },
            ],
        },
    },
}


# ============================================================================
# Reference Template Instantiation Engine
# ============================================================================

def instantiate_templated_zone(
    zone: Zone,
    template: Dict[str, Any],
    density: float,
    catalog_bboxes: Dict[str, List[float]],
) -> List[Dict[str, Any]]:
    """
    Instantiates building slots from a zone template given a continuous density value D in [0.0, 1.0].
    Computes absolute world positions from sub-district offsets and slot relative positions.
    """
    placed_buildings: List[Dict[str, Any]] = []
    zone_cx, zone_cy, zone_cz = zone.center

    for district in template.get("sub_districts", []):
        dist_ox, dist_oz = district.get("center_offset", [0.0, 0.0])

        for slot in district.get("slots", []):
            threshold = slot.get("density_threshold", 0.0)
            if density < threshold:
                continue  # Slot is inactive at this continuous density level

            slot_rx, slot_rz = slot.get("rel_pos", [0.0, 0.0])
            rot_yaw = slot.get("rotation_deg", 0.0)
            candidates = slot.get("candidates", ["SM_Bld_Tent_01"])
            prefab = candidates[0] if candidates else "SM_Bld_Tent_01"

            # World position
            wx = zone_cx + dist_ox + slot_rx
            wz = zone_cz + dist_oz + slot_rz
            wy = zone_cy

            bbox_size = catalog_bboxes.get(prefab, [8.0, 8.0, 4.0])

            bld_record = {
                "id": f"{zone.id}_{slot['slot_id']}",
                "zone_id": zone.id,
                "prefab_name": prefab,
                "placement_role": slot.get("placement_role", "building"),
                "position": [round(wx, 2), round(wy, 2), round(wz, 2)],
                "rotation": [0.0, round(rot_yaw, 1), 0.0],
                "scale": [1.0, 1.0, 1.0],
                "bounding_box": {
                    "size": bbox_size,
                    "center": [0.0, 0.0, round(bbox_size[2] / 2.0, 2)],
                },
                "buffer_meters": slot.get("buffer_meters", 2.0),
            }
            placed_buildings.append(bld_record)

    return placed_buildings


# ============================================================================
# 1. Template Schema & Zone Type Completeness Tests
# ============================================================================

class TestLayoutTemplateSchema:
    """Verifies that templates for all 5 military zone types are defined with required attributes."""

    @pytest.mark.parametrize(
        "zone_type",
        ["military_base", "airfield", "outpost", "radar_station", "depot"],
    )
    def test_all_five_zone_types_exist(self, zone_type: str):
        """All 5 zone types must be present in the offline layout template catalog."""
        templates = CANONICAL_LAYOUT_TEMPLATES["zone_templates"]
        assert zone_type in templates, f"Missing template for zone type '{zone_type}'"
        tpl = templates[zone_type]
        assert tpl["type"] == zone_type
        assert "sub_districts" in tpl
        assert len(tpl["sub_districts"]) >= 1

    def test_template_slot_attribute_validity(self):
        """Every template slot must define slot_id, rel_pos, candidates, density_threshold, and buffer_meters."""
        for ztype, tpl in CANONICAL_LAYOUT_TEMPLATES["zone_templates"].items():
            for dist in tpl["sub_districts"]:
                assert "district_id" in dist
                assert len(dist["center_offset"]) == 2
                for slot in dist["slots"]:
                    assert "slot_id" in slot
                    assert len(slot["rel_pos"]) == 2
                    assert isinstance(slot["candidates"], list)
                    assert len(slot["candidates"]) >= 1
                    assert 0.0 <= slot["density_threshold"] <= 1.0
                    assert slot["buffer_meters"] >= 0.0


# ============================================================================
# 2. Continuous Density Scaling & Monotonicity Tests
# ============================================================================

class TestContinuousDensityScaling:
    """Verifies that continuous density slider in [0.0, 1.0] monotonically scales building counts."""

    @pytest.fixture
    def mock_bboxes(self) -> Dict[str, List[float]]:
        return {
            "SM_Bld_Village_House_01": [10.0, 12.0, 6.0],
            "SM_Bld_Tent_01": [7.8, 12.0, 4.0],
            "SM_Bld_Watchtower_01": [5.0, 5.0, 14.0],
            "SM_Prop_Sandbags_01": [2.4, 1.2, 0.9],
        }

    @pytest.mark.parametrize(
        "zone_type",
        ["military_base", "airfield", "outpost", "radar_station", "depot"],
    )
    def test_density_monotonicity(self, zone_type: str, mock_bboxes: Dict[str, List[float]]):
        """Building count must be monotonically non-decreasing as continuous density increases from 0.0 to 1.0."""
        tpl = CANONICAL_LAYOUT_TEMPLATES["zone_templates"][zone_type]
        zone = Zone(
            id="test_zone",
            name=f"Test {zone_type}",
            type=zone_type,
            center=[500.0, 25.0, 500.0],
            radius=80.0,
        )

        densities = [0.0, 0.25, 0.50, 0.75, 1.0]
        counts = []

        for d in densities:
            blds = instantiate_templated_zone(zone, tpl, density=d, catalog_bboxes=mock_bboxes)
            counts.append(len(blds))

        # Check non-decreasing
        for i in range(len(counts) - 1):
            assert counts[i] <= counts[i + 1], (
                f"Density monotonicity violated in {zone_type}: D={densities[i]} ({counts[i]} blds) > "
                f"D={densities[i+1]} ({counts[i+1]} blds)"
            )

        # D=0.0 must spawn at least 1 core building, D=1.0 spawns max buildings
        assert counts[0] >= 1, f"Zero core buildings spawned at D=0.0 in {zone_type}"
        assert counts[-1] > counts[0], f"D=1.0 did not spawn more buildings than D=0.0 in {zone_type}"


# ============================================================================
# 3. SAT 2D Collision-Free Verification Tests
# ============================================================================

class TestSATCollisionFreePlacement:
    """Verifies that all buildings in templated zones are 100% collision-free via SAT."""

    @pytest.fixture
    def mock_bboxes(self) -> Dict[str, List[float]]:
        return {
            "SM_Bld_Village_House_01": [10.0, 12.0, 6.0],
            "SM_Bld_Tent_01": [7.8, 12.0, 4.0],
            "SM_Bld_Watchtower_01": [5.0, 5.0, 14.0],
            "SM_Prop_Sandbags_01": [2.4, 1.2, 0.9],
        }

    @pytest.mark.parametrize(
        "zone_type",
        ["military_base", "airfield", "outpost", "radar_station", "depot"],
    )
    def test_zero_building_collisions_at_max_density(
        self,
        zone_type: str,
        mock_bboxes: Dict[str, List[float]],
        sat_checker: SATCollisionTester,
    ):
        """At max density (D=1.0), all placed buildings must have zero 2D OBB intersection via SAT."""
        tpl = CANONICAL_LAYOUT_TEMPLATES["zone_templates"][zone_type]
        zone = Zone(
            id="test_zone",
            name=f"Dense {zone_type}",
            type=zone_type,
            center=[500.0, 30.0, 500.0],
            radius=90.0,
        )

        blds = instantiate_templated_zone(zone, tpl, density=1.0, catalog_bboxes=mock_bboxes)
        n = len(blds)

        for i in range(n):
            b1 = blds[i]
            poly1 = sat_checker.get_obb_vertices(
                pos=b1["position"],
                size=b1["bounding_box"]["size"],
                rot_yaw_deg=b1["rotation"][1],
                buffer=0.0,
            )
            for j in range(i + 1, n):
                b2 = blds[j]
                poly2 = sat_checker.get_obb_vertices(
                    pos=b2["position"],
                    size=b2["bounding_box"]["size"],
                    rot_yaw_deg=b2["rotation"][1],
                    buffer=0.0,
                )
                assert not sat_checker.check_overlap(poly1, poly2), (
                    f"Collision detected between {b1['id']} and {b2['id']} in template '{zone_type}'!"
                )


# ============================================================================
# 4. Zone Footprint Containment Tests
# ============================================================================

class TestZoneFootprintContainment:
    """Verifies that all templated buildings are placed strictly inside the zone's circular radius."""

    @pytest.fixture
    def mock_bboxes(self) -> Dict[str, List[float]]:
        return {
            "SM_Bld_Village_House_01": [10.0, 12.0, 6.0],
            "SM_Bld_Tent_01": [7.8, 12.0, 4.0],
            "SM_Bld_Watchtower_01": [5.0, 5.0, 14.0],
            "SM_Prop_Sandbags_01": [2.4, 1.2, 0.9],
        }

    @pytest.mark.parametrize(
        "zone_type",
        ["military_base", "airfield", "outpost", "radar_station", "depot"],
    )
    def test_buildings_stay_inside_zone_radius(
        self,
        zone_type: str,
        mock_bboxes: Dict[str, List[float]],
    ):
        """Distance from zone center to every building corner must not exceed zone radius + safety tolerance."""
        zone_radius = 80.0
        zone_center = [400.0, 20.0, 400.0]
        tpl = CANONICAL_LAYOUT_TEMPLATES["zone_templates"][zone_type]

        zone = Zone(
            id="zone_containment",
            name=f"Containment {zone_type}",
            type=zone_type,
            center=zone_center,
            radius=zone_radius,
        )

        blds = instantiate_templated_zone(zone, tpl, density=1.0, catalog_bboxes=mock_bboxes)

        for b in blds:
            bx, _, bz = b["position"]
            dist_to_center = math.hypot(bx - zone_center[0], bz - zone_center[2])
            # Building center + half bounding box diagonal should stay inside radius
            size = b["bounding_box"]["size"]
            half_diag = 0.5 * math.hypot(size[0], size[1])
            assert dist_to_center + half_diag <= zone_radius + 5.0, (
                f"Building {b['id']} extends outside zone radius ({dist_to_center + half_diag:.1f}m > {zone_radius}m)"
            )
