# Unity Importer Review Rubric (WorldGen V2: Adaptive Terrain Mesh & Templated Importer)

## Objective
This Agent-as-Judge rubric evaluates the implementation quality, C# architectural rigor, Unity Editor API compliance, 32-bit index buffer adaptive mesh loading, asset linkage preservation, and material swapping accuracy for **WorldGen V2 Requirements R3 and R4**.

---

## 1. Evaluation Dimensions & Checklists

### 1.1 AdaptiveTerrainMesh & 32-Bit Index Buffers (Weight: 30%)
- [ ] **Adaptive Mesh Instantiation**:
  - Creates dedicated `AdaptiveTerrainMesh` GameObject under `[WorldGen_Output] -> Terrain`.
  - Attaches required components: `MeshFilter`, `MeshRenderer`, and `MeshCollider`.
- [ ] **32-Bit Index Buffer Configuration**:
  - **MANDATORY**: Sets `mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32` prior to setting vertices/triangles to support high-resolution meshes exceeding 65,535 vertices without buffer overflow.
- [ ] **Variable-Density Geometry Loading**:
  - Parses `manifest.terrain.mesh.vertices` into `Vector3[]` vertices array (handling X, Y, Z coordinate mapping).
  - Parses `manifest.terrain.mesh.indices` into `int[]` triangles array.
  - Verifies correct triangle winding order (clockwise for Unity backface culling) so terrain faces upward.
  - Ingests `manifest.terrain.mesh.normals` into `Vector3[]` (or calls `mesh.RecalculateNormals()`).
  - Ingests `manifest.terrain.mesh.uvs` into `Vector2[]` UV coordinates.
  - Assigns generated mesh to `MeshCollider.sharedMesh` for accurate Editor/physics raycasting.
- [ ] **Dual Mode Support**:
  - Supports standard Unity `TerrainData` generation if `terrain.heightmap` is present, alongside or selectable with `AdaptiveTerrainMesh`.

### 1.2 Prefab Spawning via PrefabUtility (Weight: 25%)
- [ ] **Editor Link Preservation**:
  - **MANDATORY**: Uses `PrefabUtility.InstantiatePrefab(prefabAsset, parentTransform)` when executed in the Editor to ensure instantiated GameObjects maintain live links to the project's source Prefabs.
  - **FORBIDDEN IN EDITOR**: Using plain `Object.Instantiate` or `GameObject.Instantiate` (which breaks prefab connection and converts prefabs to plain GameObjects).
- [ ] **Asset Resolution & Missing Asset Fallback**:
  - Indexes prefabs in `Assets/PolygonMilitary/Prefabs` via `AssetDatabase.FindAssets("t:Prefab")`.
  - If a prefab is missing, instantiates a fallback primitive Cube proxy with matching bounding box dimensions and logs a descriptive warning.
- [ ] **Transform & Rotation Accuracy**:
  - Accurately applies `position`, `rotation` (Euler or Quaternion), and `localScale` matching `world_manifest.json`.

### 1.3 Templated Zone Hierarchy & Structure (Weight: 20%)
- [ ] **Hierarchical Organization**:
  - Groups all generated objects under a clean root GameObject: `[WorldGen_Output]`.
  - Sub-parents organized logically to reflect templated zone layout:
    ```
    [WorldGen_Output]
    ├── Terrain (AdaptiveTerrainMesh + MeshCollider)
    ├── Roads
    │   └── Road_zone_0_zone_1 (Spline Mesh / Waypoints)
    └── Zones
        ├── Zone_0_MilitaryBase_FactionA
        │   ├── District_command_hq
        │   │   ├── SM_Bld_Village_House_01 (HQ Main)
        │   │   └── SM_Bld_Watchtower_01 (Comms Array)
        │   └── District_barracks_row
        │       └── SM_Bld_Tent_01 (Barracks 1)
        └── Zone_1_Airfield_FactionB
            └── District_hangar_line
    ```
- [ ] **Zone Bounds & Metadata Inspector**:
  - Attaches helper metadata script/inspector showing zone faction, destruction level, continuous density, and radius.

### 1.4 Faction & Destruction Material Swapping (Weight: 25%)
- [ ] **Theme Parameter Resolution**:
  - Identifies the zone's assigned `faction` (`A`, `B`, `C`) and `destruction` level (`01`, `02`, `03`, `04`).
- [ ] **Material Asset Lookup**:
  - Attempts to assign pre-compiled Synty material assets: `PolygonMilitary_Mat_{destruction}_{faction}.mat`.
- [ ] **Texture Fallback Override**:
  - If standalone material asset is not pre-created, overrides `_MainTex` with `PolygonMilitary_Texture_{destruction}_{faction}.png` and `_BumpMap` with `PolygonMilitary_Texture_01_A_Normals.png`.
- [ ] **Selective Material Preservation**:
  - Recursively updates child `MeshRenderer` and `SkinnedMeshRenderer` components.
  - Leaves non-base materials intact (e.g. `PolygonMilitary_Glass_01`, `PolygonMilitary_Vehicles`, `Decals`).

---

## 2. Quantitative Scoring Matrix

| Score Range | Rating | Acceptance Decision |
|---|---|---|
| **90 – 100** | Exceptional | **PASS (Exceeds V2 Requirements)** |
| **80 – 89** | Proficient | **PASS (Fully Meets V2 Acceptance Criteria)** |
| **70 – 79** | Adequate | **CONDITIONAL PASS (Minor hierarchy/naming cleanup)** |
| **< 70** | Deficient | **FAIL (Must resolve blocking issues)** |

---

## 3. Anti-Patterns & Automatic Disqualifications
- ❌ Using default 16-bit index buffers (`IndexFormat.UInt16`) causing mesh truncation or crash on >65k vertex meshes.
- ❌ Using `Object.Instantiate()` instead of `PrefabUtility.InstantiatePrefab()` in Editor mode.
- ❌ Inverted triangle winding causing the adaptive mesh to render inside-out / culled from top views.
- ❌ Hardcoded absolute file paths (must use relative `Assets/...` paths or `EditorUtility.OpenFilePanel`).
- ❌ Overwriting glass, foliage, or vehicle materials with base building textures.
