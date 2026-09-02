# WorldGen V2 Backend Technical Survey & Architectural Recommendation Report

## 1. Observation

### 1.1 Codebase Structure & Component Inventory
The backend is a high-performance procedural generation engine built with FastAPI, NumPy, Numba JIT, Pydantic V2, and Pillow, managed via `uv`.

| File | Primary Functions / Classes | Current Responsibilities |
|---|---|---|
| `backend/app/generator/terrain.py` | `generate_terrain`, `domain_warped_fbm`, `fbm_2d`, `perlin_noise_2d`, `_fade`, `_grad` | Generates 2D procedural heightmaps using vectorized 2D Perlin gradient noise, multi-octave FBM, 2-stage chained domain warping, and exponential power redistribution ($\gamma = 1.3$). |
| `backend/app/generator/erosion.py` | `simulate_hydraulic_erosion`, `_erode_kernel` (Numba `@njit(fastmath=True)`) | Simulates physics-based droplet hydraulic erosion (inertia, velocity, sediment transport, deposition, evaporation) over the heightmap grid. |
| `backend/app/generator/zones.py` | `generate_zones`, `_poisson_disc_sampling`, `generate_zone_footprint_polygon`, `flatten_zone_footprints` | Distributes military compounds via Bridson's 2D Poisson-disc algorithm, perturbs radial footprint boundaries, and flattens terrain plateaus using C1 Hermite smoothstep blending ($w(t) = 3t^2 - 2t^3$). |
| `backend/app/generator/roads.py` | `generate_roads`, `_generate_zone_edges`, `_delaunay_triangulation_2d`, `_find_slope_aware_astar_path`, `_catmull_rom_spline`, `_rdp_simplify_2d` | Computes 2D Delaunay triangulation + EMST + 30% tactical loops, routes least-cost paths via slope-penalized A* pathfinding, simplifies with RDP, and smooths with Catmull-Rom splines. |
| `backend/app/generator/buildings.py` | `place_buildings`, `OBB2D`, `check_sat_overlap`, `load_asset_catalog`, `_sample_height_corners` | Places HQ buildings and secondary structures inside flattened zones, guaranteeing non-overlapping footprints via 2D Separating Axis Theorem (SAT) Oriented Bounding Box collision detection. |
| `backend/app/generator/pipeline.py` | `generate_world_pipeline` | Orchestrates end-to-end procedural generation: Terrain -> Erosion -> Zones -> Flattening -> Buildings -> Roads -> Constructs `WorldManifest`. |
| `backend/app/api/routes.py` | `/generate`, `/manifest`, `/catalog`, `/catalog/prefabs/{name}`, `/heightmap/png`, `/heightmap/raw`, `/health` | Exposes REST endpoints, in-memory seed caching, and 16-bit PNG / 32-bit float raw heightmap binary export streams. |
| `backend/app/core/schemas.py` | `TerrainConfig`, `ZoneConfig`, `GenerateWorldRequest`, `WorldManifest`, `TerrainManifest`, `Zone`, `BuildingPlacement`, `RoadSegment` | Pydantic V2 models defining request/response structures and `world_manifest.json` schema contracts. |
| `tests/` | `test_generator.py`, `test_manifest_schema.py`, `test_e2e_pipeline.py`, `test_adversarial_backend.py`, `conftest.py` | Test harness with 285 passing tests covering mathematical determinism, physics stability, schema validation, SAT collision freedom, and API stress. |

---

## 2. Logic Chain & Architectural Recommendations for WorldGen V2

### 2.1 R1: Global Map Parameters & Smooth Terrain Deformation

#### Observations & Limitations in Current Code
1. **Map Dimensions**: `TerrainConfig.world_size` is currently fixed in meters `[1000.0, 150.0, 1000.0]`. There is no direct km input abstraction (e.g. `1.0 km` to `10.0 km`), nor automatic grid cell scaling.
2. **Granularity**: Resolution is configurable (`resolution: int = 513`), but defaults to fixed values without an explicit granularity step model for UI binding.
3. **Deformation Strength**: The terrain generator uses fixed parameters for domain warping (`domain_warp_strength: 35.0`) and power redistribution (`1.3`). There is no single master `deformation_strength` slider that proportionally modulates vertical relief, octaves, and warp intensity.
4. **Edge Margin Offset**: Zone generation in `backend/app/generator/zones.py:215` hardcodes `margin=max(60.0, zone_config.max_radius + 20.0)`. Users cannot specify an edge buffer parameter to constrain military installations away from map borders.
5. **Zone Flattening Transition**: `flatten_zone_footprints` (lines 334-339) uses a fixed Hermite smoothstep $w(t) = 3t^2 - 2t^3$ over a narrow outer ring ($R_{\text{outer}} = R_{\text{inner}} \times 1.45$). On steep mountain slopes, this $1.45\times$ transition window can create steep cliff ledges around compound perimeters.

#### Proposed Architecture & Implementation Plan for R1
1. **Schema Enhancements (`backend/app/core/schemas.py`)**:
   - Add `map_width_km: Optional[float] = Field(None, ge=0.5, le=10.0, description="Map width in kilometers")`
   - Add `map_length_km: Optional[float] = Field(None, ge=0.5, le=10.0, description="Map length in kilometers")`
   - Add `edge_margin: float = Field(80.0, ge=0.0, le=1000.0, description="Minimum distance in meters from world boundaries for zone placement")`
   - Add `deformation_strength: float = Field(1.0, ge=0.0, le=5.0, description="Global terrain deformation and relief multiplier")`
   - Add `flattening_falloff: str = Field("cosine", description="Interpolation function for zone plateaus: 'cosine', 'cubic', 'smootherstep'")`
   - Add `flattening_margin_ratio: float = Field(0.65, ge=0.1, le=2.0, description="Width ratio of outer transition blend ring")`
   - Ensure backward compatibility: If `map_width_km` is provided, compute `world_size = [map_width_km * 1000.0, height_scale, map_length_km * 1000.0]`.

2. **Terrain Deformation Scaling (`backend/app/generator/terrain.py`)**:
   - In `generate_terrain()`, scale `warp_strength = config.domain_warp_strength * config.deformation_strength` and apply dynamic octave persistence adjustment:
     $$\text{effective\_persistence} = \text{clip}(\text{config.persistence} \times (0.8 + 0.2 \times \text{deformation\_strength}), 0.1, 0.95)$$

3. **Smooth Zone Plateau Falloff (`backend/app/generator/zones.py`)**:
   - In `flatten_zone_footprints()`, compute:
     $$R_{\text{outer}} = R_{\text{inner}} \times (1.0 + \text{flattening\_margin\_ratio})$$
   - Implement selectable smooth interpolation functions:
     - **Cosine Falloff (C1 Continuous)**:
       $$w(t) = 0.5 \times (1.0 - \cos(\pi \cdot t))$$
     - **Smootherstep (C2 Continuous Quintic)**:
       $$w(t) = t^3 \cdot (t \cdot (6t - 15) + 10)$$
     - **Cubic Smoothstep**:
       $$w(t) = 3t^2 - 2t^3$$
   - This completely eliminates slope discontinuity artifacts and prevents near-vertical cliff generation at compound perimeters.

---

### 2.2 R3: Backend Adaptive Mesh Decimation & Configurable Road Slope Limit

#### 2.2.1 Backend Mesh Decimation with Variable Triangle Density

#### Problem & Design Goal
A uniform heightmap grid at $513 \times 513$ generates $512 \times 512 \times 2 = 524,288$ triangles, regardless of whether the terrain is flat desert plains or jagged mountains.
**Requirement R3**: The backend must decimate the mesh into variable-sized triangles/quads (large polygons on flat areas, high-density polygons on steep slopes and compound zones), sending this optimized indexed mesh structure in `world_manifest.json` to both Three.js and Unity.

#### Algorithmic Strategy: Slope-Adaptive Curvature Sampling + Constrained 2D Delaunay Triangulation
Rather than running expensive 3D quadric error decimation on the full grid, we can implement an ultra-fast, robust, 2D curvature/slope-adaptive quadtree/Delaunay meshing algorithm in NumPy/SciPy:

1. **Step 1: Compute Terrain Slope & Curvature Fields**:
   - Calculate surface normal gradients $G_x = \frac{\partial h}{\partial x}$, $G_z = \frac{\partial h}{\partial z}$, and gradient magnitude $|\nabla h| = \sqrt{G_x^2 + G_z^2}$.
   - Compute Laplacian curvature $C = \left|\frac{\partial^2 h}{\partial x^2} + \frac{\partial^2 h}{\partial z^2}\right|$.
   - Define a local detail metric:
     $$D(x, z) = \alpha \cdot \frac{|\nabla h|}{G_{\text{max}}} + \beta \cdot \frac{C}{C_{\text{max}}} + \gamma \cdot \text{ZoneMask}(x, z)$$

2. **Step 2: Non-Uniform Adaptive Grid Sampling**:
   - **Boundary Anchors**: Always sample full boundary perimeter points $(x=0, x=W, z=0, z=L)$ at regular intervals to ensure watertight world boundaries.
   - **Critical Feature Anchors**: Sample all zone centers, zone footprint perimeter points, building anchor points, and road waypoints.
   - **Adaptive Interior Sampling**:
     - On flat plains ($D(x, z) < 0.15$): Sample every $8^{\text{th}}$ or $16^{\text{th}}$ grid cell (large triangles).
     - On moderate rolling hills ($0.15 \le D(x, z) < 0.50$): Sample every $4^{\text{th}}$ grid cell.
     - On steep cliffs and zone borders ($D(x, z) \ge 0.50$): Sample every $1^{\text{st}}$ or $2^{\text{nd}}$ grid cell.

3. **Step 3: Triangulation & Vertex Assembly**:
   - Run 2D Delaunay triangulation using `scipy.spatial.Delaunay` on the sampled 2D $(x, z)$ coordinates.
   - For every sampled vertex index, query the precise elevation $y = \text{heightmap}[z, x]$ (or bilinear sample).
   - Generate vertex buffer `vertices = [[x_0, y_0, z_0], [x_1, y_1, z_1], ...]` and index buffer `indices = [i_0, i_1, i_2, ...]`.
   - Compute decimation statistics:
     - `vertex_count`, `triangle_count`, `decimation_ratio = triangle_count / (2 * (res - 1)^2)`.

4. **Schema Update (`backend/app/core/schemas.py`)**:
   ```python
   class DecimatedMesh(BaseModel):
       vertices: List[List[float]]   # [[x, y, z], ...]
       indices: List[int]             # Flat triangle index array [0, 1, 2, ...]
       vertex_count: int
       triangle_count: int
       decimation_ratio: float

   class TerrainManifest(BaseModel):
       resolution: Union[int, List[int]] = 513
       world_size: List[float] = Field(default_factory=lambda: [1000.0, 150.0, 1000.0])
       heightmap: Optional[List[List[float]]] = None  # Preserved for backward compatibility
       mesh: Optional[DecimatedMesh] = None           # New adaptive decimated mesh
   ```

5. **Client Interoperability**:
   - **Frontend (Three.js)**: `TerrainVisualizer` can immediately instantiate `new THREE.BufferGeometry()` setting `position` attribute from `mesh.vertices` and `setIndex(mesh.indices)`, computing vertex normals with `geometry.computeVertexNormals()`.
   - **Unity Importer**: `WorldManifestImporter.cs` can build a Unity `Mesh` and attach to a `MeshFilter` / `MeshRenderer` / `MeshCollider`, while retaining the option to build Unity `TerrainData` from `heightmap`.

---

#### 2.2.2 Configurable `max_road_slope` in A* Pathfinding

#### Observations in Current Code
In `backend/app/generator/roads.py:193-198`:
- `max_grade` is currently hardcoded to `0.25` (25% slope).
- When `grade > max_grade`, it adds a penalty `1000.0 * (grade - max_grade)`, but does not strictly reject paths exceeding the slope limit, which can cause paths to traverse steep cliffs if the heuristic pulls them.

#### Implementation Plan
1. **Parameter Integration**:
   - Add `max_road_slope: float = Field(0.20, ge=0.05, le=1.0)` to `RoadConfig`, `TerrainConfig`, and `GenerateWorldRequest`.
   - Pass `max_road_slope` to `generate_roads()` and `_find_slope_aware_astar_path()`.

2. **Strict A* Constraint Enforcement**:
   - In `_find_slope_aware_astar_path`:
     ```python
     grade = abs(next_h - cur_h) / max(1e-4, step_dist)
     if grade > max_road_slope:
         # Hard barrier: Cannot climb steeper than max_road_slope
         continue
     ```
   - **Graceful Switchback / Valley Routing**:
     Because 8-connected diagonal and cardinal moves allow lateral traverses, A* will automatically contour around steep peaks and seek natural valley passes.
   - **Fallback Relaxation**:
     If no path exists under `max_road_slope` (e.g. zone placed on an isolated vertical mesa), dynamically relax the search with a quadratic barrier penalty:
     $$P(\text{grade}) = 1.0 + 20 \cdot \text{grade}^2 + 10000 \cdot \max(0.0, \text{grade} - \text{max\_road\_slope})^2$$
   - **Post-Spline Clamping Verification**:
     After Catmull-Rom spline interpolation, verify and clamp waypoint elevations so that no adjacent waypoint step exceeds $\text{max\_road\_slope} \times 1.05$.

---

### 2.3 R4: Continuous Density Slider & AI Layout Templates

#### Observations in Current Code
1. `Zone.density` is an enum string (`"low"`, `"medium"`, `"high"`).
2. `place_buildings()` randomly selects assets from categorized catalog lists (`command_hqs`, `support_structures`, `defenses_and_props`) using simple uniform random choices and random angle/distance distributions.

#### Implementation Plan
1. **Continuous Density Slider Schema**:
   - Update `Zone.density` in `backend/app/core/schemas.py` to `Union[float, str] = 0.5`.
   - Add a normalization helper:
     ```python
     def get_numeric_density(density: Union[float, str]) -> float:
         if isinstance(density, (int, float)):
             return float(np.clip(density, 0.0, 1.0))
         mapping = {"low": 0.25, "medium": 0.5, "high": 0.85}
         return mapping.get(str(density).lower(), 0.5)
     ```
   - Target building count scales smoothly with density:
     $$\text{target\_count} = \text{int}(\text{round}(4 + \text{density} \times 22))$$

2. **Offline JSON Layout Templates Structure**:
   - Create template files in `backend/app/generator/templates/`:
     - `military_base.json` (Central command bunker, motor pool, barracks rows, perimeter watchtowers, sandbag defense ring).
     - `outpost.json` (Watchtower center, small communications tent, generator, defensive barricades).
     - `airfield.json` (Hangar structures, fuel bladders, cargo crates, logistics trucks).
     - `depot.json` (Grid-aligned storage containers, supply crates, water tanks, perimeter fencing).
     - `radar_station.json` (Central radar dish/tower, generator shack, perimeter security).

3. **Template Format Specification**:
   ```json
   {
     "zone_type": "military_base",
     "name": "Fortified Military Base Template",
     "layout_rules": [
       {
         "role": "command_hq",
         "priority": 1,
         "min_density": 0.0,
         "relative_position": [0.0, 0.0],
         "allowed_prefabs": ["SM_Bld_Village_House_01", "SM_Bld_Tent_01"],
         "yaw_mode": "fixed_or_radial",
         "yaw_offset_deg": 0.0
       },
       {
         "role": "perimeter_towers",
         "priority": 2,
         "min_density": 0.3,
         "radial_distribution": {
           "radius_ratio": 0.75,
           "count_formula": "round(3 + density * 3)",
           "allowed_prefabs": ["SM_Bld_Watchtower_01", "SM_Bld_Village_House_Tower_01"]
         }
       },
       {
         "role": "barracks_cluster",
         "priority": 2,
         "min_density": 0.2,
         "grid_layout": {
           "rows": 2,
           "cols": 3,
           "spacing": [12.0, 8.0],
           "allowed_prefabs": ["SM_Bld_Tent_01", "SM_Bld_Tent_Desert_01"]
         }
       },
       {
         "role": "defensive_perimeter",
         "priority": 3,
         "min_density": 0.5,
         "scatter_around": "perimeter_towers",
         "allowed_prefabs": ["SM_Prop_Sandbags_01", "SM_Prop_Sandbag_01"]
       },
       {
         "role": "logistics_and_props",
         "priority": 4,
         "min_density": 0.4,
         "allowed_prefabs": ["SM_Prop_Crate_Military_01", "SM_Prop_Generator_01", "SM_Veh_Truck_Military_01"]
       }
     ]
   }
   ```

4. **Template Execution with SAT Collision Verification**:
   - `place_buildings()` parses the zone's layout template, instantiating items based on whether `zone.density >= rule.min_density`.
   - Every candidate placement is transformed from local zone space to world space:
     $$\mathbf{P}_{\text{world}} = \mathbf{P}_{\text{zone\_center}} + \mathbf{R}(\theta) \cdot \mathbf{P}_{\text{local}}$$
   - Before final placement, SAT collision checking (`check_sat_overlap`) is performed against all previously placed OBBs, guaranteeing zero building collisions.

---

### 2.4 R2 & Interactive Zone Recomputation Architecture

To support interactive zone dragging and editing in the frontend:
1. **Endpoint Enhancement (`POST /api/v1/generate`)**:
   - Allow passing existing `zones` array in `GenerateWorldRequest`. If explicit zone positions/radii/factions are passed, the backend skips Poisson-disc generation and directly uses the provided zones.
   - Run Terrain Flattening -> Building Layout -> Road Routing on the updated zones in $< 150\text{ms}$.
2. **Dedicated Fast Recomputation Endpoint (`POST /api/v1/zones/recompute`)**:
   - Accepts current heightmap + updated zones list.
   - Returns updated `manifest.zones`, `manifest.buildings`, `manifest.roads`, and decimated `manifest.terrain.mesh`.

---

## 3. Caveats & Risk Analysis

| Risk Area | Potential Issue | Mitigation Strategy |
|---|---|---|
| **Large Map Scale (10 km)** | Heightmap array at 10km with 513 res means cell size $\approx 19.5\text{m}$. Tiny props could have elevation aliasing. | Support resolution slider up to 1025 or use bilinear continuous elevation sampling in `_sample_height_corners`. |
| **Mesh Decimation Boundaries** | Decimated mesh edges might not be strictly rectangular if Delaunay is unconstrained. | Always inject fixed boundary coordinates along the 4 map edges into the Delaunay point set. |
| **A* Road Routing on Steep Cliffs** | Very low `max_road_slope` (e.g. 0.08) might fail to find a path between distant high/low zones. | Implement soft barrier fallback with warning in manifest metadata, or recommend switchback waypoints. |
| **Template Fallback** | If a prefab in a template is not in `catalog.json`. | Include robust fallback mapping to default synthetic catalog and generic replacement roles. |

---

## 4. Conclusion & Implementation Plan

### Recommended Step-by-Step Implementation for Implementer Agent:
1. **Step 1: Core Schemas & Config (`backend/app/core/schemas.py`)**:
   - Add `DecimatedMesh` model to `TerrainManifest`.
   - Add `map_width_km`, `map_length_km`, `edge_margin`, `deformation_strength`, `flattening_falloff`, `flattening_margin_ratio`, `max_road_slope` to `TerrainConfig` and `GenerateWorldRequest`.
   - Update `Zone.density` to support float values.
2. **Step 2: Terrain & Zone Generators (`terrain.py`, `zones.py`)**:
   - Implement `deformation_strength` scaling in `generate_terrain()`.
   - Implement Cosine and Smootherstep C2 falloff in `flatten_zone_footprints()`.
   - Apply `edge_margin` in `_poisson_disc_sampling()`.
3. **Step 3: Adaptive Mesh Decimation Generator (`backend/app/generator/mesh.py`)**:
   - Create `generate_adaptive_terrain_mesh(heightmap, terrain_config, zones)` implementing curvature-based point sampling and 2D Delaunay triangulation.
   - Integrate into `generate_world_pipeline()`.
4. **Step 4: Road Slope Limit (`roads.py`)**:
   - Integrate `max_road_slope` into `_find_slope_aware_astar_path()` and spline validation.
5. **Step 5: AI-Driven Layout Templates (`buildings.py` & `templates/`)**:
   - Create JSON layout template files for 5 zone types.
   - Update `place_buildings()` to execute priority-driven template placement with continuous density scaling and SAT OBB verification.
6. **Step 6: Programmatic Test Suite Expansion (`tests/`)**:
   - Add unit and E2E tests for dimensions scaling, mesh indices validation, road slope limit verification, and template-based building allocation.

---

## 5. Verification Method

To independently verify the implementation:

1. **Run Full Test Suite via uv**:
   ```bash
   uv run --project backend pytest tests/ -v
   ```
2. **Verify Map Dimensions & Mesh Indices**:
   - Assert `manifest.terrain.mesh.vertices` coordinate ranges match `[0.0, map_width_km * 1000.0]`.
   - Assert all indices in `manifest.terrain.mesh.indices` are valid $< \text{len}(\text{vertices})$.
   - Assert flat terrain produces $\ge 60\%$ fewer triangles than full grid.
3. **Verify `max_road_slope` Adherence**:
   - Run tests with `max_road_slope=0.15` and assert:
     $$\forall k, \quad \frac{|y_{k+1} - y_k|}{\sqrt{(x_{k+1}-x_k)^2 + (z_{k+1}-z_k)^2}} \le 0.16$$
4. **Verify Schema Validation**:
   - Run `python tests/validate_catalog.py` and manifest schema tests.
