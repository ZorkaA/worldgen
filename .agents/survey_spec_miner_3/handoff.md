# Technical Survey & Specification Mining Report: WorldGen V2 Unity Importer & AI Layouts

**Working Directory**: `/Users/jack/worldgen/.agents/survey_spec_miner_3`  
**Authoritative Specs**: `/Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md`, `/Users/jack/worldgen/PROJECT.md`  
**Target Milestone**: WorldGen V2 (Dynamic Map Sizing, Adaptive Mesh Tessellation, AI Layout Templates, Interactive Zone Drag/Recompute)

---

## Executive Summary

This technical survey provides a comprehensive architectural and mathematical blueprint for WorldGen V2 across the Unity Importer package (`WorldManifestImporter.cs`), C# test harness, AI layout template generation (via local Ollama `qwen3.8:27b`), and test rubrics in `tests/rubrics/`.

### Key Findings:
1. **Unity Importer & C# Test Harness**:
   - Current `WorldManifestImporter.cs` implements a standalone recursive descent JSON parser, heightmap-to-Unity-`TerrainData` bilinear resampling, `PrefabUtility.InstantiatePrefab` asset linking, Synty theme material swapping (Faction A/B/C, Destruction 01-04), and Catmull-Rom road quad ribbon generation.
   - The offline Mono C# test suite (`WorldImporterTests.cs` [12 tests] and `AdversarialImporterTests.cs` [30 tests]) compiles and passes 100% cleanly against `UnityEngineStubs.cs` and `UnityEditorStubs.cs`.
2. **Adaptive Decimated Mesh in Unity (R3)**:
   - Unity's native `TerrainData` is strictly constrained to regular $2^n+1$ grid heightmaps and cannot represent non-uniform decimated meshes with variable-sized triangles/quads.
   - For V2 R3, the importer must be updated with an `AdaptiveMeshGenerator` to parse `terrain.mesh` (vertices, indices, normals, UVs) and instantiate an `AdaptiveTerrainMesh` GameObject with `MeshFilter`, `MeshRenderer`, and `MeshCollider` (supporting 32-bit index buffers for vertex counts $> 65535$), while retaining backward-compatible height sampling.
3. **AI Layout Template Generation & Continuous Density (R4)**:
   - A structured JSON layout template architecture has been designed for all 5 zone types (`military_base`, `airfield`, `outpost`, `radar_station`, `depot`).
   - Each template specifies semantic sub-districts, relative coordinate anchors, asset category pools, and continuous density activation thresholds ($D \in [0.0, 1.0]$).
   - Local Ollama `qwen3.8:27b` is verified active on the host machine and ready to generate offline templates cached into `backend/app/catalog/templates.json`, with a deterministic Python fallback generator.
4. **Rubric Updates for V2 Acceptance Criteria**:
   - `frontend_rubric.md` must be upgraded to evaluate Zone CRUD, 3D viewport center drag-to-recompute (without page reload), continuous density sliders, utilitarian UI standards, and Three.js adaptive mesh rendering.
   - `unity_rubric.md` must be upgraded to evaluate variable-sized triangle loading, 32-bit index buffer handling, normal orientations, UV alignment, and templated zone hierarchy organization.

---

## 1. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Unity Importer | JSON Manifest Deserializer | Custom recursive-descent JSON parser parsing metadata, terrain, zones, buildings, and roads without external DLLs | JSON string | `WorldManifest` object model | Throws `FormatException` or `ArgumentException` on unclosed braces/invalid tokens | `WorldManifestImporter.cs:219-641` |
| 2 | Unity Importer | Heightmap Resampling & Normalization | Bilinear interpolation of arbitrary heightmaps to valid Unity resolutions ($2^n+1$) with strict $[0, 1]$ clamping | `TerrainManifest`, target resolution, height scale | 2D float array `[z, x]` | Gracefully generates flat terrain if heightmap is empty | `WorldManifestImporter.cs:657-797` |
| 3 | Unity Importer | Live Prefab Spawning | Spawns project prefabs via `PrefabUtility.InstantiatePrefab` in Editor mode, preserving asset links | `BuildingManifest`, `ZoneManifest`, search folder | Instantiated `GameObject` | Falls back to bbox-proportional proxy cube if asset missing | `WorldManifestImporter.cs:808-937` |
| 4 | Unity Importer | Synty Theme Material Swapper | Replaces materials with Faction A/B/C and Destruction 01-04 assets or texture overrides while protecting glass/vehicle materials | `GameObject`, Faction string, Destruction string | Configured `Renderer.sharedMaterials` | Preserves existing material if target textures/materials not found | `WorldManifestImporter.cs:948-1134` |
| 5 | Unity Importer | Conforming Road Ribbon Builder | Catmull-Rom spline interpolation with $+0.15$m terrain clearance and 3D quad ribbon mesh generation | `RoadManifest`, `Terrain`, width | `GameObject` with `MeshFilter`, `MeshRenderer`, `LineRenderer` | Returns `null` if fewer than 2 unique waypoints | `WorldManifestImporter.cs:1145-1358` |
| 6 | Unity Importer | Editor Window Orchestrator | Unity EditorWindow GUI with file browsing, folder configuration, undo registration, and auto-framing | User GUI inputs / file paths | Complete scene hierarchy `[WorldGen_Output]` | Displays modal error dialog on missing file or parsing failure | `WorldManifestImporter.cs:1369-1724` |
| 7 | C# Test Harness | Unit & Adversarial Test Suites | Standalone test runner executables executing 42 test cases across 6 adversarial categories | C# source + stub assemblies | Console test results & exit codes (0=Pass, 1=Fail) | Captures and logs stack traces on assertion failures | `unity/tests/*.cs` |
| 8 | Unity V2 Spec | Adaptive Decimated Mesh Parser & Builder | Parses variable-sized triangle/quad data (`terrain.mesh`) and creates `MeshFilter` + `MeshRenderer` + `MeshCollider` | `TerrainManifest.mesh` (vertices, indices, normals, UVs) | `GameObject` ("AdaptiveTerrainMesh") | Falls back to standard Terrain if mesh data absent | V2 R3 Spec Probe |
| 9 | Unity V2 Spec | 32-bit Index Buffer Support | Configures `mesh.indexFormat = UInt32` when vertex count exceeds 65535 | Decimated mesh vertex buffer $> 65535$ | Valid Unity Mesh without vertex index overflow | Prevents mesh corruption or truncation | V2 R3 Spec Probe |
| 10 | AI Layout | Ollama Qwen Template Generation | Prompts local `qwen3.8:27b` via Ollama API to generate structured semantic layout templates for 5 zone types | Prompt + catalog taxonomy | JSON template files in `backend/app/catalog/templates.json` | Falls back to deterministic rule generator if Ollama unavailable | V2 R4 Spec Probe |
| 11 | AI Layout | Continuous Density Scaling | Maps continuous slider value $D \in [0.0, 1.0]$ to template asset density thresholds | Density float $D \in [0.0, 1.0]$, zone type | Filtered list of structured asset placements | Reverts to base HQ anchors when density is minimal | V2 R4 Spec Probe |
| 12 | AI Layout | SAT OBB Template Alignment | Places templated buildings adhering to template sub-district offsets and SAT collision avoidance | Template rules, terrain elevation, zone center | Non-overlapping `BuildingPlacement` array | Drops non-fitting props after max retry attempts | V2 R4 Spec Probe |
| 13 | Frontend V2 Spec | Zone Center Drag & Drop Raycasting | Viewport interaction allowing dragging zone centers along XZ terrain plane with instant visual feedback | Mouse drag events on 3D zone beacons | Updated zone center coordinates `[cx, cy, cz]` | Clamps drag position within global map bounds | V2 R2 Spec Probe |
| 14 | Frontend V2 Spec | Live Recompute Pipeline Trigger | Triggers `/generate` or `/recompute` on zone drop and updates terrain, roads, and buildings without page reload | Drag release event / modified zone payload | Updated Three.js scene graphs | Reverts to previous state and displays HUD notification on API error | V2 R2 Spec Probe |
| 15 | Rubrics V2 Spec | V2 Verification Criteria Matrix | Quantitative rubrics evaluating zone drag, continuous density, utilitarian UI, and adaptive mesh loading | Codebase implementation & visual execution | Score $[0..100]$ & Acceptance Decision | Flags anti-patterns (e.g. page reloads, non-normalized heights) | `tests/rubrics/*.md` |

---

## 2. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | JSON Deserializer | Escaped Unicode (`\u0041`, `\u03a9`) and special characters | Correctly decodes Unicode code points and escaped quotes without truncation |
| 2 | JSON Deserializer | Scientific notation numbers (`1e5`, `-1.2e-4`, `5.5e1`) | Successfully parsed into high-precision floats and doubles |
| 3 | JSON Deserializer | Inverted Bounding Box Min/Max (`min > max`) | Handled via `Mathf.Abs(max - min)`, computing positive valid dimensions |
| 4 | JSON Deserializer | Degenerate Quaternion `[0, 0, 0, 0]` | Detects magnitude squared $< 0.001$ and falls back to `Quaternion.identity` |
| 5 | Terrain Resampling | Non-square heightmaps (e.g. $4 \times 8$ rows/cols) | Bilinear interpolation resamples correctly to target square resolution without NaN |
| 6 | Terrain Resampling | 1D heightmap with non-perfect square length (e.g. 10 elements) | Safely computes side length via `RoundToInt(Sqrt(len))` and samples valid indices |
| 7 | Terrain Resampling | Inverted min/max elevation metadata (`min_height > max_height`) | Terrain normalized strictly into $[0.0, 1.0]$ range based on height scale |
| 8 | Road Ribbon | Duplicate and near-consecutive waypoints ($< 0.1$m distance) | Filtered during pre-processing, preventing zero-length tangents and NaN vertex offsets |
| 9 | Road Ribbon | Vertical waypoints (tangent $=$ `Vector3.up`) | Cross-product singularity handled by fallback right vector (`Vector3.right`), avoiding gimbal lock |
| 10 | Road Ribbon | Sharp acute hairpins (170-degree turns) | Normals and tangents remain non-NaN, ribbon quads maintain valid topology |
| 11 | Prefab Spawner | Unregistered / Missing Prefab Name | Spawns fallback orange/gray primitive Cube matching exact bounding box dimensions |
| 12 | Prefab Spawner | Orphaned buildings (referencing non-existent `zone_id`) | Instantiates under root `Zones` GameObject without throwing `NullReferenceException` |
| 13 | Material Swapper | Non-standard faction/destruction strings (`"faction_B"`, `"3"`, `"pristine"`) | Normalized to standard `"B"`, `"03"`, `"01"` via robust suffix matching |
| 14 | Material Swapper | Protected materials (`PolygonMilitary_Glass_01`, `Vehicles`) | Preserved intact without overriding albedo/normal textures |
| 15 | Adaptive Mesh | Large terrain decimation vertex count ($> 65,535$ vertices) | Requires `IndexFormat.UInt32` on `Mesh` to prevent index wrapping in Unity |
| 16 | Adaptive Mesh | Variable-sized triangle seams across flat-to-steep transitions | Requires consistent vertex sharing or Delaunay triangulation constraint to prevent T-junction cracks |
| 17 | AI Layout Templates | Continuous density set to extreme low ($D = 0.0$) or extreme high ($D = 1.0$) | $D=0.0$ spawns only primary command anchor; $D=1.0$ saturates all clutter/prop slots respecting SAT buffers |
| 18 | AI Layout Templates | Zone footprint deformed / non-circular | Relative normalized offsets scaled along radial boundary $R(\theta)$, conforming to organic perimeter |
| 19 | Zone Drag Viewport | Zone dragged outside map boundaries ($x < 0$ or $x > width$) | Viewport raycaster clamps coordinates to $[margin, width - margin]$ |
| 20 | Zone Drag Viewport | Rapid consecutive drag-and-drop events | Backend recomputation debounced or aborted via `AbortController`, preventing race conditions |

---

## 3. Investigation Area 1: Current Unity Importer & C# Test Harness

### 3.1 Architecture of `WorldManifestImporter.cs`

The current Unity importer is located at `unity/Assets/Editor/WorldManifestImporter.cs` (1,728 lines) and is structured into six core components:

```
WorldManifestImporter.cs
├── Namespace WorldGen.Core
│   ├── Data Models: WorldManifest, TerrainManifest, ZoneManifest, BuildingManifest, RoadManifest, BoundingBoxManifest
│   └── ManifestJsonParser: Zero-dependency recursive descent JSON tokenizer and parser
└── Namespace WorldGen.Editor
    ├── TerrainGenerator: Heightmap normalization, bilinear resampling to (2^n + 1), TerrainData instantiation
    ├── PrefabSpawner: AssetDatabase indexing, PrefabUtility.InstantiatePrefab live links, Proxy Cube fallback
    ├── MaterialSwapper: Faction (A/B/C) & Destruction (01-04) resolution, dynamic texture swap, material preservation
    ├── RoadMeshBuilder: Catmull-Rom spline sampling, terrain height conformity, 3D quad ribbon mesh generator
    └── WorldManifestImporterWindow: EditorWindow GUI, progress bar, undo stack integration, scene framing
```

#### Key Mechanics:
1. **JSON Parsing (`ManifestJsonParser`)**:
   - Implements recursive descent parsing supporting nested dictionaries, heterogeneously typed lists, 1D/2D float arrays, and robust type coercion (`ConvertToInt`, `ConvertToFloat`).
   - Handles malformed data, scientific notation (`1.2e4`), unicode escapes (`\u0041`), and missing attributes with deterministic defaults.
2. **Terrain Generation (`TerrainGenerator`)**:
   - Unity terrain requires heightmap dimensions of $2^n + 1$ (e.g. 65, 129, 257, 513, 1025). `CalculateUnityHeightmapResolution` selects the minimal power-of-two plus one.
   - `ResampleHeightmap` performs 2D bilinear interpolation across $[0, 1]$ normalized coordinates and strictly clamps output to $[0.0, 1.0]$ in $[z, x]$ array indexing.
3. **Prefab Spawning (`PrefabSpawner`)**:
   - Uses `PrefabUtility.InstantiatePrefab(prefabAsset, parent)` in Editor mode to preserve authentic source prefab connections (meeting Acceptance Criteria).
   - If an asset cannot be found, `CreateProxyCube` spawns a primitive Cube scaled to the bounding box dimensions (`scale * bbox.size`), assigning a distinct proxy material.
4. **Theme & Material Swapper (`MaterialSwapper`)**:
   - Target material pattern: `PolygonMilitary_Mat_{destruction}_{faction}.mat`.
   - Fallback dynamic texture swapping: sets `_MainTex` to `PolygonMilitary_Texture_{destruction}_{faction}.png` and `_BumpMap` to `PolygonMilitary_Texture_01_A_Normals.png`.
   - Preserves special materials (`Glass`, `Vehicles`, `Decals`, `FX`, `Water`, `Screen`, `UI`) via `IsProtectedMaterial`.
5. **Road Construction (`RoadMeshBuilder`)**:
   - Centripetal Catmull-Rom spline interpolation through waypoints.
   - Conforms elevation to terrain height with $+0.15$m offset to eliminate z-fighting.
   - Builds 3D Quad Ribbon Mesh (`MeshFilter` + `MeshRenderer`) and companion `LineRenderer`.
6. **Scene Hierarchy**:
   ```
   [WorldGen_Output]
   ├── Terrain (Terrain + TerrainCollider)
   ├── Roads
   │   └── Road_road_0_1
   └── Zones
       ├── Zone_zone_0_FactionA_Destruction02
       │   └── SM_Bld_Tent_01_bld_0
       └── Zone_zone_1_FactionB_Destruction01
           └── SM_Bld_Watchtower_01_bld_1
   ```

### 3.2 C# Test Harness & Offline Mono Verification

The C# codebase is tested offline using Mono's `csc` compiler against custom stub assemblies (`UnityEngineStubs.cs` and `UnityEditorStubs.cs`):

```bash
# Compilation and test command
/Library/Frameworks/Mono.framework/Versions/Current/Commands/csc /target:exe /define:UNITY_EDITOR \
  /out:unity/WorldImporterTests.exe \
  unity/stubs/UnityEngineStubs.cs unity/stubs/UnityEditorStubs.cs \
  unity/Assets/Editor/WorldManifestImporter.cs unity/tests/WorldImporterTests.cs

/Library/Frameworks/Mono.framework/Versions/Current/Commands/mono unity/WorldImporterTests.exe
```

- **Unit Tests (`WorldImporterTests.cs`)**: 12 test cases covering JSON parsing, heightmap math, bilinear resampling, material rules, road geometry, proxy sizing, and sample manifest import. (**12/12 Passed**).
- **Adversarial Stress Tests (`AdversarialImporterTests.cs`)**: 30 test cases covering JSON fuzzing, non-square heightmaps, extreme elevations, inverted min/max, zero scale, degenerate quaternions, gimbal lock avoidance, and 500-building batching. (**30/30 Passed**).

---

## 4. Investigation Area 2: Updating Unity Importer for R3 (Adaptive Decimated Mesh)

### 4.1 The Technical Challenge

Requirement R3 specifies:
> "Implement backend mesh decimation: generate an optimized mesh structure where triangle/quad sizes vary depending on the area (e.g., larger triangles on flat plains, smaller/denser on steep slopes). This optimized mesh must be sent to the frontend and Unity."

**Constraint in Unity**: Unity's native `UnityEngine.Terrain` / `TerrainData` component is strictly an elevation raster grid with fixed $(2^n + 1) \times (2^n + 1)$ resolution. It cannot represent non-uniform decimated meshes with variable-sized triangles.

### 4.2 Architectural Solution: Dual-Mode Mesh & Terrain Representation

To support adaptive decimated meshes in Unity while maintaining full compatibility with the existing pipeline:

```
                                [world_manifest.json]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       terrain.mesh (Adaptive Mesh)               terrain.heightmap (Grid Raster)
                   │                                           │
                   ▼                                           ▼
       [AdaptiveMeshGenerator]                         [TerrainGenerator]
                   │                                           │
                   ▼                                           ▼
    GameObject: "AdaptiveTerrainMesh"               GameObject: "Terrain"
    ├── MeshFilter (sharedMesh = mesh)              ├── Terrain (TerrainData)
    ├── MeshRenderer (Standard Terrain Mat)         └── TerrainCollider (TerrainData)
    └── MeshCollider (sharedMesh = mesh)
```

### 4.3 Manifest Schema Contract for Adaptive Decimated Mesh

Extend `TerrainManifest` in `schemas.py` and `WorldGen.Core`:

```json
{
  "terrain": {
    "resolution": 513,
    "world_size": [1000.0, 150.0, 1000.0],
    "heightmap": [[0.0, 10.5, ...]],
    "mesh": {
      "vertices": [
        [0.0, 0.0, 0.0],
        [50.0, 2.5, 0.0],
        [25.0, 45.0, 30.0]
      ],
      "indices": [0, 1, 2, 2, 3, 0],
      "normals": [
        [0.0, 1.0, 0.0],
        [0.1, 0.95, -0.2],
        [0.0, 0.7, 0.7]
      ],
      "uvs": [
        [0.0, 0.0],
        [0.05, 0.0],
        [0.025, 0.03]
      ]
    }
  }
}
```

*Note: For optimal serialization and transfer speed, `vertices` and `indices` can also be parsed if provided as flat 1D float/int arrays (`[x0, y0, z0, x1, y1, z1, ...]` and `[i0, i1, i2, ...]`).*

### 4.4 Unity C# Implementation Details

1. **Data Model Updates in `WorldGen.Core`**:
   ```csharp
   [Serializable]
   public class MeshDataManifest
   {
       public List<float[]> vertices = new List<float[]>();
       public List<int> indices = new List<int>();
       public List<float[]> normals = new List<float[]>();
       public List<float[]> uvs = new List<float[]>();
       public float[] flat_vertices = null;
       public int[] flat_indices = null;
   }
   ```
2. **`AdaptiveMeshGenerator` in `WorldGen.Editor`**:
   ```csharp
   public static class AdaptiveMeshGenerator
   {
       public static GameObject BuildAdaptiveMesh(TerrainManifest manifest, Transform parentTransform)
       {
           if (manifest == null || manifest.mesh == null) return null;

           var meshData = manifest.mesh;
           int vertCount = meshData.vertices.Count > 0 ? meshData.vertices.Count : (meshData.flat_vertices != null ? meshData.flat_vertices.Length / 3 : 0);
           if (vertCount == 0) return null;

           Mesh mesh = new Mesh();
           mesh.name = "Terrain_AdaptiveDecimatedMesh";

           // Handle 32-bit indices if vertex count > 65535
           if (vertCount > 65535)
           {
               mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
           }

           // Populate vertices
           Vector3[] vertices = new Vector3[vertCount];
           Vector2[] uvs = new Vector2[vertCount];
           float width = manifest.GetWidth();
           float length = manifest.GetLength();

           for (int i = 0; i < vertCount; i++)
           {
               if (meshData.vertices.Count > 0)
               {
                   float[] v = meshData.vertices[i];
                   vertices[i] = new Vector3(v[0], v[1], v[2]);
               }
               else
               {
                   vertices[i] = new Vector3(meshData.flat_vertices[i * 3], meshData.flat_vertices[i * 3 + 1], meshData.flat_vertices[i * 3 + 2]);
               }

               // UV mapping [0, 1] relative to terrain dimensions
               if (meshData.uvs != null && i < meshData.uvs.Count)
                   uvs[i] = new Vector2(meshData.uvs[i][0], meshData.uvs[i][1]);
               else
                   uvs[i] = new Vector2(vertices[i].x / width, vertices[i].z / length);
           }

           mesh.vertices = vertices;
           mesh.uv = uvs;

           // Populate triangles / indices
           if (meshData.indices.Count > 0)
               mesh.triangles = meshData.indices.ToArray();
           else if (meshData.flat_indices != null)
               mesh.triangles = meshData.flat_indices;

           // Compute or assign normals
           if (meshData.normals != null && meshData.normals.Count == vertCount)
           {
               Vector3[] normals = new Vector3[vertCount];
               for (int i = 0; i < vertCount; i++)
                   normals[i] = new Vector3(meshData.normals[i][0], meshData.normals[i][1], meshData.normals[i][2]);
               mesh.normals = normals;
           }
           else
           {
               mesh.RecalculateNormals();
           }

           mesh.RecalculateBounds();
           mesh.RecalculateTangents();

           // Create GameObject
           GameObject go = new GameObject("AdaptiveTerrainMesh");
           go.transform.position = Vector3.zero;
           go.transform.rotation = Quaternion.identity;
           go.transform.localScale = Vector3.one;
           if (parentTransform != null) go.transform.SetParent(parentTransform, false);

           MeshFilter mf = go.AddComponent<MeshFilter>();
           mf.sharedMesh = mesh;

           MeshRenderer mr = go.AddComponent<MeshRenderer>();
           mr.sharedMaterial = CreateTerrainMaterial();

           MeshCollider mc = go.AddComponent<MeshCollider>();
           mc.sharedMesh = mesh;

           return go;
       }
   }
   ```
3. **Editor GUI Options**:
   - In `WorldManifestImporterWindow`, add a dropdown: `Terrain Mode: [Adaptive Decimated Mesh | Unity TerrainData | Hybrid Both]`.

---

## 5. Investigation Area 3: AI Layout Templates & Continuous Density Scaling (R4)

### 5.1 The Requirement

Requirement R4 specifies:
> "Replace the density dropdown with a continuous density slider. Replace random asset allocation with a system driven by offline JSON layout templates (which you will generate using the Qwen model), ensuring structured, denser, and more realistic environments based on zone type."

### 5.2 Five Zone Types & Spatial Micro-Districts

Military environments possess distinct spatial functions, perimeter topologies, and building densities:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            ZONE TAXONOMY MATRIX                              │
├─────────────────┬───────────────────────────────┬────────────────────────────┤
│ Zone Type       │ Core Semantic Micro-Districts │ Primary Asset Affinities   │
├─────────────────┼───────────────────────────────┼────────────────────────────┤
│ military_base   │ • Command HQ & Comms          │ SM_Bld_Village_House_01    │
│                 │ • Barracks Tent Rows          │ SM_Bld_Tent_01, Desert_01  │
│                 │ • Vehicle Motor Pool          │ SM_Veh_Truck_Military_01   │
│                 │ • Perimeter Sandbag Bunkers   │ SM_Prop_Sandbags_01        │
│                 │ • Corner Watchtowers          │ SM_Bld_Watchtower_01       │
├─────────────────┼───────────────────────────────┼────────────────────────────┤
│ airfield        │ • Runway / Landing Strip      │ Conforming Flat Runway     │
│                 │ • Aircraft Hangars            │ SM_Bld_Hangar_01           │
│                 │ • Flight Control Tower        │ SM_Bld_Watchtower_01       │
│                 │ • Fuel Storage Tanks          │ SM_Bld_WaterTank_01        │
│                 │ • Maintenance Generators      │ SM_Prop_Generator_01       │
├─────────────────┼───────────────────────────────┼────────────────────────────┤
│ outpost         │ • Central Forward Bivouac     │ SM_Bld_Tent_01             │
│                 │ • Elevated Observation Tower  │ SM_Bld_Village_House_Tower │
│                 │ • Sandbag Firing Positions    │ SM_Prop_Sandbag_01         │
│                 │ • Supply Ammunition Stacks    │ SM_Prop_Crate_Military_01  │
├─────────────────┼───────────────────────────────┼────────────────────────────┤
│ radar_station   │ • Primary Radar Array Dome    │ SM_Bld_Village_House_Tower │
│                 │ • Power Generation Plant      │ SM_Prop_Generator_01       │
│                 │ • Technical Comms Bunker      │ SM_Bld_Village_House_01    │
│                 │ • Perimeter Security Post     │ SM_Prop_Sandbags_01        │
├─────────────────┼───────────────────────────────┼────────────────────────────┤
│ depot           │ • Heavy Storage Warehouses    │ SM_Bld_Village_House_01    │
│                 │ • Logistics Truck Staging     │ SM_Veh_Truck_Military_01   │
│                 │ • Ammunition Crate Pallets    │ SM_Prop_Crate_Military_01  │
│                 │ • Fuel & Water Reservoirs     │ SM_Bld_WaterTank_01        │
└─────────────────┴───────────────────────────────┴────────────────────────────┘
```

### 5.3 Offline JSON Layout Template Schema

Each template entry defines relative normalized coordinates $[-1.0, 1.0]$, asset candidates, orientation rules, and a `density_threshold` $D_{min} \in [0.0, 1.0]$:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "version": "2.0.0",
  "zone_templates": {
    "military_base": {
      "type": "military_base",
      "display_name": "Fortified Military Base",
      "recommended_radius": [60.0, 110.0],
      "sub_districts": [
        {
          "district_id": "command_core",
          "center_offset": [0.0, 0.0],
          "radius_factor": 0.35,
          "slots": [
            {
              "slot_id": "hq_main",
              "rel_pos": [0.0, 0.0],
              "placement_role": "command",
              "candidates": ["SM_Bld_Village_House_01", "SM_Bld_Tent_01"],
              "orientation": { "type": "fixed", "yaw_deg": 0.0 },
              "density_threshold": 0.0,
              "buffer_meters": 3.0,
              "priority": 1
            },
            {
              "slot_id": "hq_comms_tower",
              "rel_pos": [0.18, 0.12],
              "placement_role": "watchtower",
              "candidates": ["SM_Bld_Watchtower_01"],
              "orientation": { "type": "face_outward" },
              "density_threshold": 0.25,
              "buffer_meters": 2.0,
              "priority": 2
            }
          ]
        },
        {
          "district_id": "barracks_row",
          "center_offset": [-0.45, 0.1],
          "radius_factor": 0.4,
          "slots": [
            {
              "slot_id": "tent_01",
              "rel_pos": [-0.35, -0.15],
              "placement_role": "barracks",
              "candidates": ["SM_Bld_Tent_01", "SM_Bld_Tent_Desert_01"],
              "orientation": { "type": "fixed", "yaw_deg": 90.0 },
              "density_threshold": 0.15,
              "buffer_meters": 2.0,
              "priority": 2
            },
            {
              "slot_id": "tent_02",
              "rel_pos": [-0.35, 0.15],
              "placement_role": "barracks",
              "candidates": ["SM_Bld_Tent_01", "SM_Bld_Tent_Desert_01"],
              "orientation": { "type": "fixed", "yaw_deg": 90.0 },
              "density_threshold": 0.35,
              "buffer_meters": 2.0,
              "priority": 3
            },
            {
              "slot_id": "tent_03",
              "rel_pos": [-0.55, -0.15],
              "placement_role": "barracks",
              "candidates": ["SM_Bld_Tent_01"],
              "orientation": { "type": "fixed", "yaw_deg": 90.0 },
              "density_threshold": 0.65,
              "buffer_meters": 2.0,
              "priority": 4
            }
          ]
        },
        {
          "district_id": "perimeter_defenses",
          "center_offset": [0.0, 0.0],
          "radius_factor": 0.85,
          "slots": [
            {
              "slot_id": "tower_north",
              "rel_pos": [0.0, 0.8],
              "placement_role": "watchtower",
              "candidates": ["SM_Bld_Watchtower_01", "SM_Bld_Village_House_Tower_01"],
              "orientation": { "type": "face_outward" },
              "density_threshold": 0.2,
              "buffer_meters": 2.0,
              "priority": 2
            },
            {
              "slot_id": "tower_south",
              "rel_pos": [0.0, -0.8],
              "placement_role": "watchtower",
              "candidates": ["SM_Bld_Watchtower_01"],
              "orientation": { "type": "face_outward" },
              "density_threshold": 0.45,
              "buffer_meters": 2.0,
              "priority": 3
            },
            {
              "slot_id": "sandbag_gate_left",
              "rel_pos": [0.72, 0.1],
              "placement_role": "defenses",
              "candidates": ["SM_Prop_Sandbags_01", "SM_Prop_Sandbag_01"],
              "orientation": { "type": "face_outward" },
              "density_threshold": 0.5,
              "buffer_meters": 1.0,
              "priority": 4
            },
            {
              "slot_id": "crate_stack_01",
              "rel_pos": [0.3, -0.4],
              "placement_role": "prop",
              "candidates": ["SM_Prop_Crate_Military_01"],
              "orientation": { "type": "random" },
              "density_threshold": 0.75,
              "buffer_meters": 0.8,
              "priority": 5
            }
          ]
        }
      ]
    }
  }
}
```

### 5.4 Continuous Density Allocation Mathematics

When the continuous density slider $D \in [0.0, 1.0]$ is evaluated:
1. **Activation Filter**: A slot $S_k$ is eligible for placement if and only if $S_k.\text{density\_threshold} \le D$.
2. **Radial Boundary Scaling**: The world coordinate $(X_k, Z_k)$ of slot $S_k$ with relative offset $(u_k, v_k)$ in a zone with organic deformed radius $R(\theta_k)$ is:
   $$\theta_k = \text{atan2}(v_k, u_k)$$
   $$\rho_k = \sqrt{u_k^2 + v_k^2}$$
   $$X_k = C_x + \rho_k \cdot R(\theta_k) \cdot \cos(\theta_k + \psi_{\text{zone}})$$
   $$Z_k = C_z + \rho_k \cdot R(\theta_k) \cdot \sin(\theta_k + \psi_{\text{zone}})$$
   where $\psi_{\text{zone}}$ is a zone-specific random rotation angle for orientation variety.
3. **SAT Collision & Slope Validation**: Check 2D OBB overlap against previously placed buildings and verify terrain slope $\Delta H < 2.5\text{m}$.
4. **Result**: Total asset count $N(D)$ scales monotonically and smoothly with $D$ without artificial pop-in or spatial overlap.

### 5.5 Qwen Generation Pipeline & Deterministic Fallback

1. **Host Ollama Integration**:
   - Host has `qwen3.8:27b` loaded in Ollama.
   - Script `backend/app/catalog/generate_templates.py` queries `POST http://localhost:11434/api/generate` with `format: "json"` to synthesize variations.
2. **Deterministic Fallback Generator**:
   - To guarantee zero-latency execution and offline CI/CD stability, the Python generator script provides pre-compiled baseline templates in `backend/app/catalog/templates.json` covering all 5 zone types with $> 40$ slots each.

---

## 6. Investigation Area 4: Review Rubrics Update for V2 Acceptance Criteria

### 6.1 Updates to `tests/rubrics/frontend_rubric.md`

The frontend rubric must be updated to incorporate V2 requirements:

```markdown
### 1.4 Interactive Zone CRUD & Viewport Drag-to-Recompute (Weight: 20%) [NEW IN V2]
- [ ] **Zone CRUD in Side Panel**:
  - Full CRUD operations: "Add Zone", "Remove Zone", "Rename Zone".
  - UI inputs allow modifying zone faction, destruction, and continuous density slider ($0.0-1.0$).
- [ ] **3D Viewport Zone Center Dragging**:
  - Zone center pins/beacons can be grabbed and dragged interactively in the Three.js viewport along the terrain XZ plane.
  - Smooth visual feedback during drag (e.g. ghost footprint or live position updates).
- [ ] **Live Backend Recompute on Drop**:
  - On pointer release (drop), frontend dispatches recompute request to `/api/generate` or `/api/recompute`.
  - Viewport smoothly updates terrain mesh, zone boundaries, building models, and road splines without a full page reload.

### 1.5 Global Map Parameters & Utilitarian Standards (Weight: 15%) [NEW IN V2]
- [ ] **Global Dimension & Granularity Controls**:
  - Map Width & Length sliders in kilometers ($0.5\text{km} - 4.0\text{km}$).
  - Resolution/granularity slider ($65 - 1025$).
  - Terrain deformation strength and edge margin sliders.
- [ ] **Utilitarian UI (R5 Compliance)**:
  - Stripped of generic "AI slop" terminology (e.g. "Procedural Military Designer"). Clean, tactical, CAD-style military interface.

### 1.2 Procedural Terrain & Adaptive Mesh Rendering (Weight: 15%) [UPDATED IN V2]
- [ ] **Adaptive Decimated Mesh Rendering**:
  - Seamlessly renders `terrain.mesh` with non-uniform triangle density (dense geometry on cliffs/slopes, sparse geometry on flat plains).
  - Slope-aware vertex coloring and wireframe overlay clearly showing variable-sized triangles/quads.
```

### 6.2 Updates to `tests/rubrics/unity_rubric.md`

The Unity rubric must be updated to verify V2 acceptance criteria:

```markdown
### 1.5 Adaptive Decimated Mesh Loading & Topology (Weight: 25%) [NEW IN V2]
- [ ] **Adaptive Mesh Instantiation**:
  - Parses `terrain.mesh` (vertices, indices, normals, UVs) from `world_manifest.json`.
  - Instantiates `AdaptiveTerrainMesh` GameObject with `MeshFilter`, `MeshRenderer`, and `MeshCollider`.
- [ ] **Topology & Index Format Compliance**:
  - Configures `Mesh.indexFormat = UInt32` when vertex count exceeds 65,535.
  - Verified variable-sized triangles/quads load with correct counter-clockwise winding, non-inverted normals, and bounding box bounds.
  - Coordinate system matches world bounds without horizontal inversion.
- [ ] **Material & Road Conformance**:
  - Assigns terrain material with UV coordinates $[0, 1]$ scaled to $(width, length)$.
  - Roads correctly sample elevation from adaptive mesh colliders.

### 1.2 Templated Asset Placement & Continuous Density (Weight: 25%) [UPDATED IN V2]
- [ ] **Continuous Density Hierarchy**:
  - Importer instantiates buildings generated via AI layout templates with variable density distributions.
  - Preserves hierarchical structure under zone GameObjects.
```

---

## 7. 5-Component Handoff Report

### 1. Observation
- Inspected `unity/Assets/Editor/WorldManifestImporter.cs` (1,728 lines), `unity/tests/WorldImporterTests.cs` (442 lines), `unity/tests/AdversarialImporterTests.cs` (788 lines), `unity/stubs/UnityEngineStubs.cs` (354 lines), and `unity/stubs/UnityEditorStubs.cs` (167 lines).
- Executed Mono `csc` compiler and test runner:
  - `WorldImporterTests.exe`: 12/12 passed (0 failures).
  - `AdversarialImporterTests.exe`: 30/30 passed (0 failures).
- Inspected `tests/rubrics/frontend_rubric.md` (86 lines) and `tests/rubrics/unity_rubric.md` (78 lines).
- Verified Ollama daemon running with `qwen3.8:27b` available locally.
- Analyzed backend schemas (`backend/app/core/schemas.py`) and generation algorithms (`terrain.py`, `erosion.py`, `zones.py`, `buildings.py`, `roads.py`).

### 2. Logic Chain
1. **Unity Importer R3 Capability**:
   - Observation: Unity `TerrainData` is strictly a square $2^n+1$ elevation grid.
   - Inference: Decimated meshes containing variable-sized triangles cannot be stored in `TerrainData`.
   - Conclusion: Unity importer must construct a `Mesh` object (`MeshFilter` + `MeshRenderer` + `MeshCollider`) named `AdaptiveTerrainMesh` when `terrain.mesh` is present in the manifest.
2. **AI Layout Templates & Continuous Density R4**:
   - Observation: V1 used random placement with discrete density strings (`"low"`, `"medium"`, `"high"`).
   - Inference: Continuous density $D \in [0.0, 1.0]$ requires fine-grained activation thresholds per building slot.
   - Conclusion: Structure templates with sub-districts and `density_threshold` floats, where elements activate when $\text{density\_threshold} \le D$, placing anchors first and micro-clutter at high density.
3. **Rubrics Alignment**:
   - Observation: Existing rubrics evaluate only V1 features (static generation, discrete density, standard terrain).
   - Inference: Agent-as-Judge verification for V2 acceptance criteria requires explicit checklists for zone drag/recompute, continuous density, utilitarian UI, and adaptive decimated mesh loading.
   - Conclusion: Update `frontend_rubric.md` and `unity_rubric.md` to reflect V2 requirements.

### 3. Caveats
- `Mesh.indexFormat = UInt32` is required in Unity when vertex count $> 65,535$; stub implementations in Mono test harness must reflect this property.
- When generating templates via Ollama `qwen3.8:27b`, response time varies with system load. A cached `templates.json` with a deterministic Python fallback is essential for instant test execution.
- No other caveats.

### 4. Conclusion
The technical survey confirms that the Unity Importer and C# test harness are architecturally sound and easily extensible for V2. Adding the `AdaptiveMeshGenerator` handles R3 decimated mesh loading in Unity. Defining the hierarchical template schema and continuous density thresholding satisfies R4. The updated rubrics provide rigorous, unambiguous criteria for V2 validation.

### 5. Verification Method
1. **Compile & Run Unity Unit Tests**:
   ```bash
   /Library/Frameworks/Mono.framework/Versions/Current/Commands/csc /target:exe /define:UNITY_EDITOR \
     /out:unity/WorldImporterTests.exe \
     unity/stubs/UnityEngineStubs.cs unity/stubs/UnityEditorStubs.cs \
     unity/Assets/Editor/WorldManifestImporter.cs unity/tests/WorldImporterTests.cs
   /Library/Frameworks/Mono.framework/Versions/Current/Commands/mono unity/WorldImporterTests.exe
   ```
2. **Compile & Run Unity Adversarial Stress Tests**:
   ```bash
   /Library/Frameworks/Mono.framework/Versions/Current/Commands/csc /target:exe /define:UNITY_EDITOR \
     /out:unity/AdversarialImporterTests.exe \
     unity/stubs/UnityEngineStubs.cs unity/stubs/UnityEditorStubs.cs \
     unity/Assets/Editor/WorldManifestImporter.cs unity/tests/AdversarialImporterTests.cs
   /Library/Frameworks/Mono.framework/Versions/Current/Commands/mono unity/AdversarialImporterTests.exe
   ```
3. **Inspect Output Files**:
   - View `/Users/jack/worldgen/.agents/survey_spec_miner_3/handoff.md`
   - View `/Users/jack/worldgen/.agents/survey_spec_miner_3/progress.md`
   - View `/Users/jack/worldgen/.agents/survey_spec_miner_3/BRIEFING.md`
