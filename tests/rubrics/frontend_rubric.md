# Frontend Review Rubric (R3: Interactive 3D Visualizer & Modern Web HUD)

## Objective
This Agent-as-Judge rubric evaluates the implementation quality, architectural soundness, 3D WebGL rendering fidelity, modern web best practice compliance, and API integration for **Requirement R3: Interactive 3D Frontend (Vite + Three.js)**.

---

## 1. Evaluation Dimensions & Checklists

### 1.1 Three.js 3D Scene Architecture & Lighting (Weight: 20%)
- [ ] **Scene & Camera Setup**:
  - Instantiates `THREE.Scene` and `THREE.PerspectiveCamera` with FOV $\approx 50^\circ-60^\circ$ and clipping planes (`near: 0.5`, `far: 5000`).
  - Implements `OrbitControls` with smooth damping enabled (`enableDamping: true`, `dampingFactor: 0.05`).
  - Enforces polar angle constraints (`maxPolarAngle <= Math.PI / 2.05`) to prevent camera clipping below ground level.
- [ ] **Lighting & Shadows**:
  - Primary `DirectionalLight` (sun) positioned high with shadow map configuration (`shadow.mapSize.width >= 2048`, `shadow.mapSize.height >= 2048`).
  - Fill illumination via `HemisphereLight` or `AmbientLight` for balanced sky-ground ambient contrast.
  - Renderer configures `toneMapping = THREE.ACESFilmicToneMapping` or `sRGBEncoding`.

### 1.2 Procedural Terrain Heightmap Mesh & Shader (Weight: 20%)
- [ ] **Vertex Displacement**:
  - `PlaneGeometry` instantiated with resolution matching manifest dimensions ($res \times res$).
  - Rotated to horizontal plane (XZ) and translated to positive coordinate quadrant.
  - Heights injected dynamically into vertex `position.array` ($Y$-coordinate) and `computeVertexNormals()` invoked.
- [ ] **Slope & Height Coloring**:
  - Implements slope-aware shader / vertex coloring based on surface normal angle:
    * Flat ground ($N_y > 0.85$): Grass / Field green
    * Moderate slope ($0.65 < N_y \le 0.85$): Scree / Dirt brown
    * Steep cliff ($N_y \le 0.65$): Slate rock / Cliff grey
    * Waterline / Low elevation: Sand / Shoreline tan

### 1.3 Zones, Buildings & Roads 3D Visuals (Weight: 20%)
- [ ] **Zone Footprints**:
  - Renders 2D/3D polygon line loops elevated $+0.2$m above terrain to avoid z-fighting.
  - Color-coded by military faction:
    * **Faction A**: Military Olive / Blue (`#2563eb` / `#16a34a`)
    * **Faction B**: Desert Tan / Crimson (`#d97706` / `#dc2626`)
    * **Faction C**: Urban Slate / Hazard Yellow (`#64748b` / `#eab308`)
- [ ] **Building Bounding Boxes & Proxies**:
  - Places 3D bounding boxes (`BoxGeometry`) at manifest `position`, `rotation`, and `scale`.
  - Crisp tactical CAD wireframe outlines via `LineSegments(EdgesGeometry(boxGeo))`.
  - Interactive hover raycasting displays HUD tooltip (Prefab name, Role, Bbox dimensions, Faction, Damage).
- [ ] **Road Spline Ribbon Ribbons**:
  - Interpolates waypoints smoothly using `THREE.CatmullRomCurve3(points, false, 'centripetal')`.
  - Constructs flat quad ribbon mesh or `TubeGeometry` with width matching manifest.

### 1.4 Modern Web Layout & Guidance Compliance (Weight: 20%)
*Evaluated against `modern-web-guidance` standards:*
- [ ] **Container Queries**:
  - Modular HUD cards utilize `@container (inline-size >= ...)` and `container-type: inline-size`.
- [ ] **Scroll & Overflow Stability**:
  - `scrollbar-gutter: stable` on all scrollable side panels to eliminate layout shift.
  - `overscroll-behavior: contain` to prevent canvas scroll bleeding when hovering over side panels.
- [ ] **Responsive Docked HUD Panels**:
  - Left Panel: Terrain Configuration (Seed, Resolution, Perlin Scale, Octaves, Warp, Erosion).
  - Left Panel: Zone Configuration (Zone Count, Min Distance, Factions A/B/C, Destruction 01-04, Density).
  - Right Panel: Asset Catalog Browser with multi-angle renders (front, side, top), search, and tags.
- [ ] **Accessibility (a11y)**:
  - Form controls have explicit `<label>` associations. Range sliders provide synchronized numeric output.

### 1.5 API Synchronization & Offline Fallback (Weight: 20%)
- [ ] **Backend Integration**:
  - Action buttons trigger `POST /api/generate` and fetch latest `GET /api/manifest`.
  - Asset catalog fetched via `GET /api/catalog` with live search and filter capabilities.
- [ ] **Offline Fallback**:
  - Gracefully falls back to bundled `public/sample_world_manifest.json` if backend is unreachable, displaying an "Offline Mode (Cached)" status badge.

---

## 2. Quantitative Scoring Matrix

| Score Range | Rating | Acceptance Decision |
|---|---|---|
| **90 – 100** | Exceptional | **PASS (Exceeds Requirements)** |
| **80 – 89** | Proficient | **PASS (Fully Meets Acceptance Criteria)** |
| **70 – 79** | Adequate | **CONDITIONAL PASS (Minor visual polish required)** |
| **< 70** | Deficient | **FAIL (Must resolve blocking issues)** |

---

## 3. Anti-Patterns & Automatic Disqualifications
- ❌ Hardcoded mock values that ignore backend API responses.
- ❌ Missing vertex normal recalculation causing flat/unshaded terrain.
- ❌ Heavy horizontal layout shifts on panel open/scroll (violating `scrollbar-gutter`).
- ❌ Unhandled WebGL errors on zero/flat heightmaps.
