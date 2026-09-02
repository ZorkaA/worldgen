# Frontend Review Rubric (WorldGen V2: Interactive 3D Visualizer & Utilitarian HUD)

## Objective
This Agent-as-Judge rubric evaluates the implementation quality, architectural soundness, 3D WebGL rendering fidelity, interactive zone editing capabilities, modern web best practice compliance, and API integration for **WorldGen V2 Requirements R1, R2, R3, R4, and R5**.

---

## 1. Evaluation Dimensions & Checklists

### 1.1 Zone CRUD & Interactive 3D Drag-and-Drop (Weight: 25%)
- [ ] **Zone CRUD Operations (Side Panel UI)**:
  - **Add Zone**: Button to instantiate a new tactical zone with default parameters (type, faction, density, radius).
  - **Remove Zone**: Ability to delete an existing zone from the list; viewport cleanly removes its footprint, beacon, and associated buildings.
  - **Rename Zone**: Inline or modal text editing of zone display names with immediate state synchronization.
- [ ] **3D Viewport Raycasting Drag Controls**:
  - Interactive 3D draggable beacon / handle located at each zone's center coordinate $(X, Y, Z)$.
  - Raycaster maps pointer movement across the terrain surface, locking $(X, Z)$ coordinates to the cursor during drag operations.
  - Visual drag feedback (e.g. ghost footprint, height snap, elevated beacon cursor).
- [ ] **Live Drop Recomputation (No Page Reload)**:
  - Releasing the dragged zone center immediately triggers a backend recompute request (`POST /api/generate` or `POST /api/recompute`).
  - Viewport scene updates **in place** (updating terrain heightmap/mesh, recalculated roads, and re-allocated building placements) **without a full page reload or WebGL context recreation**.
  - Camera position, orbit target, and UI panel open/close state remain stable during recomputation.

### 1.2 Adaptive Decimated Terrain Mesh & Visuals (Weight: 20%)
- [ ] **Adaptive Mesh Geometry**:
  - Instantiates `THREE.BufferGeometry` using backend decimated mesh buffers:
    * `position` attribute from `terrain.mesh.vertices`
    * `index` attribute from `terrain.mesh.indices`
    * `normal` attribute from `terrain.mesh.normals`
    * `uv` attribute from `terrain.mesh.uvs`
  - Properly handles variable-density triangles (large triangles on flat plains, dense polygons on steep slopes/peaks).
- [ ] **Wireframe & Inspection Mode**:
  - Includes a UI toggle to view the adaptive mesh wireframe (`material.wireframe = true` or overlaid wireframe helper).
  - Visually confirms decimation on flat terrain without geometric cracks or degenerate seams.
- [ ] **Slope & Elevation Coloring**:
  - Shader / vertex coloring smoothly transitions across elevations and surface gradients (waterline tan -> field green -> scree brown -> cliff rock).

### 1.3 Templated Zones, Buildings & Road Splines (Weight: 20%)
- [ ] **Templated Layout Visualization**:
  - Renders building bounding boxes and proxies generated from offline layout templates across all 5 zone types (`military_base`, `airfield`, `outpost`, `radar_station`, `depot`).
  - Continuous density slider ($0.0 \le D \le 1.0$) dynamically modulates visible building density without causing overlapping geometry.
  - Faction color-coding (Faction A: Olive/Blue, Faction B: Desert/Crimson, Faction C: Hazard/Slate).
- [ ] **Road Spline Ribbon Rendering**:
  - Smooth 3D spline interpolation along waypoints (`THREE.CatmullRomCurve3`).
  - Quad ribbon mesh or tube geometry elevated slightly above terrain ($+0.15$m) to prevent z-fighting.
  - Conforms to slope-limited paths around mountains and steep ridges.

### 1.4 Utilitarian UI Cleanup & Standards (Weight: 20%)
*Evaluated against R5 and `modern-web-guidance` standards:*
- [ ] **AI Slop Elimination**:
  - Strips generic marketing buzzwords and "AI slop" copy (e.g. "Next-Gen Procedural Military AI Designer", "Ultimate World Generator").
  - Clean, professional, utilitarian HUD typography (e.g. `TERRAIN PARAMS`, `ZONE EDITOR`, `ASSET CATALOG`, `EXPORT MANIFEST`).
- [ ] **Modern CSS Architecture**:
  - Modular HUD cards utilize Container Queries (`@container (inline-size >= ...)`, `container-type: inline-size`).
  - `scrollbar-gutter: stable` on all scrollable side panels to eliminate layout shift during scrolling.
  - `overscroll-behavior: contain` to prevent canvas scroll bleed.
- [ ] **Accessibility & Synchronization**:
  - Range sliders provide synchronized numeric inputs and explicit `<label>` bindings.
  - Keyboard navigation and ARIA attributes for modal dialogs and dropdowns.

### 1.5 Global Map Parameters & API Synchronization (Weight: 15%)
- [ ] **Configurable Map Dimensions & Granularity**:
  - Sliders for Map Width/Length (km / meters), Grid Resolution ($65 - 1025$), Terrain Deformation Multiplier, and Edge Margin Offset.
  - Changing parameters triggers live preview or explicit generate action.
- [ ] **API Resilience & Error Handling**:
  - Handles network latency with non-blocking loading states (spinner / progress indicator).
  - Graceful error boundary fallback if invalid parameters or network errors occur.

---

## 2. Quantitative Scoring Matrix

| Score Range | Rating | Acceptance Decision |
|---|---|---|
| **90 – 100** | Exceptional | **PASS (Exceeds V2 Requirements)** |
| **80 – 89** | Proficient | **PASS (Fully Meets V2 Acceptance Criteria)** |
| **70 – 79** | Adequate | **CONDITIONAL PASS (Minor visual or drag polish required)** |
| **< 70** | Deficient | **FAIL (Must resolve blocking issues)** |

---

## 3. Anti-Patterns & Automatic Disqualifications
- ❌ Reloading the browser page (`window.location.reload()`) upon dropping a dragged zone.
- ❌ Freezing or crashing the Three.js render loop when ingesting variable-density adaptive meshes.
- ❌ Leaving AI marketing copy / "AI slop" text in the UI headers and labels.
- ❌ Overlapping building wireframes when continuous density slider is set to 1.0.
- ❌ Missing vertex normals or corrupted UV mappings causing inverted lighting on terrain slopes.
