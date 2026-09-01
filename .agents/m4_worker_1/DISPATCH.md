## 2026-09-01T18:17:10Z
You are teamwork_preview_worker (Milestone 4: Unity Importer Package).
Your working directory is: /Users/jack/worldgen/.agents/m4_worker_1

Read the authoritative requirements at: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md
Also read:
- /Users/jack/worldgen/PROJECT.md
- /Users/jack/worldgen/.agents/survey_spec_miner_3/spec_report.md
- /Users/jack/worldgen/tests/rubrics/unity_rubric.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your write ownership:
You exclusively own `/Users/jack/worldgen/unity/`.

Your mission:
1. Implement Unity C# Editor Importer package in `/Users/jack/worldgen/unity/Assets/Editor/WorldManifestImporter.cs` (and accompanying documentation/sample files):
   - Implements an `EditorWindow` accessible via `[MenuItem("WorldGen/Import World Manifest")]` with a user-friendly GUI (file path picker, load manifest button, import options, clear generated world button, progress bar).
   - Reads and parses `world_manifest.json` using robust JSON deserialization (handling metadata, terrain, zones, buildings, roads).
   - Unity Terrain Instantiation:
     * Creates or updates a `Terrain` GameObject with `TerrainData`.
     * Maps the heightmap float array to `float[,] heights` with bilinear interpolation to $(N+1) \times (N+1)$ resolution.
     * Sets `terrainData.heightmapResolution` and `terrainData.size = new Vector3(world_size[0], world_size[1], world_size[2])`.
     * Applies `terrainData.SetHeights(0, 0, heights)`.
   - Prefab Spawning via `PrefabUtility.InstantiatePrefab`:
     * Uses `PrefabUtility.InstantiatePrefab(prefabAsset)` when in Editor to preserve authentic prefab links (with `Object.Instantiate` runtime fallback).
     * Searches for prefabs by `prefab_name` in `Assets/PolygonMilitary/Prefabs/` (or via `AssetDatabase.FindAssets`).
     * Instantiates prefabs at `position = new Vector3(x, y, z)`, `rotation = Quaternion.Euler(rot)` or quaternion, `localScale = scale`.
     * Parents all spawned buildings under clean hierarchical GameObjects: `[WorldGen_Output] -> Zones -> Zone_{id}_{faction}_Destruction{level} -> Buildings`.
     * Implements full Undo support via `Undo.RegisterCreatedObjectUndo`.
   - Material & Texture Swapping Logic:
     * Extracts zone `faction` ('A', 'B', 'C') and `destruction` ('01', '02', '03', '04').
     * For every `Renderer` in the spawned prefab hierarchy:
       - Checks for existing materials or material name `PolygonMilitary_Mat_{destruction}_{faction}` in `Assets/PolygonMilitary/Materials/`.
       - Or dynamically modifies the material instance / `MaterialPropertyBlock`:
         * Sets `_MainTex` texture to `PolygonMilitary_Texture_{destruction}_{faction}.png` loaded from `Assets/PolygonMilitary/Textures/`.
         * Sets `_BumpMap` normal map to `PolygonMilitary_Texture_01_A_Normals.png`.
   - Road Instantiation:
     * Generates spline line renderers or ribbon meshes connecting road waypoints across the terrain.
2. Verify C# syntax and compilation using Mono `csc` compiler (`/Library/Frameworks/Mono.framework/Versions/Current/Commands/csc` or `csc /target:library`) with mock/stub UnityEngine assemblies or standalone syntax checker.
3. Write your handoff report to `/Users/jack/worldgen/.agents/m4_worker_1/handoff.md` and notify your parent via `send_message`.
