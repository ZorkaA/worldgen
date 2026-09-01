# Comprehensive Technical Specification & Verification Report
## R3: Interactive 3D Frontend (Vite + Three.js)
## R4: Unity Importer Package (C#)
## Acceptance Criteria & E2E Testing Suite

---

## 1. Executive Summary & Specification Scope
This document specifies the technical architecture, data contracts, mathematical/geometric formulations, UI layout standards, Unity Editor integration, and end-to-end verification rubrics for:
1. **R3: Interactive 3D Frontend** — A modern web-based world viewer built with Vite, Three.js, and modern CSS/HTML APIs compliant with the `modern-web-guidance` standard.
2. **R4: Unity Importer Package** — A robust C# Unity Editor extension that deserializes `world_manifest.json`, instantiates Unity Terrain with exact heightmap dimensions, instantiates linked prefabs via `PrefabUtility.InstantiatePrefab`, and executes automated material/texture swapping for Synty PolygonMilitary assets based on zone faction (`A`, `B`, `C`) and destruction level (`01`, `02`, `03`, `04`).
3. **Acceptance Criteria & E2E Testing Suite** — Automated test harness including pytest suites (`test_manifest_schema.py`, `test_generator.py`), catalog validator (`validate_catalog.py`), and formal review rubrics for Frontend and Unity code.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R3 Frontend: Rendering | WebGL Scene & Camera Setup | Three.js `WebGLRenderer` (antialias, sRGB encoding, shadowMap), `PerspectiveCamera` (FOV 60, aspect ratio, near 0.1, far 2000), `OrbitControls` with smooth damping and distance constraints. | Canvas element, window resize events, mouse/touch drag | Render loop updating canvas at 60fps | Falls back to WebGL 1.0 or shows WebGL not supported banner | ORIGINAL_REQUEST.md § R3 |
| 2 | R3 Frontend: Rendering | Directional & Ambient Lighting | Directional sunlight (with soft shadows, position `[100, 200, 100]`, shadow camera frustum covering world bounds) and Hemisphere/Ambient light for fill illumination. | Sun position, color, intensity | Dynamic illumination of terrain and building geometries | Clamps invalid intensities to [0.0, 5.0] | ORIGINAL_REQUEST.md § R3 |
| 3 | R3 Frontend: Terrain | Heightmap Mesh Instantiation | `PlaneGeometry` with vertex resolution matching manifest (e.g., 256x256 or 512x512) rotated to horizontal (XZ plane), vertex heights displaced from 1D/2D `Float32Array` elevation data. | Heightmap float array, world dimensions `[width, length, heightScale]` | Dynamic `MeshStandardMaterial` or vertex-colored terrain mesh with computed normals | Displays flat plane if height array is missing or mismatched | ORIGINAL_REQUEST.md § R3 |
| 4 | R3 Frontend: Terrain | Slope/Height Shader Coloring | Multi-pass or custom vertex/fragment shader mapping elevation and normal gradient to biome colors (water/sand, grass, rock cliffs, mountain snow/dirt). | Terrain vertices, normal vectors, slope thresholds | Visually distinct terrain texture/color gradient | Reverts to uniform base color on shader compile error | ORIGINAL_REQUEST.md § R3 |
| 5 | R3 Frontend: Zones | Footprint Visualizer | Renders color-coded 2D/3D polygon line loops and semi-transparent circular/spline zone overlays elevated slightly above terrain. | Zone list: `center`, `radius`, `faction`, `destruction` | Visual boundary cylinders, wireframe rings, and HUD label badges | Omits malformed zone coordinates gracefully | ORIGINAL_REQUEST.md § R3 |
| 6 | R3 Frontend: Buildings | Building Bounding Box & Proxy Visualizer | Places 3D bounding boxes (semi-transparent colored wireframes/boxes or low-poly proxies) at specified `[x,y,z]` positions and rotations. | Building list: `prefab_name`, `position`, `rotation`, `bbox`, `faction`, `destruction` | 3D visual boxes in scene with hover/selection bounding box highlighting | Falls back to default 1x1x1 cube if bbox missing | ORIGINAL_REQUEST.md § R3 |
| 7 | R3 Frontend: Roads | Road Spline Ribbon / Tube Visualizer | Connects zone waypoints using `CatmullRomCurve3` splines and generates flat quad ribbon strips or `TubeGeometry` with width matching manifest. | Road waypoints `[[x, y, z], ...]`, road width, surface type | Continuous asphalt/dirt ribbon mesh floating 0.1m above terrain to avoid z-fighting | Skips road segments with fewer than 2 waypoints | ORIGINAL_REQUEST.md § R3 |
| 8 | R3 Frontend: UI/HUD | Collapsible Responsive HUD Panels | Modern HUD with glassmorphism, container queries, `scrollbar-gutter: stable`, and `overscroll-behavior: contain` per modern-web-guidance. | User viewport, CSS variables, toggle buttons | Accessible sliding/docked side panels (Terrain, Zones, Catalog, Export) | Degrades to stacked responsive layout on small screens | modern-web-guidance & ORIGINAL_REQUEST.md |
| 9 | R3 Frontend: UI/HUD | Terrain Configuration Panel | Form controls for seed, resolution, Perlin scale, octaves, persistence, lacunarity, domain warp strength/octaves, hydraulic erosion iterations. | Input range sliders, numeric inputs, preset buttons | Reactive parameter payload ready for backend generation | Disables generation button while generation in progress | ORIGINAL_REQUEST.md § R3 |
| 10 | R3 Frontend: UI/HUD | Zone Configuration Panel | Controls for zone count (2-10), min distance, global/per-zone faction assignments (`A`/`B`/`C`), destruction levels (`01`-`04`), and density sliders. | Sliders, select dropdowns, per-zone override list | Updated zone generation request payload | Clamps zone count and min distance to terrain bounds | ORIGINAL_REQUEST.md § R3 |
| 11 | R3 Frontend: UI/HUD | Asset Catalog Browser | Searchable, filterable catalog explorer with multi-angle render previews (front, side, top), category filter, tag filter, and bbox dimensions. | Cached `catalog.json` or `/api/catalog` response | Interactive grid cards with thumbnails, tags, and dimension chips | Displays placeholder thumbnail if render missing | ORIGINAL_REQUEST.md § R3 |
| 12 | R3 Frontend: Sync | Export & Sync Controller | Action buttons to trigger live generation (`POST /api/generate`), fetch latest manifest (`GET /api/manifest`), and download `world_manifest.json`. | Backend URL, user trigger clicks | File download trigger, scene reload, manifest metadata summary | Displays error toast with retry button on network failure | ORIGINAL_REQUEST.md § R3 |
| 13 | R4 Unity: Importer | Unity Editor Window (`WorldManifestImporterWindow`) | Custom `EditorWindow` accessible via `[MenuItem("WorldGen/Import Manifest...")]` providing manifest path selector, prefab root path, and one-click import. | File path to `world_manifest.json`, Unity asset paths | Editor GUI window with progress bar and execution triggers | Logs `EditorUtility.DisplayDialog` on missing file | ORIGINAL_REQUEST.md § R4 |
| 14 | R4 Unity: Terrain | Unity TerrainData Instantiation | Constructs `TerrainData`, configures `heightmapResolution` and `size`, transforms normalized 2D height array, and executes `TerrainData.SetHeights`. | `TerrainManifest` object, float[,] height array `[0.0, 1.0]` | Active `Terrain` GameObject with `TerrainCollider` and assigned `TerrainData` | Throws descriptive ArgumentException if resolution is not power of 2 + 1 | ORIGINAL_REQUEST.md § R4 |
| 15 | R4 Unity: Spawner | Prefab Spawner with PrefabUtility | Resolves prefab asset paths from `catalog.json` / Assets folder, instantiates via `PrefabUtility.InstantiatePrefab`, sets local/world transform. | Prefab asset reference, position `Vector3`, rotation `Quaternion`, scale `Vector3` | Instantiated prefab GameObject linked to project asset | Falls back to `GameObject.CreatePrimitive` if prefab asset not found | ORIGINAL_REQUEST.md § R4 |
| 16 | R4 Unity: Hierarchy | Hierarchical Scene Organization | Groups all imported objects under `[WorldGen_Output]`, with sub-parents `Terrain`, `Roads`, and `Zones/Zone_{id}_Faction{A/B/C}_Destruction{01-04}`. | Zone IDs, faction strings, destruction strings | Clean, organized scene hierarchy with Undo support (`Undo.RegisterCreatedObjectUndo`) | Creates default root if naming collision occurs | ORIGINAL_REQUEST.md § R4 |
| 17 | R4 Unity: Materials | Faction & Destruction Material Swap | Automatically remaps `sharedMaterials` on `MeshRenderer` / `SkinnedMeshRenderer` to `PolygonMilitary_Mat_{01-04}_{A-C}.mat` or updates `_MainTex`/`_BumpMap`. | Zone faction (`A`/`B`/`C`), destruction (`01`/`02`/`03`/`04`), renderer components | Updated material assignments matching zone theme and damage state | Preserves special materials (e.g. Glass, Vehicles, Decals) intact | ORIGINAL_REQUEST.md § R4 & Asset Inspection |
| 18 | R4 Unity: Roads | Unity Road Ribbon Mesh Generator | Generates procedural spline mesh GameObjects with UVs and assigns `Road_Texture` material along manifest waypoints. | Road waypoints `Vector3[]`, width, surface type | Road mesh GameObject parented under `Roads` with MeshFilter and MeshRenderer | Clamps waypoint count >= 2 and applies terrain conform | ORIGINAL_REQUEST.md § R4 |
| 19 | Verification | Pytest Manifest Schema Validation | Automated test suite `test_manifest_schema.py` validating compliance of `world_manifest.json` against strict Pydantic/JSONSchema models. | Generated `world_manifest.json` payloads | Pass/Fail assertion reports for types, bounds, and required keys | Fails test with detailed validation error message | ORIGINAL_REQUEST.md § Acceptance Criteria |
| 20 | Verification | Pytest Procedural Generator Suite | Automated test suite `test_generator.py` testing determinism, Poisson-disc spacing, non-overlapping bboxes, slope-constrained roads, and API endpoints. | Test seeds, generation configurations | Pass/Fail assertion reports for geometric and algorithmic constraints | Fails test on boundary violations or NaN elevations | ORIGINAL_REQUEST.md § Acceptance Criteria |
| 21 | Verification | Catalog JSON Validator | Standalone CLI script `validate_catalog.py` verifying `catalog.json` has valid float bboxes, string array tags, and valid placement roles. | `catalog.json` file | Exit code 0 on success, exit code 1 with line-by-line violation report | Prints exact offending item name and invalid key | ORIGINAL_REQUEST.md § Acceptance Criteria |
| 22 | Verification | Frontend & Unity Review Rubrics | Formal Agent-as-Judge review rubrics with grading checklists for Vite/Three.js rendering fidelity and Unity C# importer correctness. | Source code, build outputs, scene snapshots, importer script | Quantitative and qualitative scorecards with pass/fail criteria | Flags anti-patterns (e.g. `Object.Instantiate` in editor) | ORIGINAL_REQUEST.md § Acceptance Criteria |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Three.js Heightmap Mesh | Flat or all-zero heightmap array | Renders a completely flat plane at elevation Y=0 without shader errors or NaN normals. |
| 2 | Three.js Heightmap Mesh | Heightmap resolution mismatch (e.g. 513x513 array for 256x256 PlaneGeometry) | Geometry dynamically reallocates vertex buffers to match the exact dimensions of the received heightmap array. |
| 3 | Three.js Building Placement | Building position outside terrain bounding box | Clamps or flags building with a visual alert boundary; does not crash the WebGL scene. |
| 4 | Three.js Road Spline | Road with 2 identical coincident waypoints | Filters out zero-distance duplicate points prior to constructing `CatmullRomCurve3` to avoid tangent division by zero. |
| 5 | Three.js Asset Browser | Catalog item missing multi-angle render images | Renders SVG fallback icon / 3D wireframe preview placeholder in the catalog card. |
| 6 | Three.js UI Panels | Rapid consecutive clicks on "Generate" button | Debounces click handler and disables trigger button while an async generation request is in-flight. |
| 7 | Unity Terrain Importer | Height values outside [0.0, 1.0] normalized range | Normalizes input heights using `(h - min_h) / (max_h - min_h)` and sets `terrainData.size.y = max_h - min_h`. |
| 8 | Unity Terrain Importer | Terrain resolution is not $(2^n + 1)$ (e.g. 256 or 500) | Automatically adjusts `heightmapResolution` to nearest valid Unity size (e.g. 257 or 513) via bilinear resampling. |
| 9 | Unity Prefab Spawner | Prefab asset path missing in project | Logs warning `[WorldGen] Prefab not found: {prefab_name}`, creates fallback proxy Cube with matching bbox size. |
| 10 | Unity Prefab Spawner | Multiple nested MeshRenderers in compound prefab | Recursively traverses all child `MeshRenderer` and `SkinnedMeshRenderer` components to swap materials uniformly. |
| 11 | Unity Material Swapper | Prefab uses non-swappable materials (e.g. `PolygonMilitary_Glass_01` or `Decals`) | Checks material name against `PolygonMilitary_Mat_` base pattern; leaves glass, decals, and particle materials unmodified. |
| 12 | Catalog Validator | Bounding box coordinates contain `null`, `NaN`, `Infinity`, or string | `validate_catalog.py` catches type mismatch, reports item name, and returns exit code 1. |
| 13 | Manifest Schema Validator | Zone with zero buildings or roads connecting non-existent zone IDs | Schema validator detects invalid foreign key references and raises schema validation error. |
| 14 | Backend API Connection | FastAPI server offline when Frontend loads | Frontend gracefully loads offline cached `sample_world_manifest.json` and displays status badge: "Offline Mode (Cached)". |

---

## 4. Architectural Specification: R3 Interactive 3D Frontend

### 4.1 Technology Stack & Directory Structure
- **Build Tool**: Vite 6+ (with Vanilla TypeScript or React 18+ / React Three Fiber / Pure Three.js).
- **3D Engine**: Three.js (r160+) with `OrbitControls`, `GLTFLoader`, `FontLoader`.
- **CSS / Styling**: Modern Vanilla CSS or Tailwind CSS following `modern-web-guidance`:
  - Container queries (`container-type: inline-size`) for modular HUD cards.
  - `scrollbar-gutter: stable` and `overscroll-behavior: contain`.
  - CSS Custom Properties for theme tokens (faction colors, destruction colors, elevation color stops).
  - Native `<dialog>` / `popover` for modals and tooltips.

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── public/
│   ├── favicon.svg
│   └── sample_world_manifest.json
└── src/
    ├── main.ts
    ├── style.css
    ├── api/
    │   ├── client.ts              # Fetch wrappers for /api/generate, /api/manifest, /api/catalog
    │   └── types.ts               # TypeScript interfaces for Manifest & Catalog
    ├── scene/
    │   ├── WorldScene.ts          # Core Three.js Scene, Renderer, Camera, Lights, OrbitControls
    │   ├── TerrainMesh.ts         # Procedural heightmap mesh with vertex displacement & shader
    │   ├── ZoneOverlay.ts         # Colored footprint rings, boundary decals, faction markers
    │   ├── BuildingVisualizer.ts  # Bounding box wireframes / InstancedMesh proxies
    │   └── RoadVisualizer.ts      # CatmullRomCurve3 spline ribbons / tube geometry
    └── ui/
        ├── HUD.ts                 # Main HUD layout controller
        ├── TerrainConfigPanel.ts  # Terrain generator parameter sliders & triggers
        ├── ZoneConfigPanel.ts     # Zone count, faction, destruction, density controls
        ├── CatalogBrowser.ts      # Multi-angle render previews, tag & role search
        └── ExportSyncBar.ts       # Manifest sync, status badge, JSON download button
```

### 4.2 Three.js Scene Architecture

```
                                +------------------------------------------+
                                |               WorldScene                 |
                                |  (PerspectiveCamera + OrbitControls)    |
                                +--------------------+---------------------+
                                                     |
             +-----------------------+---------------+-----------------------+-----------------------+
             |                       |                                       |                       |
+------------v-----------+ +---------v-----------+               +-----------v-----------+ +---------v-----------+
|      TerrainMesh       | |     ZoneOverlays    |               |  BuildingVisualizer   | |   RoadVisualizer      |
|  - PlaneGeometry (NxN) | |  - LineLoop Ring    |               |  - BoxHelper / Cubes  | |  - CatmullRomCurve3 |
|  - Vertex Displacement | |  - Faction Decal    |               |  - Bounding Box BBox  | |  - Ribbon Quad Strip|
|  - Slope-aware Shader  | |  - Destruction Label|               |  - Hover Tooltip      | |  - Terrain Snapped  |
+------------------------+ +---------------------+               +-----------------------+ +---------------------+
```

#### 4.2.1 Camera & Lighting Setup
1. **Camera**:
   - `PerspectiveCamera(fov: 55, aspect: window.innerWidth / window.innerHeight, near: 0.5, far: 5000)`.
   - Initial position: `[width * 0.7, heightScale * 1.5, length * 0.7]`. Target: `[width / 2, 0, length / 2]`.
2. **Controls**:
   - `OrbitControls` with `enableDamping = true`, `dampingFactor = 0.05`, `maxPolarAngle = Math.PI / 2.05` (prevents camera clipping below ground plane), `minDistance = 10`, `maxDistance = 3000`.
3. **Lighting**:
   - **Directional Light (Sun)**: `DirectionalLight(0xfffaed, 2.2)`, position `[width * 0.5, heightScale * 3.0, length * 0.8]`.
     - `castShadow = true`, `shadow.mapSize.width = 2048`, `shadow.mapSize.height = 2048`.
     - `shadow.camera.left = -width / 2`, `shadow.camera.right = width / 2`, `shadow.camera.top = length / 2`, `shadow.camera.bottom = -length / 2`.
   - **Hemisphere Light**: `HemisphereLight(0x78a0dc, 0x3d352b, 0.8)` for sky-ground ambient contrast.
   - **Tone Mapping**: `renderer.toneMapping = THREE.ACESFilmicToneMapping`, `renderer.toneMappingExposure = 1.1`.

#### 4.2.2 Terrain Mesh & Elevation Displacement Formulation
- **Geometry**: `PlaneGeometry(width, length, resX - 1, resY - 1)`.
- **Coordinate Conversion**:
  - Three.js PlaneGeometry defaults to XY plane with center at `(0,0,0)`.
  - Rotate geometry: `planeGeo.rotateX(-Math.PI / 2)`.
  - Translate to positive quadrant: `planeGeo.translate(width / 2, 0, length / 2)`.
- **Vertex Height Injection**:
  ```typescript
  const positions = planeGeo.attributes.position.array as Float32Array;
  // PlaneGeometry vertices in XZ plane with resolution resX x resY
  for (let i = 0; i < positions.length / 3; i++) {
    const xIdx = i % resX;
    const zIdx = Math.floor(i / resX);
    // Normalized or world height lookup from heightmap[zIdx][xIdx]
    const elevation = heightmap2D[zIdx][xIdx];
    positions[i * 3 + 1] = elevation; // Update Y coordinate
  }
  planeGeo.attributes.position.needsUpdate = true;
  planeGeo.computeVertexNormals();
  ```
- **Shader / Material**:
  - Slope-aware vertex/fragment shader blending based on normal $N_y = \vec{n} \cdot (0, 1, 0)$:
    - Flat ground ($N_y > 0.85$): Grass / Field color (`#4a7c59`).
    - Moderate slope ($0.65 < N_y \le 0.85$): Dirt / Scree (`#7d6b53`).
    - Steep cliff ($N_y \le 0.65$): Rock / Slate (`#404347`).
    - Lowland / Water line ($Y < \text{seaLevel}$): Sand / Wetland (`#c2b280`).

#### 4.2.3 Zone Footprints
- For each zone in `manifest.zones`:
  - **Boundary Ring**: Line loop sampling $K=64$ points on circle $(x_c + r \cos \theta, z_c + r \sin \theta)$, sampling terrain height $Y(\theta)$ at each point plus $+0.2\text{m}$ offset.
  - **Color Coding by Faction**:
    - Faction A: Military Blue / Olive Camo (`#2563eb` / `#16a34a`)
    - Faction B: Desert Tan / Crimson (`#d97706` / `#dc2626`)
    - Faction C: Urban Slate / Hazard Yellow (`#64748b` / `#eab308`)
  - **Destruction Level Indicator**:
    - Ring line style or pulsing badge: `01` (Solid bright), `02` (Dotted), `03` (Dashed), `04` (Red hazard pulse).

#### 4.2.4 Building Bounding Box & Proxy Visualizer
- For each building in `manifest.buildings`:
  - **Position**: `Vector3(building.position[0], building.position[1], building.position[2])`.
  - **Rotation**: `Quaternion(building.rotation[0], building.rotation[1], building.rotation[2], building.rotation[3])` or Euler yaw.
  - **Dimensions**: `size = building.bbox.size` ($w, h, d$).
  - **Mesh Representation**:
    - Semi-transparent colored box (`BoxGeometry(w, h, d)`) with `MeshStandardMaterial(transparent: true, opacity: 0.65)`.
    - Distinct `LineSegments(EdgesGeometry(boxGeo))` for crisp military tactical CAD appearance.
    - Color-coded to zone faction and destruction state.
  - **Raycasting & Interaction**:
    - Hovering over building displays high-precision floating HUD badge: Prefab name, Role, Bbox dimensions, Faction, Destruction level.

#### 4.2.5 Road Spline Ribbon Visualizer
- For each road segment in `manifest.roads`:
  - Waypoints: $P_0, P_1, \dots, P_m \in \mathbb{R}^3$.
  - Interpolate smooth path with `THREE.CatmullRomCurve3(points, false, 'centripetal')`.
  - Subdivide curve into $N = 100$ equidistant samples $s_k$.
  - Construct dynamic quad strip mesh:
    - At each point $s_k$, compute tangent $\vec{t}_k$ and horizontal normal $\vec{n}_k = \vec{t}_k \times (0, 1, 0)$.
    - Left vertex: $L_k = s_k - \vec{n}_k \cdot \frac{\text{width}}{2} + (0, 0.15, 0)$.
    - Right vertex: $R_k = s_k + \vec{n}_k \cdot \frac{\text{width}}{2} + (0, 0.15, 0)$.
    - UVs: $U = 0$ at $L_k$, $U = 1$ at $R_k$; $V = \text{distance} / \text{width}$.
  - Material: Dark asphalt / dirt road material (`#2e3033`) with subtle dashed center line.

### 4.3 UI / Layout Architecture (Modern Web Guidance)
Per `modern-web-guidance`:
1. **Container Queries**: Each panel component is defined with `container-type: inline-size` so slider widths, grid columns, and typography scale smoothly (`clamp(0.85rem, 2cqi, 1.1rem)`).
2. **Layout Primitives**:
   - `#app-layout`: `display: grid; grid-template-columns: 340px 1fr 380px; height: 100dvh; overflow: hidden;`
   - Mobile / Tablet breakpoint (`@media (max-width: 1024px)`): Left/Right panels become off-canvas sliding overlays.
3. **Native Overlays**:
   - Use `popover="auto"` or `<dialog>` for the Asset Detail Inspector and Generation Preset Manager.
4. **Scroll & Overflow Safety**:
   - `scrollbar-gutter: stable` on all scrollable side panels to eliminate horizontal layout shifts.
   - `overscroll-behavior: contain` to prevent mouse wheel events from triggering canvas zooming when hovering over panels.
5. **Accessibility (a11y)**:
   - `<label>` linked to all `<input>` elements via `for`/`id`.
   - Synchronized numeric displays for `<input type="range">`.
   - `aria-live="polite"` on Generation Status Badge for live progress announcements.

```
+-----------------------------------------------------------------------------------------------+
| TOP BAR: [Logo: WORLDGEN 3D] | Status: [Idle / Generating / Synced] | [Presets] | [Quick Export]|
+----------------------+-------------------------------------------------+----------------------+
| LEFT PANEL           | CENTER VIEWPORT (THREE.JS CANVAS)               | RIGHT PANEL          |
| [Terrain Config]     |                                                 | [Asset Catalog]      |
| - Seed: [1337      ] |  [OrbitControls 3D Viewport]                    | - Search: [barracks] |
| - Res:  [512       ] |                                                 | - Filter: [Buildings]|
| - Perlin Scale: 0.05 |    [3D Heightmap Terrain]                       | +------------------+ |
| - Octaves: 6         |    [Zone Footprints A/B/C]                      | | [Thumb] Barracks | |
| - Domain Warp: 1.4   |    [Building Bounding Boxes]                    | | 12.4m x 6.2m x 4m| |
| - Erosion Iter: 25k  |    [Road Ribbon Splines]                        | | Tags: military...| |
| [Zone Config]        |                                                 | +------------------+ |
| - Zone Count: 5      |                                                 | | [Thumb] Hangar   | |
| - Min Dist: 80m      |  HUD Overlay:                                   | | 24.0m x 18m x 9m | |
| - Factions: [A, B, C]|  [Compass Gizmo] [FPS: 60] [PolyCount: 124,512] | +------------------+ |
| - Damage: [01,02,03] |                                                 | [Export & Sync]      |
| [GENERATE WORLD]     |                                                 | - Fetch /manifest    |
|                      |                                                 | - Download JSON      |
+----------------------+-------------------------------------------------+----------------------+
| BOTTOM STATUS BAR: Seed: 1337 | 5 Zones | 64 Buildings | 4 Road Links | Status: Complete      |
+-----------------------------------------------------------------------------------------------+
```

---

## 5. Architectural Specification: R4 Unity Importer Package (C#)

### 5.1 Package Structure & File Layout
```
unity_package/
├── package.json                   # Unity UPM package descriptor
├── Editor/
│   ├── WorldManifestImporterWindow.cs   # Custom EditorWindow UI & Menu Item
│   ├── WorldManifestImporter.cs         # Core importer orchestrator
│   ├── TerrainGenerator.cs              # Unity TerrainData & SetHeights builder
│   ├── PrefabSpawner.cs                 # PrefabUtility instantiation & hierarchy builder
│   ├── MaterialSwapper.cs               # Faction (A/B/C) & Destruction (01-04) material swapper
│   └── RoadMeshBuilder.cs               # Spline ribbon mesh generator for Unity
└── Runtime/
    └── WorldManifestData.cs             # C# Serializable data models for JSON parsing
```

### 5.2 Serialized Manifest Data Models (`WorldManifestData.cs`)
```csharp
using System;
using System.Collections.Generic;
using UnityEngine;

namespace WorldGen.Importer
{
    [Serializable]
    public class WorldManifest
    {
        public ManifestMetadata metadata;
        public TerrainDataManifest terrain;
        public List<ZoneDataManifest> zones = new List<ZoneDataManifest>();
        public List<BuildingDataManifest> buildings = new List<BuildingDataManifest>();
        public List<RoadDataManifest> roads = new List<RoadDataManifest>();
    }

    [Serializable]
    public class ManifestMetadata
    {
        public int seed;
        public string generator_version;
        public string timestamp;
        public float[] bounds; // [minX, minY, minZ, maxX, maxY, maxZ]
    }

    [Serializable]
    public class TerrainDataManifest
    {
        public int resolution;
        public float width;
        public float length;
        public float height_scale;
        public float min_height;
        public float max_height;
        // heightmap can be serialized as flat 1D array or 2D array
        public float[] heights; // length == resolution * resolution
    }

    [Serializable]
    public class ZoneDataManifest
    {
        public string id;
        public string name;
        public float[] center; // [x, y, z]
        public float radius;
        public string faction; // "A", "B", "C"
        public string destruction; // "01", "02", "03", "04"
        public float building_density;
        public List<string> building_ids = new List<string>();
    }

    [Serializable]
    public class BuildingDataManifest
    {
        public string id;
        public string zone_id;
        public string prefab_name; // e.g., "SM_Bld_Barracks_01"
        public float[] position; // [x, y, z]
        public float[] rotation; // [x, y, z, w] quaternion or [pitch, yaw, roll]
        public float[] scale;    // [sx, sy, sz]
        public BoundingBoxManifest bbox;
        public string faction;
        public string destruction;
    }

    [Serializable]
    public class BoundingBoxManifest
    {
        public float[] min;
        public float[] max;
        public float[] size;
    }

    [Serializable]
    public class RoadDataManifest
    {
        public string id;
        public string source_zone;
        public string target_zone;
        public float width;
        public string surface_type;
        public List<float[]> waypoints = new List<float[]>(); // [[x,y,z], ...]
    }
}
```

### 5.3 Unity Terrain Instantiation Pipeline (`TerrainGenerator.cs`)
1. **Resolution & Size Alignment**:
   - Unity requires heightmap resolution to be $2^n + 1$ (e.g., 129, 257, 513, 1025).
   - If manifest resolution $R$ is power of 2 (e.g. 512), importer creates `TerrainData` with `heightmapResolution = R + 1` (513) and bilinearly resamples heights.
   - `terrainData.size = new Vector3(manifest.terrain.width, manifest.terrain.height_scale, manifest.terrain.length)`.
2. **Height Array Conversion**:
   - Unity `TerrainData.SetHeights(0, 0, heights2D)` expects a 2D float array `float[z, x]` with values normalized strictly in $[0.0, 1.0]$.
   - Conversion logic:
     ```csharp
     int res = terrainData.heightmapResolution;
     float[,] heights = new float[res, res];
     float hScale = manifest.terrain.height_scale;

     for (int z = 0; z < res; z++)
     {
         for (int x = 0; x < res; x++)
         {
             // Sample from manifest heightmap (handling 1D flat or 2D array)
             float rawH = SampleManifestHeight(manifest, x, z, res);
             // Normalize to [0.0, 1.0]
             heights[z, x] = Mathf.Clamp01(rawH / hScale);
         }
     }
     terrainData.SetHeights(0, 0, heights);
     ```
3. **Terrain GameObject Creation**:
   - `GameObject terrainGO = Terrain.CreateTerrainGameObject(terrainData);`
   - Position at `Vector3.zero`.
   - Assign layer and parent under `[WorldGen_Output] -> Terrain`.

### 5.4 Prefab Instantiation & Hierarchy Pipeline (`PrefabSpawner.cs`)
1. **Asset Search / Indexing**:
   - Importer indexes all prefabs in `Assets/PolygonMilitary/Prefabs` (or custom search path) using `AssetDatabase.FindAssets("t:Prefab", searchFolders)`.
   - Builds lookup dictionary: `Dictionary<string, string> prefabNameToPath`.
2. **Editor-Compliant Spawning**:
   - For each building in `manifest.buildings`:
     ```csharp
     string prefabPath = LookupPrefabPath(building.prefab_name);
     GameObject prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);

     GameObject instance = null;
     if (prefabAsset != null)
     {
         // CRITICAL: Preserve prefab linkage in Unity Editor
         instance = (GameObject)PrefabUtility.InstantiatePrefab(prefabAsset, zoneParentTransform);
     }
     else
     {
         // Fallback to primitive cube with matching bounding box
         instance = GameObject.CreatePrimitive(PrimitiveType.Cube);
         instance.name = $"{building.prefab_name}_MissingAssetProxy";
         instance.transform.SetParent(zoneParentTransform);
     }

     Vector3 pos = new Vector3(building.position[0], building.position[1], building.position[2]);
     Quaternion rot = building.rotation.Length == 4 
         ? new Quaternion(building.rotation[0], building.rotation[1], building.rotation[2], building.rotation[3])
         : Quaternion.Euler(building.rotation[0], building.rotation[1], building.rotation[2]);
     Vector3 scale = building.scale != null && building.scale.Length == 3
         ? new Vector3(building.scale[0], building.scale[1], building.scale[2])
         : Vector3.one;

     instance.transform.position = pos;
     instance.transform.rotation = rot;
     instance.transform.localScale = scale;
     instance.name = $"{building.prefab_name}_{building.id}";

     Undo.RegisterCreatedObjectUndo(instance, "Import WorldGen Buildings");
     ```
3. **Hierarchy Structure**:
   ```
   [WorldGen_Output]
   ├── Terrain (Terrain Component + TerrainCollider)
   ├── Roads
   │   ├── Road_0_to_1 (MeshFilter + MeshRenderer)
   │   └── Road_1_to_2 (MeshFilter + MeshRenderer)
   └── Zones
       ├── Zone_0_FactionA_Destruction01
       │   ├── SM_Bld_Barracks_01_bld_0
       │   └── SM_Bld_Watchtower_01_bld_1
       ├── Zone_1_FactionB_Destruction03
       │   ├── SM_Bld_Hangar_01_bld_2
       │   └── SM_Prop_Barricade_01_bld_3
       └── Zone_2_FactionC_Destruction04
           └── SM_Bld_CommandCenter_01_bld_4
   ```

### 5.5 Material & Texture Swapping Pipeline (`MaterialSwapper.cs`)
Authoritative discovery from Synty PolygonMilitary package assets:
- **Material Naming Convention**: `PolygonMilitary_Mat_{destruction}_{faction}.mat`
  - Destruction values: `01` (Pristine), `02` (Light Damage), `03` (Heavy Damage), `04` (Ruined/Scorched)
  - Faction values: `A` (Woodland/Blue), `B` (Desert/Tan/Red), `C` (Urban/Grey/Yellow)
- **Texture Naming Convention**:
  - Albedo (`_MainTex`): `PolygonMilitary_Texture_{destruction}_{faction}.png`
  - Normal Map (`_BumpMap`): `PolygonMilitary_Texture_01_A_Normals.png`
- **Swapping Algorithm**:
  ```csharp
  public static void ApplyZoneMaterialTheme(GameObject buildingInstance, string faction, string destruction)
  {
      string targetMatName = $"PolygonMilitary_Mat_{destruction}_{faction}";
      Material targetMat = FindMaterialAsset(targetMatName);

      Renderer[] renderers = buildingInstance.GetComponentsInChildren<Renderer>(true);
      foreach (Renderer rend in renderers)
      {
          Material[] sharedMats = rend.sharedMaterials;
          bool changed = false;

          for (int i = 0; i < sharedMats.Length; i++)
          {
              Material mat = sharedMats[i];
              if (mat == null) continue;

              // Check if material is a swappable base PolygonMilitary material
              if (mat.name.StartsWith("PolygonMilitary_Mat_0") || mat.name.StartsWith("PolygonMilitary_Mat_Gold"))
              {
                  if (targetMat != null)
                  {
                      sharedMats[i] = targetMat;
                      changed = true;
                  }
                  else
                  {
                      // Fallback: Texture override on existing material
                      Texture2D mainTex = FindTexture($"PolygonMilitary_Texture_{destruction}_{faction}");
                      Texture2D bumpTex = FindTexture("PolygonMilitary_Texture_01_A_Normals");
                      if (mainTex != null) mat.SetTexture("_MainTex", mainTex);
                      if (bumpTex != null) mat.SetTexture("_BumpMap", bumpTex);
                  }
              }
              // Skip Glass, Decals, Vehicle specials
          }

          if (changed)
          {
              rend.sharedMaterials = sharedMats;
              EditorUtility.SetDirty(rend);
          }
      }
  }
  ```

---

## 6. Acceptance Criteria & E2E Testing Suite Specification

### 6.1 Pytest Manifest Schema Validation Suite (`tests/test_manifest_schema.py`)
Validates every field, nested schema, coordinate range, and relationship constraint of `world_manifest.json`:
- **Test Cases**:
  1. `test_manifest_metadata_validity`: Verifies presence and valid types for `seed` (int), `generator_version` (str), `timestamp` (ISO8601), and `bounds` (6 floats with min < max).
  2. `test_terrain_data_schema`: Verifies `resolution` is positive integer, `width > 0`, `length > 0`, `height_scale > 0`, `min_height <= max_height`, and `heights` length equals `resolution * resolution` (or 2D shape `(resolution, resolution)`).
  3. `test_zone_schema_and_factions`: Verifies each zone has valid `id`, `name`, `center` (3 floats within bounds), `radius > 0`, `faction` in `['A', 'B', 'C']`, `destruction` in `['01', '02', '03', '04']`, and `building_density` in `[0.0, 1.0]`.
  4. `test_building_schema_and_transforms`: Verifies `position` (3 floats within terrain bounds), `rotation` (quaternion with magnitude $\approx 1.0$ or 3 euler angles), `bbox` contains valid `min`, `max`, `size` with `size >= 0`, `faction` and `destruction` match zone.
  5. `test_road_schema_and_connectivity`: Verifies road waypoints are non-empty lists of 3D points connecting valid zone centers, width > 0.
  6. `test_foreign_key_integrity`: Ensures all `building.zone_id` references exist in `zones` array and all `road.source_zone` / `road.target_zone` exist in `zones` array.

### 6.2 Pytest Generator Suite (`tests/test_generator.py`)
Tests algorithmic correctness and determinism:
- **Test Cases**:
  1. `test_generator_determinism`: Running generator with seed `42` twice produces bitwise identical `world_manifest.json`.
  2. `test_poisson_disc_zone_spacing`: Asserts Euclidean distance between any two zone centers is $\ge \text{min\_distance}$.
  3. `test_non_overlapping_buildings`: Computes 2D axis-aligned/oriented bounding boxes for all buildings in each zone; asserts no intersection overlap between building footprints.
  4. `test_terrain_flattening_under_zones`: Asserts height variance $\sigma^2_h$ inside flattened zone radii is significantly lower than overall terrain variance.
  5. `test_slope_aware_road_routing`: Asserts max slope $\left|\frac{\Delta Y}{\Delta XZ}\right|$ between consecutive road waypoints is below maximum traversable slope threshold (e.g., $< 0.45$).
  6. `test_fastapi_endpoints`:
     - `GET /api/health` -> returns `{"status": "ok"}` (200).
     - `POST /api/generate` -> accepts config JSON, returns 200 with new manifest.
     - `GET /api/manifest` -> returns latest `world_manifest.json` (200).
     - `GET /api/catalog` -> returns `catalog.json` (200).
     - `POST /api/export` -> returns downloadable JSON blob or file stream.

### 6.3 Standalone Catalog Validation Script (`scripts/validate_catalog.py`)
- Programmatic CLI script returning exit code `0` on success and `1` on error.
- **Validation Rules**:
  1. `catalog.json` is valid JSON and contains top-level array or dict of items.
  2. For each item:
     - `prefab_name`: Non-empty string.
     - `category`: String in allowed set (`Buildings`, `Environment`, `Props`, `Vehicles`, `Weapons`, `Generic`).
     - `bbox`: Must contain `min` [x,y,z], `max` [x,y,z], `size` [w,h,d]. Every element MUST be a finite float (`isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)`).
     - `size[i] == max[i] - min[i]` (within floating-point tolerance $10^{-3}$).
     - `tags`: List of strings (`isinstance(tags, list)` and all `isinstance(t, str)`).
     - `placement_roles`: List of strings (e.g. `["barracks", "military_base", "shelter"]`).
     - `affinities`: List of strings or dict of numeric affinities.
     - `multi_angle_renders`: Object with keys `front`, `side`, `top` whose string values point to accessible image files or valid data URIs.

### 6.4 Review Rubrics (Agent-as-Judge & Verification Checklists)

#### 6.4.1 Frontend Verification Rubric (R3)
| Metric | Pass Criteria | Severity if Failed |
|---|---|---|
| **Build Cleanliness** | `npm run build` completes with 0 errors and produces optimized bundle in `dist/`. | Blocker |
| **Three.js Scene Graph** | Scene instantiates `PerspectiveCamera`, `OrbitControls`, `DirectionalLight`, and `AmbientLight`/`HemisphereLight`. | Blocker |
| **Terrain Mesh Rendering** | `PlaneGeometry` vertex heights match manifest elevation data; normal calculation produces smooth shading. | Blocker |
| **Zone Footprints** | Visible colored rings/overlays matching Factions A (`#2563eb`), B (`#d97706`), C (`#64748b`). | Major |
| **Building Visuals** | Bounding box wireframes/proxies accurately match coordinates and orientations from manifest. | Major |
| **Road Visuals** | Continuous ribbon/tube meshes connect zones along waypoints without z-fighting. | Major |
| **Modern Web UI Standards** | Panels use Container Queries, `scrollbar-gutter: stable`, accessible form controls, and responsive styling per `modern-web-guidance`. | Major |
| **API Connectivity & Fallback** | Successfully queries `/api/generate` & `/api/manifest`; falls back to cached `sample_world_manifest.json` if offline. | Major |

#### 6.4.2 Unity Importer Verification Rubric (R4)
| Metric | Pass Criteria | Severity if Failed |
|---|---|---|
| **C# Compilation** | Script compiles in Unity Editor without syntax errors, missing namespaces, or obsolete API warnings. | Blocker |
| **Prefab Instantiation** | Uses `PrefabUtility.InstantiatePrefab(prefabAsset, parentTransform)` when executed in Editor mode to preserve asset linkages. | Blocker |
| **Material Swapping Logic** | Automatically maps zone faction (A/B/C) and destruction (01-04) to `PolygonMilitary_Mat_{01-04}_{A-C}.mat` (or swaps `_MainTex` and `_BumpMap`). | Blocker |
| **Terrain Instantiation** | Creates `TerrainData` with correct resolution and size; populates heights via `TerrainData.SetHeights` in normalized `[0.0, 1.0]` range. | Blocker |
| **Scene Organization** | Clean hierarchy rooted at `[WorldGen_Output]` with `Terrain`, `Roads`, and `Zones/Zone_{id}_Faction{A/B/C}_Destruction{01-04}`. | Major |
| **Editor UX & Undo** | Menu item `[MenuItem("WorldGen/Import Manifest...")]` or EditorWindow; registers undo operations via `Undo.RegisterCreatedObjectUndo`. | Major |

---

## 7. Data Contracts & JSON Schemas

### 7.1 `world_manifest.json` Schema Specification
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WorldManifest",
  "type": "object",
  "required": ["metadata", "terrain", "zones", "buildings", "roads"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["seed", "generator_version", "timestamp", "bounds"],
      "properties": {
        "seed": { "type": "integer" },
        "generator_version": { "type": "string" },
        "timestamp": { "type": "string", "format": "date-time" },
        "bounds": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 6,
          "maxItems": 6
        }
      }
    },
    "terrain": {
      "type": "object",
      "required": ["resolution", "width", "length", "height_scale", "min_height", "max_height", "heights"],
      "properties": {
        "resolution": { "type": "integer", "minimum": 64 },
        "width": { "type": "number", "minimum": 1 },
        "length": { "type": "number", "minimum": 1 },
        "height_scale": { "type": "number", "minimum": 1 },
        "min_height": { "type": "number" },
        "max_height": { "type": "number" },
        "heights": {
          "type": "array",
          "items": { "type": "number" }
        }
      }
    },
    "zones": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "center", "radius", "faction", "destruction", "building_density"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "center": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "radius": { "type": "number", "minimum": 1 },
          "faction": { "type": "string", "enum": ["A", "B", "C"] },
          "destruction": { "type": "string", "enum": ["01", "02", "03", "04"] },
          "building_density": { "type": "number", "minimum": 0, "maximum": 1 },
          "building_ids": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "buildings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "zone_id", "prefab_name", "position", "rotation", "bbox", "faction", "destruction"],
        "properties": {
          "id": { "type": "string" },
          "zone_id": { "type": "string" },
          "prefab_name": { "type": "string" },
          "position": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "rotation": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 4
          },
          "scale": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "bbox": {
            "type": "object",
            "required": ["min", "max", "size"],
            "properties": {
              "min": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
              "max": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
              "size": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 }
            }
          },
          "faction": { "type": "string", "enum": ["A", "B", "C"] },
          "destruction": { "type": "string", "enum": ["01", "02", "03", "04"] }
        }
      }
    },
    "roads": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "source_zone", "target_zone", "width", "waypoints"],
        "properties": {
          "id": { "type": "string" },
          "source_zone": { "type": "string" },
          "target_zone": { "type": "string" },
          "width": { "type": "number", "minimum": 0.5 },
          "surface_type": { "type": "string" },
          "waypoints": {
            "type": "array",
            "items": {
              "type": "array",
              "items": { "type": "number" },
              "minItems": 3,
              "maxItems": 3
            }
          }
        }
      }
    }
  }
}
```

### 7.2 `catalog.json` Schema Specification
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AssetCatalog",
  "type": "object",
  "patternProperties": {
    "^[a-zA-Z0-9_]+$": {
      "type": "object",
      "required": ["prefab_name", "category", "bbox", "tags", "placement_roles"],
      "properties": {
        "prefab_name": { "type": "string" },
        "category": { "type": "string" },
        "description": { "type": "string" },
        "bbox": {
          "type": "object",
          "required": ["min", "max", "size"],
          "properties": {
            "min": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
            "max": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
            "size": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 }
          }
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "placement_roles": {
          "type": "array",
          "items": { "type": "string" }
        },
        "affinities": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        },
        "multi_angle_renders": {
          "type": "object",
          "properties": {
            "front": { "type": "string" },
            "side": { "type": "string" },
            "top": { "type": "string" }
          }
        }
      }
    }
  }
}
```

---

## 8. Summary of Implementation Directives
1. **Frontend**: Build using Vite with TypeScript, modular Three.js scene components (`TerrainMesh`, `ZoneOverlay`, `BuildingVisualizer`, `RoadVisualizer`), and modern responsive HUD with container queries and scrollbar-gutter stability.
2. **Unity Importer**: Implement `WorldManifestImporterWindow.cs` and `WorldManifestImporter.cs`, using `TerrainData.SetHeights`, `PrefabUtility.InstantiatePrefab`, and `PolygonMilitary_Mat_{01-04}_{A-C}` material swapping.
3. **E2E Testing**: Deliver pytest validation suite (`test_manifest_schema.py`, `test_generator.py`) and standalone CLI catalog validator (`validate_catalog.py`).
