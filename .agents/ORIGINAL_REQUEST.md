# Original User Request

## Initial Request — 2026-09-01T21:52:26+04:00

A web-based 3D world designer (FastAPI/Python + Vite/Three.js) and Unity C# importer that generates procedural battle-royale-style military worlds using Synty PolygonMilitary assets.

Working directory: /Users/jack/worldgen
Integrity mode: benchmark

## Requirements

### R1. Asset Catalog Builder (Python)
Create a catalog build pipeline that programmatically extracts bounding boxes via the Blender CLI (`/Applications/Blender.app/Contents/MacOS/Blender`). 
It must also implement a multi-angle render pipeline (front, side, top) and send these images to a local VLM (`qwen3.8:27b` via Ollama) to generate tags, descriptions, and placement roles for each prefab. The output should be a cached `catalog.json`.

### R2. Terrain and Zone Generator (FastAPI Backend)
Build a FastAPI backend (managed via `uv`) that generates a procedural heightmap (multifractal Perlin, domain warp, Numba hydraulic erosion).
It must place zones (Poisson-disc, organic footprints flattened to the terrain), place buildings within them respecting their bounding boxes, and route slope-aware roads connecting the zones.
The backend must expose endpoints to export this data as a `world_manifest.json`.

### R3. Interactive 3D Frontend (Vite + Three.js)
Create a web interface to view the terrain, zone footprints, and building footprints interactively.
Include side panels for configuring terrain parameters, zone attributes (faction, destruction level, density), and browsing the asset catalog. 
*Important: You must execute the `modern-web-guidance` skill before implementing any UI/layout features to ensure modern web best practices are followed.*

### R4. Unity Importer Package (C#)
Write a Unity Editor script that reads `world_manifest.json` and instantiates the heightmap as a Unity Terrain. 
It must spawn all prefabs (linked correctly) grouped by zone, and automatically swap the materials (`_MainTex` and `_BumpMap`) based on the zone's faction letter (A/B/C) and destruction level number (01-04).

## Acceptance Criteria

### API and Backend Verification
- [ ] Automated programmatic test successfully calls the generation and export endpoints and validates the resulting `world_manifest.json` schema.
- [ ] Catalog JSON validation script confirms that bounding boxes are valid floats and tags/affinities are arrays of strings.

### Frontend and Unity Verification (Agent-as-Judge)
- [ ] Review rubric confirms the frontend successfully communicates with the backend, and uses modern React/Three.js patterns.
- [ ] Review rubric confirms the C# Unity importer uses `PrefabUtility.InstantiatePrefab` and includes the correct material swapping logic for faction/damage.

**Note from user**: Make sure to test that everything works correctly and completely!

## Follow-up — 2026-09-02T07:59:05Z

WorldGen V2: Enhancing the procedural military world generator with dynamic map sizing, interactive zone CRUD and drag-to-recompute, smooth terrain deformation, AI-templated asset allocation, and adaptive terrain tessellation.

Working directory: /Users/jack/worldgen
Integrity mode: benchmark

## Requirements

### R1. Global Map Parameters (Backend & Frontend)
Update the UI and backend API to support configurable map dimensions (width/height in km), granularity (resolution slider), a terrain deformation strength slider, and an edge margin offset parameter. Terrain flattening for zones must use a smooth interpolation (e.g., cubic or cosine falloff) rather than linear to prevent near-vertical cliffs.

### R2. Zone Editing & Interactivity (Frontend)
Implement full CRUD (Add, Remove, Rename) for individual zones in the React side panel. Make zone centers manually draggable in the Three.js 3D viewport. When a zone is dropped, the frontend must trigger a backend recomputation of the terrain, roads, and assets, and smoothly update the viewport.

### R3. Backend Adaptive Tessellation & Road Limits
Implement backend mesh decimation: generate an optimized mesh structure where triangle/quad sizes vary depending on the area (e.g., larger triangles on flat plains, smaller/denser on steep slopes). This optimized mesh must be sent to the frontend and Unity. Additionally, add a configurable `max_road_slope` limit for the A* road routing algorithm to prevent unrealistic vertical roads.

### R4. AI-Driven Asset Allocation
Replace the density dropdown with a continuous density slider. Replace random asset allocation with a system driven by offline JSON layout templates (which you will generate using the Qwen model), ensuring structured, denser, and more realistic environments based on zone type.

### R5. UI Cleanup & Standards
Strip generic or "AI slop" terminology (e.g., "Procedural Military Designer") from the UI, keeping it strictly utilitarian. 
*Important: You must execute the `modern-web-guidance` skill before implementing any frontend changes to ensure modern web standards.*

## Acceptance Criteria

### API and Backend Verification
- [ ] Programmatic tests verify that changing map dimensions returns arrays and mesh indices of the correct corresponding sizes.
- [ ] Automated tests verify that road paths strictly adhere to the `max_road_slope` parameter.

### Frontend and Unity Verification (Agent-as-Judge)
- [ ] Review rubric confirms the frontend successfully allows dragging a zone and visually updates the terrain and footprint without a full page reload.
- [ ] Review rubric confirms the backend decimation produces variable-sized triangles/quads that load correctly in both Three.js and the Unity importer.

## Follow-up — 2026-09-02T18:45:16+04:00

This is a single self-contained fix; keep it small and focused. Fix the four critical bugs reported by the user regarding roads, terrain voids, camera conflicts, and API spam.

Working directory: /Users/jack/worldgen
Integrity mode: benchmark

## Requirements

### R1. Fix A* Road Pathfinding (`roads.py`)
A* is currently aborting due to a low `max_expansions` limit (12,000), resulting in a fallback straight line that slices through mountains and air.
- Increase `max_expansions` to at least `250,000`.
- Update the fallback logic: if A* fails, do NOT draw a 2-point straight line. Instead, draw a straight line but sample the heightmap along it every 5-10 meters so the road follows the terrain instead of floating or slicing through it.
- Use `scipy.spatial.Delaunay` instead of the custom Bowyer-Watson implementation to ensure proper connectivity without crossing edges.

### R2. Fix Terrain Mesh Tears / Voids (`mesh.py` or `terrain.py`)
The adaptive decimation or zone smoothing logic is creating jagged holes and black voids in the terrain mesh. Debug and fix the geometry generation so the mesh remains manifold and watertight, particularly around zone boundaries.

### R3. Fix Drag vs. Orbit Camera Conflict (Frontend)
When dragging zone centers in the 3D viewport, the camera behaves weirdly because `OrbitControls` is active simultaneously. 
Disable `OrbitControls` on the `dragstart` event and re-enable it on `dragend`.

### R4. Fix Backend Online/Offline Toggling (Frontend)
The frontend keeps dropping the backend connection during zone movement because it is likely spamming the API on every frame of the drag event, causing the server to timeout.
Ensure the `POST /api/generate` call is only fired on `dragend` (when the user releases the mouse), not continuously during the drag.

## Acceptance Criteria

### Verification
- [ ] Agent-as-judge rubric confirms that the A* fallback correctly samples the heightmap and `max_expansions` is increased.
- [ ] Agent-as-judge rubric confirms the Three.js frontend disables OrbitControls during drag and only calls the generation API on `dragend`.
- [ ] Automated tests verify the terrain mesh has no degenerate or out-of-bounds indices causing holes.

