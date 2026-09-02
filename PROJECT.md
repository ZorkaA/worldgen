# Project: Procedural 3D Military World Designer & Unity Importer

## Architecture
A full-stack procedural 3D military world generation system composed of four modular subsystems and a comprehensive testing suite:
1. **Asset Pipeline (R1)**: Headless Blender 2.83.3 CLI script for 3D AABB/OBB bounding box extraction and multi-angle Workbench MatCap rendering (front, side, top), integrated with local Ollama `qwen3.8:27b` VLM vision inference and persistent `catalog.json` caching.
2. **Backend Generator (R2)**: FastAPI service managed via `uv`, implementing multifractal Perlin noise with domain warping, high-performance Numba JIT droplet hydraulic erosion, Bridson's 2D Poisson-disc zone distribution, organic zone flattening, Separating Axis Theorem (SAT) collision-free building placement, slope-aware A* road pathfinding, and REST export endpoints producing `world_manifest.json`.
3. **Interactive 3D Visualizer (R3)**: Vite + Three.js web application adhering to modern web guidance (container queries, CSS custom properties, responsive HUD side panels), rendering displaced heightmap terrain, zone footprints, building wireframes/meshes, road splines, and interactive catalog browser with live API synchronization.
4. **Unity Importer Package (R4)**: Unity Editor C# package (`WorldManifestImporter.cs`) providing an Editor window to parse `world_manifest.json`, instantiate Unity `TerrainData` with heightmap scaling, instantiate Synty PolygonMilitary prefabs via `PrefabUtility.InstantiatePrefab`, and swap material textures (`_MainTex` and `_BumpMap`) for factions A/B/C and destruction levels 01-04.
5. **E2E Testing Track**: Comprehensive test suite covering Tiers 1-4 (feature coverage, boundaries, combinatorial, and real-world workloads) with automated schema validation and agent review rubrics.

```
[Synty PolygonMilitary Assets]
       │
       ▼
[R1: Asset Catalog Builder] (Blender CLI + Ollama VLM qwen3.8:27b)
       │
       ▼ (catalog.json)
[R2: FastAPI Generator Backend] (Perlin + Numba Erosion + Poisson + SAT + A* Road)
       │
       ▼ (world_manifest.json)
       ├─────────────────────────────────────┐
       ▼                                     ▼
[R3: Three.js Interactive Frontend]   [R4: Unity C# Editor Importer]
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Blender Bounding Box Extraction | Headless script extracting min/max/dimensions/center across mesh hierarchies | M1 | R1 |
| 2 | Multi-Angle Render Pipeline | Automated 3-angle (front, side, top) MatCap renders with auto-framing | M1 | R1 |
| 3 | Ollama VLM Asset Enrichment | Prompting `qwen3.8:27b` with multi-image input to extract tags, roles, description | M1 | R1 |
| 4 | Asset Catalog Caching | JSON schema validation and file-mtime/hash caching into `catalog.json` | M1 | R1 |
| 5 | Multifractal Perlin & Domain Warping | Procedural heightmap synthesis with configurable octaves, persistence, lacunarity | M2 | R2 |
| 6 | Numba Hydraulic Erosion | Accelerated droplet physics simulation (inertia, capacity, erosion, deposition) | M2 | R2 |
| 7 | Poisson-Disc Zone Distribution | Bridson's algorithm for organic military zone placement and terrain flattening | M2 | R2 |
| 8 | SAT OBB Building Placement | Non-overlapping building footprint layout respecting bboxes & terrain height | M2 | R2 |
| 9 | Slope-Aware A* Road Routing | Least-cost pathfinding connecting zones with grade penalties and smoothing | M2 | R2 |
| 10 | World Manifest Export API | FastAPI `/generate`, `/manifest`, `/catalog`, `/health` endpoints | M2 | R2 |
| 11 | Three.js Heightmap Terrain Mesh | Dynamic elevation displacement mesh with slope shading and wireframe mode | M3 | R3 |
| 12 | Zone & Building 3D Visualizer | Color-coded zone boundaries, building boxes/meshes, and road spline ribbons | M3 | R3 |
| 13 | Interactive Config Side Panels | Modern HUD panels for terrain parameters, zone attributes, and live regeneration | M3 | R3 |
| 14 | Asset Catalog Browser UI | Visual gallery with multi-angle renders, tags, search, and filter | M3 | R3 |
| 15 | Unity Terrain Heightmap Instantiation | C# script converting manifest heights to Unity `TerrainData` | M4 | R4 |
| 16 | Prefab Spawning via PrefabUtility | Spawning prefabs preserving asset links grouped under zone GameObjects | M4 | R4 |
| 17 | Faction & Destruction Material Swapping | Dynamic texture assignment (`_MainTex`, `_BumpMap`) for Factions A-C & Damage 01-04 | M4 | R4 |
| 18 | Automated API & Manifest Schema Tests | Pytest test suite validating endpoints and `world_manifest.json` schema | Test Track | Acceptance Criteria |
| 19 | Catalog Schema Validation Tool | Standalone validation CLI ensuring valid float bboxes & string array tags | Test Track | Acceptance Criteria |
| 20 | Frontend & Unity Agent-as-Judge Rubrics | Review rubrics verifying modern frontend patterns and Unity C# logic | Test Track | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| Test | E2E Testing Track | Test harness, validators, Tiers 1-4 tests, TEST_READY.md | none | DONE |
| M1 | Asset Catalog Builder | Blender CLI bbox/render pipeline, Ollama VLM, `catalog.json` | none | DONE |
| M2 | Procedural Generator Backend | FastAPI, Perlin, Numba erosion, Poisson zones, SAT buildings, A* roads | M1 (catalog) | DONE |
| M3 | Interactive 3D Frontend | Vite + Three.js, visualizer, modern HUD side panels, catalog browser | M2 (API/manifest) | DONE |
| M4 | Unity Importer Package | C# Editor script, TerrainData, PrefabUtility, material swap | M2 (manifest) | DONE |
| M5 | E2E Pass & Adversarial Hardening | Pass 100% E2E tests (Tiers 1-4) + Tier 5 adversarial verification | M1, M2, M3, M4, Test | DONE |

## Interface Contracts

### 1. `catalog.json` Contract
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "version": "1.0.0",
  "assets": {
    "<prefab_or_model_name>": {
      "name": "SM_Bld_Tent_01",
      "category": "building",
      "placement_role": "barracks",
      "tags": ["tent", "military", "shelter", "barracks"],
      "description": "Standard military barracks canvas tent.",
      "bounding_box": {
        "min": [-3.899, -6.015, 0.0],
        "max": [3.899, 6.015, 4.072],
        "size": [7.799, 12.030, 4.072],
        "center": [0.0, 0.0, 2.036]
      },
      "render_paths": {
        "front": "renders/SM_Bld_Tent_01_front.png",
        "side": "renders/SM_Bld_Tent_01_side.png",
        "top": "renders/SM_Bld_Tent_01_top.png"
      },
      "affinities": ["military_base", "outpost"],
      "suggested_density": "medium"
    }
  }
}
```

### 2. `world_manifest.json` Contract
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "metadata": {
    "version": "1.0.0",
    "seed": 42,
    "created_at": "2026-09-01T22:00:00Z",
    "generator": "FastAPI Procedural WorldGen v1.0"
  },
  "terrain": {
    "resolution": 513,
    "world_size": [1000.0, 150.0, 1000.0],
    "heightmap": [[0.0, ...]]
  },
  "zones": [
    {
      "id": "zone_0",
      "name": "Military Outpost Alpha",
      "faction": "A",
      "destruction": "02",
      "density": "high",
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
      "waypoints": [[250.0, 42.5, 300.0], [260.0, 41.2, 320.0], ...]
    }
  ]
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
│   │   │   ├── zones.py
│   │   │   ├── buildings.py
│   │   │   └── roads.py
│   │   └── catalog/
│   │       ├── builder.py
│   │       ├── blender_extract.py
│   │       ├── vlm_enrich.py
│   │       └── catalog.json
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── style.css
│       ├── scene/
│       │   ├── viewer.js
│       │   ├── terrain.js
│       │   ├── zones.js
│       │   ├── buildings.js
│       │   └── roads.js
│       ├── components/
│       │   ├── hud.js
│       │   ├── terrain_panel.js
│       │   ├── zone_panel.js
│       │   └── catalog_browser.js
│       └── api/
│           └── client.js
├── unity/
│   └── Assets/
│       └── Editor/
│           └── WorldManifestImporter.cs
├── tests/
│   ├── conftest.py
│   ├── test_manifest_schema.py
│   ├── test_generator.py
│   ├── test_catalog.py
│   ├── test_e2e_pipeline.py
│   ├── validate_catalog.py
│   └── rubrics/
│       ├── frontend_rubric.md
│       └── unity_rubric.md
├── PROJECT.md
└── TEST_READY.md
```
