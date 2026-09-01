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
