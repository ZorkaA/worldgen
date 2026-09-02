"""Bounding-Box-Aware Building Placement using Separating Axis Theorem (SAT)."""

import json
import math
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from ..core.config import CATALOG_FILE, TEMPLATES_FILE
from ..core.schemas import BuildingPlacement, BoundingBox, Zone, TerrainConfig
from ..catalog.generate_templates import TEMPLATES_DATA


# Default fallback asset dictionary with real PolygonMilitary bounding boxes & render paths
DEFAULT_SYNTHETIC_CATALOG: Dict[str, Dict[str, Any]] = {
    "SM_Bld_Tent_01": {
        "name": "SM_Bld_Tent_01",
        "category": "building",
        "placement_role": "barracks",
        "tags": ["tent", "military", "shelter", "barracks"],
        "description": "Standard military barracks canvas tent.",
        "bounding_box": {
            "min": [-3.899, -6.015, 0.0],
            "max": [3.899, 6.015, 4.072],
            "size": [7.799, 12.030, 4.072],
            "dimensions": [7.799, 12.030, 4.072],
            "center": [0.0, 0.0, 2.036],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Bld_Tent_01_front.png",
            "side": "renders/SM_Bld_Tent_01_side.png",
            "top": "renders/SM_Bld_Tent_01_top.png",
        },
        "suggested_density": "medium",
        "affinities": ["military_base", "outpost"],
    },
    "SM_Bld_Watchtower_01": {
        "name": "SM_Bld_Watchtower_01",
        "category": "structures",
        "placement_role": "watchtower",
        "tags": ["tower", "defense", "watchtower", "guard"],
        "description": "Elevated perimeter watchtower structure.",
        "bounding_box": {
            "min": [-2.5, -2.5, 0.0],
            "max": [2.5, 2.5, 11.5],
            "size": [5.0, 5.0, 11.5],
            "dimensions": [5.0, 5.0, 11.5],
            "center": [0.0, 0.0, 5.75],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Bld_Watchtower_01_front.png",
            "side": "renders/SM_Bld_Watchtower_01_side.png",
            "top": "renders/SM_Bld_Watchtower_01_top.png",
        },
        "suggested_density": "high",
        "affinities": ["military_base", "outpost", "radar_station"],
    },
    "SM_Prop_Sandbags_01": {
        "name": "SM_Prop_Sandbags_01",
        "category": "defenses",
        "placement_role": "defensive_structure",
        "tags": ["sandbags", "cover", "defense", "bunker"],
        "description": "Curved sandbag defensive wall fortification.",
        "bounding_box": {
            "min": [-1.2, -0.6, 0.0],
            "max": [1.2, 0.6, 1.1],
            "size": [2.4, 1.2, 1.1],
            "dimensions": [2.4, 1.2, 1.1],
            "center": [0.0, 0.0, 0.55],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Prop_Sandbags_01_front.png",
            "side": "renders/SM_Prop_Sandbags_01_side.png",
            "top": "renders/SM_Prop_Sandbags_01_top.png",
        },
        "suggested_density": "high",
        "affinities": ["military_base", "outpost", "radar_station"],
    },
    "SM_Bld_Tent_Desert_01": {
        "name": "SM_Bld_Tent_Desert_01",
        "category": "building",
        "placement_role": "barracks",
        "tags": ["tent", "desert", "military", "shelter"],
        "description": "Desert camouflage barracks tent.",
        "bounding_box": {
            "min": [-3.899, -6.015, 0.0],
            "max": [3.899, 6.015, 4.072],
            "size": [7.799, 12.030, 4.072],
            "dimensions": [7.799, 12.030, 4.072],
            "center": [0.0, 0.0, 2.036],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Bld_Tent_Desert_01_front.png",
            "side": "renders/SM_Bld_Tent_Desert_01_side.png",
            "top": "renders/SM_Bld_Tent_Desert_01_top.png",
        },
        "suggested_density": "medium",
        "affinities": ["military_base", "outpost"],
    },
    "SM_Bld_Village_House_01": {
        "name": "SM_Bld_Village_House_01",
        "category": "building",
        "placement_role": "command",
        "tags": ["house", "command_post", "structure", "headquarters"],
        "description": "Reinforced command headquarters structure.",
        "bounding_box": {
            "min": [-4.5, -5.5, 0.0],
            "max": [4.5, 5.5, 6.2],
            "size": [9.0, 11.0, 6.2],
            "dimensions": [9.0, 11.0, 6.2],
            "center": [0.0, 0.0, 3.1],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Bld_Village_House_01_front.png",
            "side": "renders/SM_Bld_Village_House_01_side.png",
            "top": "renders/SM_Bld_Village_House_01_top.png",
        },
        "suggested_density": "low",
        "affinities": ["military_base", "radar_station"],
    },
    "SM_Bld_Village_House_Tower_01": {
        "name": "SM_Bld_Village_House_Tower_01",
        "category": "structures",
        "placement_role": "watchtower",
        "tags": ["tower", "defense", "watchtower", "sniper"],
        "description": "Elevated perimeter watchtower.",
        "bounding_box": {
            "min": [-2.5, -2.5, 0.0],
            "max": [2.5, 2.5, 11.5],
            "size": [5.0, 5.0, 11.5],
            "dimensions": [5.0, 5.0, 11.5],
            "center": [0.0, 0.0, 5.75],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Bld_Village_House_Tower_01_front.png",
            "side": "renders/SM_Bld_Village_House_Tower_01_side.png",
            "top": "renders/SM_Bld_Village_House_Tower_01_top.png",
        },
        "suggested_density": "high",
        "affinities": ["military_base", "outpost", "radar_station"],
    },
    "SM_Bld_WaterTank_01": {
        "name": "SM_Bld_WaterTank_01",
        "category": "structures",
        "placement_role": "infrastructure",
        "tags": ["watertank", "utility", "depot", "industrial"],
        "description": "Industrial water supply tower.",
        "bounding_box": {
            "min": [-3.0, -3.0, 0.0],
            "max": [3.0, 3.0, 8.5],
            "size": [6.0, 6.0, 8.5],
            "dimensions": [6.0, 6.0, 8.5],
            "center": [0.0, 0.0, 4.25],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Bld_WaterTank_01_front.png",
            "side": "renders/SM_Bld_WaterTank_01_side.png",
            "top": "renders/SM_Bld_WaterTank_01_top.png",
        },
        "suggested_density": "medium",
        "affinities": ["depot", "airfield"],
    },
    "SM_Prop_Sandbag_01": {
        "name": "SM_Prop_Sandbag_01",
        "category": "defenses",
        "placement_role": "defensive_structure",
        "tags": ["sandbags", "cover", "defense"],
        "description": "Curved sandbag defensive wall.",
        "bounding_box": {
            "min": [-1.2, -0.6, 0.0],
            "max": [1.2, 0.6, 1.1],
            "size": [2.4, 1.2, 1.1],
            "dimensions": [2.4, 1.2, 1.1],
            "center": [0.0, 0.0, 0.55],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Prop_Sandbag_01_front.png",
            "side": "renders/SM_Prop_Sandbag_01_side.png",
            "top": "renders/SM_Prop_Sandbag_01_top.png",
        },
        "suggested_density": "high",
        "affinities": ["military_base", "outpost", "radar_station"],
    },
    "SM_Prop_Crate_Military_01": {
        "name": "SM_Prop_Crate_Military_01",
        "category": "decorations",
        "placement_role": "prop",
        "tags": ["crate", "supplies", "ammunition", "storage"],
        "description": "Wooden military ammunition crate.",
        "bounding_box": {
            "min": [-0.8, -0.8, 0.0],
            "max": [0.8, 0.8, 1.2],
            "size": [1.6, 1.6, 1.2],
            "dimensions": [1.6, 1.6, 1.2],
            "center": [0.0, 0.0, 0.6],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Prop_Crate_Military_01_front.png",
            "side": "renders/SM_Prop_Crate_Military_01_side.png",
            "top": "renders/SM_Prop_Crate_Military_01_top.png",
        },
        "suggested_density": "high",
        "affinities": ["depot", "military_base", "outpost"],
    },
    "SM_Prop_Generator_01": {
        "name": "SM_Prop_Generator_01",
        "category": "decorations",
        "placement_role": "infrastructure",
        "tags": ["generator", "power", "industrial", "electric"],
        "description": "Diesel field generator.",
        "bounding_box": {
            "min": [-1.0, -1.5, 0.0],
            "max": [1.0, 1.5, 1.8],
            "size": [2.0, 3.0, 1.8],
            "dimensions": [2.0, 3.0, 1.8],
            "center": [0.0, 0.0, 0.9],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Prop_Generator_01_front.png",
            "side": "renders/SM_Prop_Generator_01_side.png",
            "top": "renders/SM_Prop_Generator_01_top.png",
        },
        "suggested_density": "medium",
        "affinities": ["radar_station", "airfield", "military_base"],
    },
    "SM_Veh_Truck_Military_01": {
        "name": "SM_Veh_Truck_Military_01",
        "category": "vehicles",
        "placement_role": "vehicle",
        "tags": ["truck", "transport", "vehicle", "logistics"],
        "description": "Heavy 6x6 military transport truck.",
        "bounding_box": {
            "min": [-1.5, -3.8, 0.0],
            "max": [1.5, 3.8, 3.2],
            "size": [3.0, 7.6, 3.2],
            "dimensions": [3.0, 7.6, 3.2],
            "center": [0.0, 0.0, 1.6],
            "ground_level_offset": 0.0,
        },
        "render_paths": {
            "front": "renders/SM_Veh_Truck_Military_01_front.png",
            "side": "renders/SM_Veh_Truck_Military_01_side.png",
            "top": "renders/SM_Veh_Truck_Military_01_top.png",
        },
        "suggested_density": "low",
        "affinities": ["depot", "airfield", "military_base"],
    },
}


def load_asset_catalog() -> Dict[str, Dict[str, Any]]:
    """Load asset catalog from JSON file, falling back to default catalog if not present."""
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                prefabs = data.get("assets") or data.get("prefabs") or {}
                if prefabs:
                    # Normalize prefabs
                    normalized = {}
                    for k, v in prefabs.items():
                        name = v.get("name") or v.get("prefab_name") or k
                        bbox = v.get("bounding_box", {})
                        size = bbox.get("size") or bbox.get("dimensions") or [4.0, 4.0, 3.0]
                        center = bbox.get("center") or [0.0, 0.0, size[2] / 2.0]
                        min_v = bbox.get("min") or [-size[0]/2.0, -size[1]/2.0, 0.0]
                        max_v = bbox.get("max") or [size[0]/2.0, size[1]/2.0, size[2]]
                        renders = v.get("render_paths") or {
                            "front": f"renders/{name}_front.png",
                            "side": f"renders/{name}_side.png",
                            "top": f"renders/{name}_top.png",
                        }
                        normalized[name] = {
                            "name": name,
                            "category": v.get("category", "building"),
                            "placement_role": v.get("placement_role", "building"),
                            "tags": v.get("tags", ["military", "structure"]),
                            "description": v.get("description", f"Military asset {name}"),
                            "bounding_box": {
                                "size": [float(s) for s in size],
                                "dimensions": [float(s) for s in size],
                                "center": [float(c) for c in center],
                                "min": [float(m) for m in min_v],
                                "max": [float(m) for m in max_v],
                                "ground_level_offset": float(bbox.get("ground_level_offset", 0.0)),
                            },
                            "render_paths": renders,
                            "suggested_density": v.get("suggested_density", "medium"),
                            "affinities": v.get("affinities", ["military_base", "outpost"]),
                        }
                    # Merge any missing standard test assets from default catalog
                    for def_k, def_v in DEFAULT_SYNTHETIC_CATALOG.items():
                        if def_k not in normalized:
                            normalized[def_k] = def_v
                    return normalized
        except Exception:
            pass

    return DEFAULT_SYNTHETIC_CATALOG


class OBB2D:
    """2D Oriented Bounding Box for SAT collision testing."""
    def __init__(self, cx: float, cz: float, width: float, length: float, yaw_rad: float, buffer: float = 1.5):
        self.cx = cx
        self.cz = cz
        self.hw = (width / 2.0) + buffer
        self.hl = (length / 2.0) + buffer
        self.yaw = yaw_rad
        self.cos_a = math.cos(yaw_rad)
        self.sin_a = math.sin(yaw_rad)

        # 4 vertices in 2D (world space)
        dx1 = self.cos_a * self.hw - self.sin_a * self.hl
        dz1 = self.sin_a * self.hw + self.cos_a * self.hl

        dx2 = -self.cos_a * self.hw - self.sin_a * self.hl
        dz2 = -self.sin_a * self.hw + self.cos_a * self.hl

        self.vertices = [
            (cx + dx1, cz + dz1),
            (cx + dx2, cz + dz2),
            (cx - dx1, cz - dz1),
            (cx - dx2, cz - dz2),
        ]

        # 2 principal normal axes
        self.axes = [
            (self.cos_a, self.sin_a),
            (-self.sin_a, self.cos_a),
        ]


def check_sat_overlap(obb1: OBB2D, obb2: OBB2D) -> bool:
    """Separating Axis Theorem (SAT) test for two 2D OBBs.

    Returns True if overlapping (collision), False if separated.
    """
    axes = obb1.axes + obb2.axes
    for ax, az in axes:
        # Project obb1 vertices
        p1 = [vx * ax + vz * az for vx, vz in obb1.vertices]
        min1, max1 = min(p1), max(p1)

        # Project obb2 vertices
        p2 = [vx * ax + vz * az for vx, vz in obb2.vertices]
        min2, max2 = min(p2), max(p2)

        # If there is a separating axis, no collision
        if max1 < min2 or max2 < min1:
            return False

    return True


def _sample_height_corners(
    heightmap: np.ndarray,
    cx: float,
    cz: float,
    width: float,
    length: float,
    yaw_rad: float,
    terrain_config: TerrainConfig,
) -> Tuple[float, float, float, float, float]:
    """Sample terrain height at center and 4 corners of the oriented building."""
    from .zones import _sample_heightmap_bilinear

    world_w = terrain_config.world_size[0]
    world_l = terrain_config.world_size[2]

    cos_a = math.cos(yaw_rad)
    sin_a = math.sin(yaw_rad)
    hw = width / 2.0
    hl = length / 2.0

    corners = [
        (cx, cz),  # center
        (cx + cos_a * hw - sin_a * hl, cz + sin_a * hw + cos_a * hl),
        (cx - cos_a * hw - sin_a * hl, cz - sin_a * hw + cos_a * hl),
        (cx - cos_a * hw + sin_a * hl, cz - sin_a * hw - cos_a * hl),
        (cx + cos_a * hw + sin_a * hl, cz + sin_a * hw - cos_a * hl),
    ]

    heights = [_sample_heightmap_bilinear(heightmap, px, pz, world_w, world_l) for px, pz in corners]
    return heights[0], heights[1], heights[2], heights[3], heights[4]


def load_zone_templates() -> Dict[str, Any]:
    """Load offline layout templates from JSON, falling back to TEMPLATES_DATA if file missing."""
    if TEMPLATES_FILE.exists():
        try:
            with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "zone_templates" in data:
                    return data
        except Exception:
            pass
    return TEMPLATES_DATA


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


def place_buildings(
    heightmap: np.ndarray,
    zones: List[Zone],
    terrain_config: TerrainConfig,
    catalog: Optional[Dict[str, Dict[str, Any]]] = None,
    templates: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> List[BuildingPlacement]:
    """Place bounding-box aware buildings inside zones using SAT collision avoidance.

    Supports AI-driven offline layout templates with continuous density scaling (0.0 - 1.0).
    """
    if catalog is None:
        catalog = load_asset_catalog()
    if templates is None:
        templates = load_zone_templates()

    zone_templates = templates.get("zone_templates", {})

    uint_seed = int(seed) & 0xFFFFFFFF
    rng = np.random.RandomState((uint_seed + 400) & 0xFFFFFFFF)
    placed_buildings: List[BuildingPlacement] = []
    placed_obbs: List[OBB2D] = []

    # Categorize catalog items
    command_hqs = [k for k, v in catalog.items() if v.get("placement_role") in ["command", "barracks"] or "building" in v.get("category", "")]
    support_structures = [k for k, v in catalog.items() if v.get("placement_role") in ["watchtower", "infrastructure", "radar"] or v.get("category") in ["structures", "building"]]
    defenses_and_props = [k for k, v in catalog.items() if v.get("category") in ["defenses", "decorations", "vehicles", "props"]]

    if not command_hqs:
        command_hqs = list(catalog.keys())
    if not support_structures:
        support_structures = list(catalog.keys())
    if not defenses_and_props:
        defenses_and_props = list(catalog.keys())

    global_bld_idx = 0

    for zone in zones:
        zx, zy, zz = zone.center[0], zone.center[1], zone.center[2]
        z_radius = zone.radius

        # Determine zone type
        z_type = getattr(zone, "zone_type", None) or getattr(zone, "type", None) or "military_base"

        # Continuous density in [0.0, 1.0]
        if isinstance(zone.density, (float, int)):
            d_val = float(zone.density)
        elif isinstance(zone.density, str):
            density_str = zone.density.lower()
            if density_str == "low":
                d_val = 0.30
            elif density_str == "high":
                d_val = 0.90
            elif density_str == "medium":
                d_val = 0.60
            else:
                try:
                    d_val = float(zone.density)
                except ValueError:
                    d_val = 0.60
        else:
            d_val = 0.60
        d_val = max(0.0, min(1.0, d_val))

        # Target count based on density
        if d_val < 0.4:
            target_count = rng.randint(4, 6)
        elif d_val >= 0.75:
            target_count = rng.randint(10, 16)
        else:
            target_count = rng.randint(6, 10)

        zone_obbs: List[OBB2D] = []
        zone_placed_count = 0

        # Template-driven placement
        if z_type in zone_templates:
            tpl = zone_templates[z_type]
            # Collect and sort all subdistrict slots by priority
            candidate_slots = []
            for district in tpl.get("sub_districts", []):
                dist_ox, dist_oz = district.get("center_offset", [0.0, 0.0])
                for slot in district.get("slots", []):
                    thresh = slot.get("density_threshold", 0.0)
                    if d_val >= thresh:
                        prio = slot.get("priority", 10)
                        candidate_slots.append((prio, dist_ox, dist_oz, slot))

            # Sort by priority (1 is highest)
            candidate_slots.sort(key=lambda x: x[0])

            for prio, dist_ox, dist_oz, slot in candidate_slots:
                slot_rx, slot_rz = slot.get("rel_pos", [0.0, 0.0])
                rot_yaw = slot.get("rotation_deg", 0.0)
                rot_yaw_rad = math.radians(rot_yaw)

                raw_ox = dist_ox + slot_rx
                raw_oz = dist_oz + slot_rz
                off_dist = math.hypot(raw_ox, raw_oz)

                # Clamp to zone radius
                max_allowed_r = z_radius * 0.80
                if off_dist > max_allowed_r and off_dist > 1e-4:
                    scale_factor = max_allowed_r / off_dist
                    raw_ox *= scale_factor
                    raw_oz *= scale_factor

                cand_cx = zx + raw_ox
                cand_cz = zz + raw_oz

                candidates = slot.get("candidates", ["SM_Bld_Tent_01"])
                # Pick available candidate from catalog
                chosen_prefab = candidates[0] if candidates else "SM_Bld_Tent_01"
                for cand in candidates:
                    if cand in catalog:
                        chosen_prefab = cand
                        break

                asset_meta = catalog.get(chosen_prefab, DEFAULT_SYNTHETIC_CATALOG.get(chosen_prefab, {}))
                bbox_data = asset_meta.get("bounding_box", {})
                dim = bbox_data.get("size") or bbox_data.get("dimensions") or [6.0, 6.0, 4.0]
                buf = slot.get("buffer_meters", 1.5)

                obb = OBB2D(cand_cx, cand_cz, dim[0], dim[1], rot_yaw_rad, buffer=buf)

                # SAT Collision Check against all previously placed buildings (global & zone)
                collides = False
                for ex_obb in placed_obbs:
                    if check_sat_overlap(obb, ex_obb):
                        collides = True
                        break

                if collides:
                    continue

                # Ground elevation sampling
                h_c, h1, h2, h3, h4 = _sample_height_corners(heightmap, cand_cx, cand_cz, dim[0], dim[1], rot_yaw_rad, terrain_config)
                base_y = min(h1, h2, h3, h4)

                qy = math.sin(rot_yaw_rad / 2.0)
                qw = math.cos(rot_yaw_rad / 2.0)

                zone_obbs.append(obb)
                placed_obbs.append(obb)

                placed_buildings.append(BuildingPlacement(
                    id=f"bld_{global_bld_idx}",
                    zone_id=zone.id,
                    prefab_name=chosen_prefab,
                    category=asset_meta.get("category", "building"),
                    position=[round(cand_cx, 2), round(base_y, 2), round(cand_cz, 2)],
                    rotation=[0.0, round(rot_yaw, 1), 0.0],
                    rotation_euler=[0.0, round(rot_yaw, 1), 0.0],
                    rotation_quaternion=[0.0, round(qy, 4), 0.0, round(qw, 4)],
                    scale=[1.0, 1.0, 1.0],
                    bounding_box=BoundingBox(
                        size=[round(float(s), 3) for s in dim],
                        dimensions=[round(float(s), 3) for s in dim],
                        center=[0.0, 0.0, round(float(dim[2]) / 2.0, 3)],
                        min=[round(float(m), 3) for m in bbox_data.get("min", [-dim[0]/2, -dim[1]/2, 0.0])],
                        max=[round(float(m), 3) for m in bbox_data.get("max", [dim[0]/2, dim[1]/2, dim[2]])],
                    ),
                    faction=str(zone.faction),
                    destruction=str(zone.destruction),
                ))
                global_bld_idx += 1
                zone_placed_count += 1

            # If more buildings are desired for high density, add support props / barriers
            if zone_placed_count < target_count and d_val >= 0.5:
                candidate_pool = support_structures + defenses_and_props
                max_attempts = (target_count - zone_placed_count) * 20
                attempt = 0
                while zone_placed_count < target_count and attempt < max_attempts:
                    attempt += 1
                    asset_name = rng.choice(candidate_pool)
                    asset_data = catalog[asset_name]
                    bbox_info = asset_data["bounding_box"]
                    dim = bbox_info.get("size") or [3.0, 3.0, 2.0]

                    dist = rng.uniform(8.0, z_radius * 0.78)
                    angle = rng.uniform(0.0, 2.0 * math.pi)
                    cand_cx = zx + dist * math.cos(angle)
                    cand_cz = zz + dist * math.sin(angle)
                    cand_yaw = float(rng.uniform(0.0, 360.0))
                    cand_yaw_rad = math.radians(cand_yaw)

                    cand_obb = OBB2D(cand_cx, cand_cz, dim[0], dim[1], cand_yaw_rad, buffer=1.5)

                    collides = False
                    for ex_obb in placed_obbs:
                        if check_sat_overlap(cand_obb, ex_obb):
                            collides = True
                            break
                    if collides:
                        continue

                    h_c, h1, h2, h3, h4 = _sample_height_corners(heightmap, cand_cx, cand_cz, dim[0], dim[1], cand_yaw_rad, terrain_config)
                    base_y = min(h1, h2, h3, h4)
                    qy = math.sin(cand_yaw_rad / 2.0)
                    qw = math.cos(cand_yaw_rad / 2.0)

                    zone_obbs.append(cand_obb)
                    placed_obbs.append(cand_obb)

                    placed_buildings.append(BuildingPlacement(
                        id=f"bld_{global_bld_idx}",
                        zone_id=zone.id,
                        prefab_name=asset_name,
                        category=asset_data.get("category", "building"),
                        position=[round(cand_cx, 2), round(base_y, 2), round(cand_cz, 2)],
                        rotation=[0.0, round(cand_yaw, 1), 0.0],
                        rotation_euler=[0.0, round(cand_yaw, 1), 0.0],
                        rotation_quaternion=[0.0, round(qy, 4), 0.0, round(qw, 4)],
                        scale=[1.0, 1.0, 1.0],
                        bounding_box=BoundingBox(
                            size=[round(float(s), 3) for s in dim],
                            dimensions=[round(float(s), 3) for s in dim],
                            center=[0.0, 0.0, round(float(dim[2]) / 2.0, 3)],
                            min=[round(float(m), 3) for m in bbox_info.get("min", [-dim[0]/2, -dim[1]/2, 0.0])],
                            max=[round(float(m), 3) for m in bbox_info.get("max", [dim[0]/2, dim[1]/2, dim[2]])],
                        ),
                        faction=str(zone.faction),
                        destruction=str(zone.destruction),
                    ))
                    global_bld_idx += 1
                    zone_placed_count += 1

        else:
            # Fallback procedural placement if zone type template not recognized
            target_count = max(4, int(d_val * 16))
            hq_name = rng.choice(command_hqs)
            hq_asset = catalog[hq_name]
            hq_bbox = hq_asset["bounding_box"]
            hq_dim = hq_bbox.get("size") or [8.0, 10.0, 4.0]
            hq_yaw = float(rng.uniform(0.0, 360.0))
            hq_yaw_rad = math.radians(hq_yaw)

            hq_cx = zx + rng.uniform(-2.0, 2.0)
            hq_cz = zz + rng.uniform(-2.0, 2.0)
            hq_obb = OBB2D(hq_cx, hq_cz, hq_dim[0], hq_dim[1], hq_yaw_rad, buffer=2.0)
            zone_obbs.append(hq_obb)
            placed_obbs.append(hq_obb)

            h_c, h1, h2, h3, h4 = _sample_height_corners(heightmap, hq_cx, hq_cz, hq_dim[0], hq_dim[1], hq_yaw_rad, terrain_config)
            base_y = min(h1, h2, h3, h4)
            qy = math.sin(hq_yaw_rad / 2.0)
            qw = math.cos(hq_yaw_rad / 2.0)

            placed_buildings.append(BuildingPlacement(
                id=f"bld_{global_bld_idx}",
                zone_id=zone.id,
                prefab_name=hq_name,
                category=hq_asset.get("category", "building"),
                position=[round(hq_cx, 2), round(base_y, 2), round(hq_cz, 2)],
                rotation=[0.0, round(hq_yaw, 1), 0.0],
                rotation_euler=[0.0, round(hq_yaw, 1), 0.0],
                rotation_quaternion=[0.0, round(qy, 4), 0.0, round(qw, 4)],
                scale=[1.0, 1.0, 1.0],
                bounding_box=BoundingBox(
                    size=[round(float(s), 3) for s in hq_dim],
                    dimensions=[round(float(s), 3) for s in hq_dim],
                    center=[0.0, 0.0, round(float(hq_dim[2]) / 2.0, 3)],
                    min=[round(float(m), 3) for m in hq_bbox.get("min", [-hq_dim[0]/2, -hq_dim[1]/2, 0.0])],
                    max=[round(float(m), 3) for m in hq_bbox.get("max", [hq_dim[0]/2, hq_dim[1]/2, hq_dim[2]])],
                ),
                faction=str(zone.faction),
                destruction=str(zone.destruction),
            ))
            global_bld_idx += 1
            zone_placed_count += 1

            candidate_pool = support_structures + defenses_and_props
            max_attempts = target_count * 20
            attempt = 0
            while zone_placed_count < target_count and attempt < max_attempts:
                attempt += 1
                asset_name = rng.choice(candidate_pool)
                asset_data = catalog[asset_name]
                bbox_info = asset_data["bounding_box"]
                dim = bbox_info.get("size") or [3.0, 3.0, 2.0]

                dist = rng.uniform(8.0, z_radius * 0.78)
                angle = rng.uniform(0.0, 2.0 * math.pi)
                cand_cx = zx + dist * math.cos(angle)
                cand_cz = zz + dist * math.sin(angle)
                cand_yaw = float(rng.uniform(0.0, 360.0))
                cand_yaw_rad = math.radians(cand_yaw)

                cand_obb = OBB2D(cand_cx, cand_cz, dim[0], dim[1], cand_yaw_rad, buffer=1.5)

                collides = False
                for ex_obb in placed_obbs:
                    if check_sat_overlap(cand_obb, ex_obb):
                        collides = True
                        break
                if collides:
                    continue

                h_c, h1, h2, h3, h4 = _sample_height_corners(heightmap, cand_cx, cand_cz, dim[0], dim[1], cand_yaw_rad, terrain_config)
                base_y = min(h1, h2, h3, h4)
                qy = math.sin(cand_yaw_rad / 2.0)
                qw = math.cos(cand_yaw_rad / 2.0)

                zone_obbs.append(cand_obb)
                placed_obbs.append(cand_obb)

                placed_buildings.append(BuildingPlacement(
                    id=f"bld_{global_bld_idx}",
                    zone_id=zone.id,
                    prefab_name=asset_name,
                    category=asset_data.get("category", "building"),
                    position=[round(cand_cx, 2), round(base_y, 2), round(cand_cz, 2)],
                    rotation=[0.0, round(cand_yaw, 1), 0.0],
                    rotation_euler=[0.0, round(cand_yaw, 1), 0.0],
                    rotation_quaternion=[0.0, round(qy, 4), 0.0, round(qw, 4)],
                    scale=[1.0, 1.0, 1.0],
                    bounding_box=BoundingBox(
                        size=[round(float(s), 3) for s in dim],
                        dimensions=[round(float(s), 3) for s in dim],
                        center=[0.0, 0.0, round(float(dim[2]) / 2.0, 3)],
                        min=[round(float(m), 3) for m in bbox_info.get("min", [-dim[0]/2, -dim[1]/2, 0.0])],
                        max=[round(float(m), 3) for m in bbox_info.get("max", [dim[0]/2, dim[1]/2, dim[2]])],
                    ),
                    faction=str(zone.faction),
                    destruction=str(zone.destruction),
                ))
                global_bld_idx += 1
                zone_placed_count += 1

    return placed_buildings
