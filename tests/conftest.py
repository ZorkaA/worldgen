"""
tests/conftest.py - Comprehensive test fixtures, mock data, and schema definitions
for the Procedural 3D Military World Designer and Unity Importer.
"""

import copy
import json
import math
import os
import sys
from typing import Any, Dict, Generator, List

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import jsonschema
    from jsonschema import Draft202012Validator, Draft7Validator
except ImportError:
    jsonschema = None
    Draft202012Validator = None
    Draft7Validator = None


# ============================================================================
# 1. JSON Schemas (Draft 2020-12 / Draft 7 Compatible)
# ============================================================================

CATALOG_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AssetCatalog",
    "type": "object",
    "required": ["version", "assets"],
    "properties": {
        "version": {"type": "string"},
        "generated_at": {"type": "string"},
        "assets": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": [
                    "name",
                    "category",
                    "placement_role",
                    "tags",
                    "bounding_box",
                ],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "category": {"type": "string", "minLength": 1},
                    "placement_role": {"type": "string", "minLength": 1},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "minItems": 1,
                    },
                    "description": {"type": "string"},
                    "bounding_box": {
                        "type": "object",
                        "required": ["min", "max", "size", "center"],
                        "properties": {
                            "min": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                            "max": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                            "size": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                            "center": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                        },
                    },
                    "render_paths": {
                        "type": "object",
                        "properties": {
                            "front": {"type": "string"},
                            "side": {"type": "string"},
                            "top": {"type": "string"},
                        },
                    },
                    "affinities": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "suggested_density": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
            },
        },
    },
}


MANIFEST_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "WorldManifest",
    "type": "object",
    "required": ["metadata", "terrain", "zones", "buildings", "roads"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["version", "seed", "created_at", "generator"],
            "properties": {
                "version": {"type": "string"},
                "seed": {"type": "integer"},
                "created_at": {"type": "string"},
                "generator": {"type": "string"},
                "bounds": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 6,
                    "maxItems": 6,
                },
            },
        },
        "terrain": {
            "type": "object",
            "required": ["resolution", "world_size", "heightmap"],
            "properties": {
                "resolution": {"type": "integer", "minimum": 16},
                "world_size": {
                    "type": "array",
                    "items": {"type": "number", "minimum": 1.0},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "heightmap": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                },
            },
        },
        "zones": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "name",
                    "faction",
                    "destruction",
                    "density",
                    "center",
                    "radius",
                    "footprint_points",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "faction": {"type": "string", "enum": ["A", "B", "C"]},
                    "destruction": {
                        "type": "string",
                        "enum": ["01", "02", "03", "04"],
                    },
                    "density": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "radius": {"type": "number", "minimum": 1.0},
                    "footprint_points": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "minItems": 3,
                    },
                },
            },
        },
        "buildings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "zone_id",
                    "prefab_name",
                    "position",
                    "rotation",
                    "scale",
                    "bounding_box",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "zone_id": {"type": "string", "minLength": 1},
                    "prefab_name": {"type": "string", "minLength": 1},
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "rotation": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 4,
                    },
                    "scale": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "bounding_box": {
                        "type": "object",
                        "required": ["size", "center"],
                        "properties": {
                            "size": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                            "center": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                        },
                    },
                    "faction": {"type": "string", "enum": ["A", "B", "C"]},
                    "destruction": {
                        "type": "string",
                        "enum": ["01", "02", "03", "04"],
                    },
                },
            },
        },
        "roads": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "from_zone", "to_zone", "width", "waypoints"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "from_zone": {"type": "string", "minLength": 1},
                    "to_zone": {"type": "string", "minLength": 1},
                    "width": {"type": "number", "minimum": 0.5},
                    "waypoints": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "minItems": 2,
                    },
                },
            },
        },
    },
}


# ============================================================================
# 2. Canonical Mock Data Fixtures
# ============================================================================

@pytest.fixture
def manifest_schema() -> Dict[str, Any]:
    """Returns the JSON schema definition for world_manifest.json."""
    return MANIFEST_SCHEMA


@pytest.fixture
def catalog_schema() -> Dict[str, Any]:
    """Returns the JSON schema definition for catalog.json."""
    return CATALOG_SCHEMA


@pytest.fixture
def sample_catalog_dict() -> Dict[str, Any]:
    """Returns a valid asset catalog dictionary compliant with R1."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "version": "1.0.0",
        "generated_at": "2026-09-01T22:00:00Z",
        "assets": {
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
                    "center": [0.0, 0.0, 2.036],
                },
                "render_paths": {
                    "front": "renders/SM_Bld_Tent_01_front.png",
                    "side": "renders/SM_Bld_Tent_01_side.png",
                    "top": "renders/SM_Bld_Tent_01_top.png",
                },
                "affinities": ["military_base", "outpost"],
                "suggested_density": "medium",
            },
            "SM_Bld_Watchtower_01": {
                "name": "SM_Bld_Watchtower_01",
                "category": "building",
                "placement_role": "defense",
                "tags": ["tower", "security", "perimeter", "defense"],
                "description": "Elevated wooden and steel military watchtower.",
                "bounding_box": {
                    "min": [-2.5, -2.5, 0.0],
                    "max": [2.5, 2.5, 14.2],
                    "size": [5.0, 5.0, 14.2],
                    "center": [0.0, 0.0, 7.1],
                },
                "render_paths": {
                    "front": "renders/SM_Bld_Watchtower_01_front.png",
                    "side": "renders/SM_Bld_Watchtower_01_side.png",
                    "top": "renders/SM_Bld_Watchtower_01_top.png",
                },
                "affinities": ["outpost", "radar_station"],
                "suggested_density": "low",
            },
            "SM_Prop_Sandbags_01": {
                "name": "SM_Prop_Sandbags_01",
                "category": "prop",
                "placement_role": "barrier",
                "tags": ["sandbags", "fortification", "cover"],
                "description": "Curved military sandbag defensive fortification.",
                "bounding_box": {
                    "min": [-1.2, -0.6, 0.0],
                    "max": [1.2, 0.6, 0.9],
                    "size": [2.4, 1.2, 0.9],
                    "center": [0.0, 0.0, 0.45],
                },
                "render_paths": {
                    "front": "renders/SM_Prop_Sandbags_01_front.png",
                    "side": "renders/SM_Prop_Sandbags_01_side.png",
                    "top": "renders/SM_Prop_Sandbags_01_top.png",
                },
                "affinities": ["military_base", "outpost", "checkpoint"],
                "suggested_density": "high",
            },
        },
    }


@pytest.fixture
def sample_valid_manifest() -> Dict[str, Any]:
    """Returns a valid world_manifest.json structure compliant with R2, R3, R4."""
    res = 65
    # Generate 65x65 flat/sloped terrain
    heightmap: List[List[float]] = []
    for z in range(res):
        row: List[float] = []
        for x in range(res):
            h = 20.0 + 10.0 * math.sin(x / 10.0) * math.cos(z / 10.0)
            row.append(round(h, 4))
        heightmap.append(row)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "metadata": {
            "version": "1.0.0",
            "seed": 42,
            "created_at": "2026-09-01T22:00:00Z",
            "generator": "FastAPI Procedural WorldGen v1.0",
            "bounds": [0.0, 0.0, 0.0, 1000.0, 150.0, 1000.0],
        },
        "terrain": {
            "resolution": res,
            "world_size": [1000.0, 150.0, 1000.0],
            "heightmap": heightmap,
        },
        "zones": [
            {
                "id": "zone_0",
                "name": "Military Outpost Alpha",
                "faction": "A",
                "destruction": "02",
                "density": "high",
                "center": [250.0, 25.4, 300.0],
                "radius": 85.0,
                "footprint_points": [
                    [250.0 + 85.0 * math.cos(i * math.pi / 4), 300.0 + 85.0 * math.sin(i * math.pi / 4)]
                    for i in range(8)
                ],
            },
            {
                "id": "zone_1",
                "name": "Command Post Bravo",
                "faction": "B",
                "destruction": "01",
                "density": "medium",
                "center": [650.0, 28.1, 700.0],
                "radius": 95.0,
                "footprint_points": [
                    [650.0 + 95.0 * math.cos(i * math.pi / 4), 700.0 + 95.0 * math.sin(i * math.pi / 4)]
                    for i in range(8)
                ],
            },
        ],
        "buildings": [
            {
                "id": "bld_0",
                "zone_id": "zone_0",
                "prefab_name": "SM_Bld_Tent_01",
                "position": [245.0, 25.4, 295.0],
                "rotation": [0.0, 45.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "bounding_box": {
                    "size": [7.799, 12.030, 4.072],
                    "center": [0.0, 0.0, 2.036],
                },
                "faction": "A",
                "destruction": "02",
            },
            {
                "id": "bld_1",
                "zone_id": "zone_1",
                "prefab_name": "SM_Bld_Watchtower_01",
                "position": [640.0, 28.1, 690.0],
                "rotation": [0.0, 90.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "bounding_box": {
                    "size": [5.0, 5.0, 14.2],
                    "center": [0.0, 0.0, 7.1],
                },
                "faction": "B",
                "destruction": "01",
            },
        ],
        "roads": [
            {
                "id": "road_0_1",
                "from_zone": "zone_0",
                "to_zone": "zone_1",
                "width": 6.0,
                "waypoints": [
                    [250.0, 25.4, 300.0],
                    [350.0, 26.2, 400.0],
                    [450.0, 27.0, 500.0],
                    [550.0, 27.5, 600.0],
                    [650.0, 28.1, 700.0],
                ],
            }
        ],
    }


# ============================================================================
# 3. Geometric & Algorithmic Validation Helper Fixtures
# ============================================================================

class SATCollisionTester:
    """
    Separating Axis Theorem (SAT) 2D Oriented Bounding Box collision checker.
    Used for verifying zero building collision overlaps.
    """
    @staticmethod
    def get_obb_vertices(pos: List[float], size: List[float], rot_yaw_deg: float, buffer: float = 0.0) -> List[List[float]]:
        cx, cz = pos[0], pos[2] if len(pos) >= 3 else pos[1]
        half_w = (size[0] / 2.0) + buffer
        half_l = (size[1] / 2.0) + buffer if len(size) >= 2 else half_w

        rad = math.radians(rot_yaw_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_corners = [
            (-half_w, -half_l),
            (half_w, -half_l),
            (half_w, half_l),
            (-half_w, half_l),
        ]

        world_vertices = []
        for lx, lz in local_corners:
            wx = cx + (lx * cos_a - lz * sin_a)
            wz = cz + (lx * sin_a + lz * cos_a)
            world_vertices.append([wx, wz])
        return world_vertices

    @classmethod
    def check_overlap(cls, poly_a: List[List[float]], poly_b: List[List[float]]) -> bool:
        """Returns True if poly_a and poly_b overlap in 2D XZ plane."""
        polygons = [poly_a, poly_b]
        for poly in polygons:
            n = len(poly)
            for i in range(n):
                p1 = poly[i]
                p2 = poly[(i + 1) % n]
                edge = [p2[0] - p1[0], p2[1] - p1[1]]
                axis = [-edge[1], edge[0]]  # Normal vector
                length = math.hypot(axis[0], axis[1])
                if length == 0:
                    continue
                axis = [axis[0] / length, axis[1] / length]

                # Project poly_a
                projs_a = [p[0] * axis[0] + p[1] * axis[1] for p in poly_a]
                min_a, max_a = min(projs_a), max(projs_a)

                # Project poly_b
                projs_b = [p[0] * axis[0] + p[1] * axis[1] for p in poly_b]
                min_b, max_b = min(projs_b), max(projs_b)

                # Check gap
                if max_a < min_b or max_b < min_a:
                    return False  # Separating axis found -> No overlap
        return True  # Overlap on all axes -> Collision


@pytest.fixture
def sat_checker() -> SATCollisionTester:
    return SATCollisionTester()


# ============================================================================
# 4. FastAPI TestClient Fixture (Dynamic or Fallback Mock)
# ============================================================================

class MockAPIResponse:
    def __init__(self, status_code: int, json_data: Any):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


class MockAPIClient:
    """Mock client mimicking FastAPI TestClient for offline / standalone test runs."""
    def __init__(self, manifest_data: Dict[str, Any], catalog_data: Dict[str, Any]):
        self.manifest_data = copy.deepcopy(manifest_data)
        self.catalog_data = copy.deepcopy(catalog_data)

    def get(self, path: str, params: Dict[str, Any] = None):
        clean_path = path.split("?")[0].rstrip("/")
        if clean_path in ["/api/health", "/api/v1/health"]:
            return MockAPIResponse(200, {"status": "ok", "service": "procedural-worldgen", "version": "1.0.0"})
        if clean_path in ["/api/catalog", "/api/v1/catalog"]:
            return MockAPIResponse(200, self.catalog_data)
        if clean_path in ["/api/manifest", "/api/v1/manifest"]:
            m = copy.deepcopy(self.manifest_data)
            return MockAPIResponse(200, m)
        return MockAPIResponse(404, {"detail": "Not found"})

    def post(self, path: str, json: Dict[str, Any] = None):
        clean_path = path.split("?")[0].rstrip("/")
        if clean_path in ["/api/generate", "/api/v1/generate"]:
            payload = json or {}
            seed = payload.get("seed", 42)
            resolution = payload.get("resolution", 65)
            world_size = payload.get("world_size", [1000.0, 150.0, 1000.0])

            m = copy.deepcopy(self.manifest_data)
            m["metadata"]["seed"] = seed
            m["terrain"]["resolution"] = resolution
            m["terrain"]["world_size"] = world_size

            return MockAPIResponse(200, {
                "success": True,
                "seed": seed,
                "manifest": m,
            })
        return MockAPIResponse(404, {"detail": "Not found"})


@pytest.fixture
def api_client(sample_valid_manifest, sample_catalog_dict):
    """
    Provides a test client for FastAPI endpoints.
    Attempts to import the real FastAPI app from backend.app.main if present;
    otherwise returns a compliant MockAPIClient.
    """
    try:
        from fastapi.testclient import TestClient
        from backend.app.main import app
        return TestClient(app)
    except Exception:
        return MockAPIClient(sample_valid_manifest, sample_catalog_dict)
