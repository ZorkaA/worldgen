## 2026-09-01T21:53:52Z
You are teamwork_preview_spec_miner (Survey Spec Miner 3: R3 Frontend, R4 Unity Importer & Verification Specs).
Your working directory is: /Users/jack/worldgen/.agents/survey_spec_miner_3

Read the authoritative requirements at: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md

Your mission:
1. Mine and define precise architectural and technical specifications for:
   - R3: Interactive 3D Frontend (Vite + Three.js):
     * Note: Follow modern-web-guidance skill rules for UI/layout.
     * Three.js scene architecture: OrbitControls / Camera, directional sunlight + ambient light, custom heightmap terrain mesh (PlaneGeometry with vertex displacement from heightmap data or Float32Array elevation), wireframe/color-coded zone footprints, building boxes/wireframes/meshes positioned accurately, road line ribbons/tubes.
     * UI / Layout: Modern HUD / Side panels (collapsible, accessible, responsive):
       - Terrain Config Panel: seed, resolution, perlin scale, octaves, domain warp strength, erosion iterations, generate button, live status.
       - Zone Config Panel: number of zones, min distance, faction assignments (A/B/C), destruction levels (01-04), density sliders.
       - Asset Catalog Browser: view cached catalog items, thumbnails/multi-angle renders, tags, roles, bounding box dimensions, search/filter by tag/role.
       - Export & Sync: button to fetch `/manifest`, download `world_manifest.json`, trigger live regenerations.
   - R4: Unity Importer Package (C#):
     * Unity Editor script (e.g. `WorldManifestImporter.cs` inheriting from `EditorWindow` or using `[MenuItem("WorldGen/Import Manifest")]`).
     * Reads `world_manifest.json`.
     * Instantiates Unity Terrain: `TerrainData` with heights array matching the manifest, sets size and resolution.
     * Prefab instantiator: Spawns prefabs using `PrefabUtility.InstantiatePrefab` if in Editor (or `Object.Instantiate`), parenting them under zone GameObjects (e.g. `Zone_0_FactionA_Destruction02`).
     * Material swapping logic: Maps zone faction (A/B/C) and destruction (01-04) to material textures, replacing `_MainTex` and `_BumpMap` (or `_NormalMap`) on the mesh renderers.
   - Acceptance Criteria & E2E Testing Suite:
     * Automated pytest suite for FastAPI endpoints & schema validation (`test_manifest_schema.py`, `test_generator.py`).
     * Automated catalog validation script (`validate_catalog.py`) ensuring valid floats for bboxes and string arrays for tags/affinities.
     * Review rubrics and verification tests for Frontend (Three.js rendering, Vite build, API connectivity) and Unity Importer (C# syntax, `PrefabUtility.InstantiatePrefab` usage, material swap logic).
2. Write a detailed specification and verification report to `/Users/jack/worldgen/.agents/survey_spec_miner_3/spec_report.md` and handoff to `/Users/jack/worldgen/.agents/survey_spec_miner_3/handoff.md`.
3. Send a message to your parent when done.
