# Project: WorldGen V2 — Procedural 3D World Designer & Unity Importer

## Architecture
WorldGen V2 enhances the procedural military world generation system with dynamic map sizing, interactive zone CRUD and drag-to-recompute, smooth terrain deformation, AI-templated asset allocation, and adaptive terrain tessellation across four modular subsystems and an automated testing suite:

1. **Asset Pipeline & AI Layouts (R4)**: Headless Blender 2.83.3 CLI bounding box extraction & multi-angle MatCap rendering with Ollama `qwen3.8:27b` VLM enrichment, plus offline JSON layout templates synthesizing structured, high-density layouts for 5 military zone types (`military_base`, `airfield`, `outpost`, `radar_station`, `depot`) supporting continuous density scaling ($0.0 - 1.0$).
2. **Backend Generator (R1, R3, R4)**: FastAPI service managed via `uv`, supporting configurable map dimensions ($0.5 - 10.0$ km), granularity resolution, terrain deformation strength scaling, edge margin offsets, smooth Cosine/Smootherstep C2 zone plateau falloffs, slope/curvature-adaptive 2D Delaunay mesh decimation producing variable-density indexed meshes, strict `max_road_slope` A* road pathfinding, and SAT collision-free building placement.
3. **Interactive 3D Visualizer (R1, R2, R3, R4, R5)**: Vite + Three.js web application adhering to modern web guidance (container queries, CSS custom properties, responsive HUD side panels, utilitarian styling). Features full zone CRUD (Add, Remove, Rename), 3D viewport raycasting drag controls for zone centers, drop-triggered live backend recomputation without page reload, adaptive decimated mesh rendering with wireframe inspection, and continuous density sliders.
4. **Unity Importer Package (R3, R4)**: Unity Editor C# package (`WorldManifestImporter.cs`) parsing `world_manifest.json`, instantiating Unity `TerrainData` and `AdaptiveTerrainMesh` GameObjects (with `MeshFilter`, `MeshRenderer`, `MeshCollider`, 32-bit index buffers), instantiating Synty PolygonMilitary prefabs via `PrefabUtility.InstantiatePrefab`, and swapping material textures for factions A/B/C and destruction levels 01-04.
5. **E2E Testing Track**: Comprehensive test suite covering Tiers 1-4 (feature coverage, boundaries, combinatorial, and real-world workloads) with automated programmatic tests for map dimensions, mesh indices, and road slope limits, plus Agent-as-Judge review rubrics for zone drag/recompute and adaptive mesh loading.

```
[Synty PolygonMilitary Assets] + [Ollama qwen3.8:27b VLM / Layout Templates]
                          │
                          ▼
            [FastAPI Generator Backend V2]
 (Perlin + Deformation + Smooth Falloff + Adaptive Decimation + A* Road Limits)
                          │
                          ▼ (world_manifest.json)
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
[Three.js Interactive Frontend V2]   [Unity C# Importer V2]
 (Zone CRUD + Drag-Recompute +       (AdaptiveTerrainMesh +
  Adaptive Mesh + Continuous Density)  PrefabUtility + Material Swap)
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Global Map Dimensions (km) | Configurable width/length in kilometers (0.5 - 10.0 km) with grid cell scaling | M1 | V2 R1 |
| 2 | Granularity & Resolution Control | Resolution slider (65 - 1025) controlling heightmap and base grid detail | M1 | V2 R1 |
| 3 | Terrain Deformation Multiplier | Deformation strength slider scaling domain warp and fractal persistence | M1 | V2 R1 |
| 4 | Edge Margin Offset | Parameter constraining zone placements away from map borders | M1 | V2 R1 |
| 5 | Smooth Zone Flattening Falloff | Cosine and Smootherstep C2 non-linear falloff for plateau blending | M1 | V2 R1 |
| 6 | Strict Road Slope Limits | A* pathfinding enforcing `max_road_slope` gradient constraint | M1 | V2 R3 |
| 7 | Backend Adaptive Mesh Decimation | Slope/curvature-adaptive 2D Delaunay mesh decimation (variable density) | M2 | V2 R3 |
| 8 | AI-Driven JSON Layout Templates | Structured zone templates across 5 zone types generated via Qwen VLM | M2 | V2 R4 |
| 9 | Continuous Density Scaling | Continuous float density slider (0.0 - 1.0) activating template slots | M2 | V2 R4 |
| 10 | SAT Collision-Free Template Placement | Multi-tier sub-district template instantiation with SAT OBB checking | M2 | V2 R4 |
| 11 | Zone CRUD Side Panel UI | Add, Remove, and Rename zones in the React/HUD side panel | M3 | V2 R2 |
| 12 | Draggable Zone Centers (3D Viewport) | 3D raycasting drag controls for zone beacons in Three.js | M3 | V2 R2 |
| 13 | Viewport Drag-Drop Recomputation | Drop triggers backend recomputation and updates scene in-place | M3 | V2 R2 |
| 14 | Three.js Adaptive Decimated Mesh | Ingesting and rendering variable-density triangle mesh with wireframe mode | M3 | V2 R3 |
| 15 | Utilitarian UI Cleanup & Standards | Stripping AI marketing copy, modern web guidance compliance | M3 | V2 R5 |
| 16 | Unity Adaptive Decimated Mesh Loader | Instantiating `AdaptiveTerrainMesh` with 32-bit index buffers in Unity | M4 | V2 R3 |
| 17 | Unity Templated Zone Hierarchy | Instantiating AI-templated buildings with faction/destruction materials | M4 | V2 R4 |
| 18 | Programmatic Dimension & Mesh Tests | Automated Pytest tests for dimension scaling and mesh index validity | Test Track | V2 Acceptance Criteria |
| 19 | Programmatic Road Slope Tests | Automated tests verifying road waypoints adhere to `max_road_slope` | Test Track | V2 Acceptance Criteria |
| 20 | Frontend & Unity Review Rubrics | Agent-as-Judge rubrics for zone drag/recompute and adaptive mesh loading | Test Track | V2 Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| Test | E2E Testing Track Update | Programmatic tests for dimensions, mesh indices, road slope; V2 rubrics | none | IN_PROGRESS |
| M1 | Backend Global Params & Road Limits | Schemas, map km sizing, deformation, smooth falloff, A* max_road_slope | none | PLANNED |
| M2 | Backend Adaptive Mesh & AI Templates | Curvature Delaunay decimation, Qwen layout templates, continuous density | M1 | PLANNED |
| M3 | Frontend V2 Overhaul | Zone CRUD, 3D viewport drag-to-recompute, adaptive mesh, utilitarian UI | M1, M2 | PLANNED |
| M4 | Unity Importer V2 | AdaptiveTerrainMesh loader, 32-bit index buffers, C# tests | M1, M2 | PLANNED |
| M5 | E2E Integration & Adversarial Hardening | 100% E2E test pass, Tier 5 stress-testing, Forensic Integrity Audit | M1, M2, M3, M4, Test | PLANNED |

## Interface Contracts

### 1. `world_manifest.json` Contract (V2 Extended)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "metadata": {
    "version": "2.0.0",
    "seed": 42,
    "created_at": "2026-09-02T12:00:00Z",
    "generator": "FastAPI Procedural WorldGen v2.0"
  },
  "terrain": {
    "resolution": 513,
    "world_size": [1000.0, 150.0, 1000.0],
    "heightmap": [[0.0, ...]],
    "mesh": {
      "vertices": [[0.0, 10.5, 0.0], [50.0, 12.0, 0.0], ...],
      "indices": [0, 1, 2, ...],
      "normals": [[0.0, 1.0, 0.0], ...],
      "uvs": [[0.0, 0.0], ...],
      "vertex_count": 14250,
      "triangle_count": 28100,
      "decimation_ratio": 0.053
    }
  },
  "zones": [
    {
      "id": "zone_0",
      "name": "Military Outpost Alpha",
      "faction": "A",
      "destruction": "02",
      "density": 0.65,
      "zone_type": "military_base",
      "center": [250.0, 42.5, 300.0],
      "radius": 85.0,
      "footprint_points": [[240.0, 310.0], ...]
    }
  ],
  "buildings": [
    {
      "id": "bld_0",
      "zone_id": "zone_0",
      "prefab_name": "SM_Bld_Tent_01",
      "placement_role": "barracks",
      "position": [245.0, 42.5, 295.0],
      "rotation": [0.0, 45.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "bounding_box": {
        "size": [7.799, 12.030, 4.072],
        "center": [0.0, 0.0, 2.036]
      }
    }
  ],
  "roads": [
    {
      "id": "road_0_1",
      "from_zone": "zone_0",
      "to_zone": "zone_1",
      "width": 6.0,
      "max_slope_observed": 0.182,
      "waypoints": [[250.0, 42.5, 300.0], [260.0, 41.2, 320.0], ...]
    }
  ]
}
```

### 2. `templates.json` Contract
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "version": "2.0.0",
  "zone_templates": {
    "military_base": {
      "type": "military_base",
      "display_name": "Fortified Military Base",
      "sub_districts": [
        {
          "district_id": "command_core",
          "center_offset": [0.0, 0.0],
          "slots": [
            {
              "slot_id": "hq_main",
              "rel_pos": [0.0, 0.0],
              "placement_role": "command",
              "candidates": ["SM_Bld_Village_House_01", "SM_Bld_Tent_01"],
              "density_threshold": 0.0,
              "buffer_meters": 3.0,
              "priority": 1
            }
          ]
        }
      ]
    }
  }
}
```

## Code Layout
```
/Users/jack/worldgen/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── schemas.py
│   │   ├── generator/
│   │   │   ├── terrain.py
│   │   │   ├── erosion.py
│   │   │   ├── mesh.py          <-- New adaptive mesh decimation
│   │   │   ├── zones.py
│   │   │   ├── buildings.py
│   │   │   ├── roads.py
│   │   │   └── pipeline.py
│   │   └── catalog/
│   │       ├── builder.py
│   │       ├── blender_extract.py
│   │       ├── vlm_enrich.py
│   │       ├── generate_templates.py <-- AI Qwen layout template generator
│   │       ├── templates.json        <-- Cached offline layout templates
│   │       └── catalog.json
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── style.css
│       ├── scene/
│       │   ├── viewer.js         <-- Zone center raycast drag controls
│       │   ├── terrain.js        <-- Adaptive decimated mesh BufferGeometry
│       │   ├── zones.js          <-- Dynamic zone drag preview
│       │   ├── buildings.js
│       │   └── roads.js
│       ├── components/
│       │   ├── hud.js
│       │   ├── terrain_panel.js  <-- Global parameters (km, res, deformation)
│       │   ├── zone_panel.js     <-- Zone CRUD & continuous density slider
│       │   └── catalog_browser.js
│       └── api/
│           └── client.js         <-- Recompute endpoint & offline generator
├── unity/
│   ├── Assets/
│   │   └── Editor/
│   │       └── WorldManifestImporter.cs <-- AdaptiveTerrainMesh builder
│   ├── stubs/
│   │   ├── UnityEngineStubs.cs
│   │   └── UnityEditorStubs.cs
│   └── tests/
│       ├── WorldImporterTests.cs
│       └── AdversarialImporterTests.cs
├── tests/
│   ├── conftest.py
│   ├── test_manifest_schema.py
│   ├── test_generator.py
│   ├── test_catalog.py
│   ├── test_e2e_pipeline.py
│   ├── test_map_dimensions.py   <-- New programmatic dimension tests
│   ├── test_adaptive_mesh.py    <-- New programmatic mesh decimation tests
│   ├── test_road_slope_limits.py<-- New programmatic road slope tests
│   ├── test_layout_templates.py <-- New layout template tests
│   ├── validate_catalog.py
│   └── rubrics/
│       ├── frontend_rubric.md   <-- Updated V2 Agent-as-Judge rubric
│       └── unity_rubric.md      <-- Updated V2 Agent-as-Judge rubric
├── PROJECT.md
└── TEST_READY.md
```
