# Unity Importer Review Rubric (R4: C# Editor Package & Material Swapper)

## Objective
This Agent-as-Judge rubric evaluates the implementation quality, C# architectural rigor, Unity Editor API compliance, asset linkage preservation, and material swapping accuracy for **Requirement R4: Unity Importer Package (C#)**.

---

## 1. Evaluation Dimensions & Checklists

### 1.1 Unity Terrain Instantiation & SetHeights (Weight: 25%)
- [ ] **TerrainData Configuration**:
  - Constructs `TerrainData` and configures `heightmapResolution` to match manifest resolution ($2^n + 1$ compliance, e.g. 129, 257, 513).
  - Sets `terrainData.size = new Vector3(manifest.terrain.world_size[0], manifest.terrain.world_size[1], manifest.terrain.world_size[2])`.
- [ ] **Height Normalization & Transposition**:
  - Populates heights using `TerrainData.SetHeights(0, 0, heights2D)`.
  - Normalizes heights strictly into the $[0.0, 1.0]$ range (`Mathf.Clamp01(h / height_scale)`).
  - Handles 2D array indexing correctly ($[z, x]$ ordering expected by Unity).
- [ ] **Terrain GameObject**:
  - Creates active `Terrain` GameObject with attached `TerrainCollider` and assigned `TerrainData`.

### 1.2 Prefab Spawning via PrefabUtility (Weight: 25%)
- [ ] **Editor Link Preservation**:
  - **MANDATORY**: Uses `PrefabUtility.InstantiatePrefab(prefabAsset, parentTransform)` when executed in the Editor to ensure instantiated GameObjects maintain live links to the project's source Prefabs.
  - **FORBIDDEN IN EDITOR**: Using plain `Object.Instantiate` or `GameObject.Instantiate` (which breaks prefab connection and converts prefabs to plain GameObjects).
- [ ] **Asset Resolution & Missing Asset Fallback**:
  - Indexes prefabs in `Assets/PolygonMilitary/Prefabs` via `AssetDatabase.FindAssets("t:Prefab")`.
  - If a prefab is missing, instantiates a fallback primitive Cube proxy with matching bounding box dimensions and logs a descriptive warning.
- [ ] **Transform Application**:
  - Accurately applies `position`, `rotation` (Quaternion or Euler), and `localScale` matching `world_manifest.json`.

### 1.3 Faction & Destruction Material / Texture Swapping (Weight: 25%)
- [ ] **Theme Parameter Resolution**:
  - Identifies the zone's assigned `faction` (`A`, `B`, `C`) and `destruction` level (`01`, `02`, `03`, `04`).
- [ ] **Material Asset Lookup**:
  - Attempts to assign pre-compiled Synty material assets: `PolygonMilitary_Mat_{destruction}_{faction}.mat`.
- [ ] **Texture Fallback Override**:
  - If standalone material asset is not pre-created, overrides `_MainTex` with `PolygonMilitary_Texture_{destruction}_{faction}.png` and `_BumpMap` with `PolygonMilitary_Texture_01_A_Normals.png`.
- [ ] **Selective Material Preservation**:
  - Recursively updates all child `MeshRenderer` and `SkinnedMeshRenderer` components.
  - Leaves non-base materials intact (e.g., `PolygonMilitary_Glass_01`, `PolygonMilitary_Vehicles`, `Decals`).

### 1.4 Hierarchy Organization & Editor UX (Weight: 25%)
- [ ] **Clean Scene Hierarchy**:
  - Groups all generated objects under a clean root GameObject: `[WorldGen_Output]`.
  - Sub-parents organized logically:
    ```
    [WorldGen_Output]
    ├── Terrain
    ├── Roads
    └── Zones
        ├── Zone_0_FactionA_Destruction01
        └── Zone_1_FactionB_Destruction03
    ```
- [ ] **Editor Menu & Window**:
  - Accessible via `[MenuItem("WorldGen/Import Manifest...")]`.
  - Editor window allows selecting `world_manifest.json` file path and prefab search root directory.
- [ ] **Undo Integration**:
  - Registers all created GameObjects with Unity's Undo stack using `Undo.RegisterCreatedObjectUndo(instance, "Import WorldGen Manifest")`.

---

## 2. Quantitative Scoring Matrix

| Score Range | Rating | Acceptance Decision |
|---|---|---|
| **90 – 100** | Exceptional | **PASS (Exceeds Requirements)** |
| **80 – 89** | Proficient | **PASS (Fully Meets Acceptance Criteria)** |
| **70 – 79** | Adequate | **CONDITIONAL PASS (Minor naming/hierarchy cleanup)** |
| **< 70** | Deficient | **FAIL (Must resolve blocking issues)** |

---

## 3. Anti-Patterns & Automatic Disqualifications
- ❌ Using `Object.Instantiate()` instead of `PrefabUtility.InstantiatePrefab()` in Editor mode.
- ❌ Hardcoded absolute file paths (must use relative `Assets/...` paths or `EditorUtility.OpenFilePanel`).
- ❌ Passing non-normalized (>1.0) heights to `TerrainData.SetHeights()`.
- ❌ Overwriting glass or vehicle materials with base building textures.
