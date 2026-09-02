# E2E Test Infra: WorldGen V2 — Procedural 3D World Designer & Unity Importer

## 1. Test Philosophy & Core Principles

WorldGen V2 implements a strict, requirement-driven, zero-facade test methodology across four core subsystem layers:
- **Opaque-Box Requirement Verification**: Tests evaluate system behavior against documented specifications in `ORIGINAL_REQUEST.md` and interface contracts in `PROJECT.md` without coupling to internal private state.
- **Mathematical & Algorithmic Rigor**: Geometric invariants (Separating Axis Theorem for 2D Oriented Bounding Boxes, Bowyer-Watson Delaunay triangulation, A* slope cost penalties, continuous density monotonicity, mesh decimation ratios) are verified using exact analytical proofs and reference oracles.
- **Progressive Testability & Isolation**: Every test case is self-contained, deterministically seeded, independent of execution order, and operates with explicit expected output derivations.
- **Dual-Track Quality Assurance**:
  1. *Automated Programmatic Pytest Suites* (`tests/`): Executing unit, boundary, combinatorial, and end-to-end integration tests on FastAPI backend, schemas, geometry, and algorithms.
  2. *Agent-as-Judge Review Rubrics* (`tests/rubrics/`): Formal qualitative and architectural verification rubrics for the Three.js interactive visualizer and Unity C# Editor importer.

---

## 2. 4-Tier Test Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│               Tier 4: Real-World Application Scenarios                 │
│  (Multi-km Archipelagos, Mountainous Compounds, Full Pipeline E2E)     │
├────────────────────────────────────────────────────────────────────────┤
│            Tier 3: Pairwise Combinatorial Matrix Testing               │
│  (Map Size × Resolution × Road Slope × Zone Density × Deformation)     │
├────────────────────────────────────────────────────────────────────────┤
│           Tier 2: Boundary Value Analysis & Stress Invariants          │
│  (0.5km - 10km Limits, Sheer Cliffs, D=0.0/1.0, Edge Margins, BBoxes)  │
├────────────────────────────────────────────────────────────────────────┤
│          Tier 1: Feature Functional & Contract Testing (R1-R5)         │
│  (Dimensions, Decimated Meshes, Road Slopes, Layout Templates, CRUD)   │
└────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Feature Functional & Contract Testing
- Validates the primary behavior (happy paths) for every single feature in the inventory.
- Enforces strict JSON Schema compliance for `world_manifest.json` (Draft 2020-12 / Draft 7) and `templates.json`.
- Verifies return types, array dimensions, bounding boxes, coordinate spaces, and API response structures.

### Tier 2: Boundary Value Analysis (BVA) & Limit Stressing
- Evaluates behavior at extreme boundaries: minimum map dimensions ($0.5$ km) and maximum ($10.0$ km); lowest resolution ($17 \times 17$) and high ($1025 \times 1025$).
- Tests continuous density limits ($D = 0.0$ producing minimal core footprints, $D = 1.0$ populating all template slots).
- Tests steep terrain gradients ($0.0 \le \text{max\_road\_slope} \le 1.0$) and verifies boundary preservation in adaptive mesh decimation (watertight mesh skirts and perimeter vertices).
- Tests edge margin constraints to prevent zones from clipping map boundaries.

### Tier 3: Combinatorial & Cross-Feature Interaction Matrix
- Uses pairwise combinatorial orthogonal arrays to test multidimensional parameter interactions:
  * Map Size ($0.5$ km, $1.0$ km, $2.5$ km, $4.0$ km)
  * Grid Resolution ($65$, $129$, $257$, $513$)
  * Road Slope Limit ($0.10$, $0.18$, $0.25$, $0.45$)
  * Zone Density ($0.0$, $0.35$, $0.70$, $1.0$)
  * Terrain Deformation Multiplier ($0.0$, $1.0$, $2.5$)
- Asserts that terrain generation, zone placement, SAT collision checking, road routing, and mesh decimation execute without deadlocks, NaN values, or index out-of-range errors.

### Tier 4: Real-World Application Scenarios
- Realistic, high-complexity military deployment environments exercising end-to-end dataflow from layout generation to frontend rendering and Unity importer ingestion.

---

## 3. Feature Inventory Mapping (R1 – R5)

| # | Feature Inventory Item | Requirement Source | Tier 1 (Func) | Tier 2 (Bound) | Tier 3 (Comb) | Tier 4 (E2E) | Primary Test Suite / Rubric |
|---|------------------------|--------------------|:-------------:|:--------------:|:-------------:|:------------:|-----------------------------|
| **1** | Global Map Dimensions (0.5 – 10.0 km) | V2 R1 | 6 | 6 | ✓ | ✓ | `tests/test_map_dimensions.py` |
| **2** | Granularity & Resolution Control | V2 R1 | 5 | 5 | ✓ | ✓ | `tests/test_map_dimensions.py` |
| **3** | Terrain Deformation Multiplier | V2 R1 | 5 | 5 | ✓ | ✓ | `tests/test_map_dimensions.py` |
| **4** | Edge Margin Offset Constraint | V2 R1 | 5 | 5 | ✓ | ✓ | `tests/test_map_dimensions.py` |
| **5** | Smooth Zone Flattening Falloff | V2 R1 | 5 | 5 | ✓ | ✓ | `tests/test_generator.py` |
| **6** | Strict Road Slope Limits (`max_road_slope`) | V2 R3 | 8 | 8 | ✓ | ✓ | `tests/test_road_slope_limits.py` |
| **7** | Backend Adaptive Mesh Decimation | V2 R3 | 8 | 8 | ✓ | ✓ | `tests/test_adaptive_mesh.py` |
| **8** | AI-Driven JSON Layout Templates | V2 R4 | 8 | 6 | ✓ | ✓ | `tests/test_layout_templates.py` |
| **9** | Continuous Density Scaling ($0.0 \le D \le 1.0$) | V2 R4 | 6 | 6 | ✓ | ✓ | `tests/test_layout_templates.py` |
| **10** | SAT Collision-Free Template Placement | V2 R4 | 6 | 6 | ✓ | ✓ | `tests/test_layout_templates.py` |
| **11** | Zone CRUD Side Panel UI (Add, Remove, Rename) | V2 R2 | 5 | 5 | ✓ | ✓ | `tests/rubrics/frontend_rubric.md` |
| **12** | Draggable Zone Centers (3D Viewport) | V2 R2 | 5 | 5 | ✓ | ✓ | `tests/rubrics/frontend_rubric.md` |
| **13** | Viewport Drag-Drop Live Recomputation | V2 R2 | 5 | 5 | ✓ | ✓ | `tests/rubrics/frontend_rubric.md` |
| **14** | Three.js Adaptive Decimated Mesh Renderer | V2 R3 | 5 | 5 | ✓ | ✓ | `tests/rubrics/frontend_rubric.md` |
| **15** | Utilitarian UI Cleanup (Stripping AI Slop) | V2 R5 | 5 | 5 | ✓ | ✓ | `tests/rubrics/frontend_rubric.md` |
| **16** | Unity `AdaptiveTerrainMesh` (32-Bit Index Buffer)| V2 R3 | 6 | 6 | ✓ | ✓ | `tests/rubrics/unity_rubric.md` |
| **17** | Unity Templated Zone Hierarchy & Material Swap | V2 R4 | 6 | 6 | ✓ | ✓ | `tests/rubrics/unity_rubric.md` |
| **18** | Programmatic Dimension & Mesh Bounds Verification| Acceptance | 6 | 6 | ✓ | ✓ | `tests/test_map_dimensions.py` |
| **19** | Programmatic Road Slope Verification | Acceptance | 6 | 6 | ✓ | ✓ | `tests/test_road_slope_limits.py` |
| **20** | Agent-as-Judge Frontend & Unity Rubric Gates | Acceptance | 5 | 5 | ✓ | ✓ | `tests/rubrics/` |

---

## 4. Test Suites & Execution Architecture

### 4.1 Pytest Test Suite Layout
```
tests/
├── conftest.py                   # Shared fixtures, schemas (V1/V2), SAT math, mock client
├── test_manifest_schema.py       # JSON schema & referential integrity suite
├── test_generator.py             # Perlin FBM, erosion, Poisson zones, basic roads
├── test_catalog.py               # 3D AABB math, auto-framing, Ollama extraction
├── test_catalog_builder_unit.py  # Unit tests for catalog builder pipeline
├── test_map_dimensions.py        # [NEW V2] Sizing (0.5 - 4.0 km), resolution, bounds
├── test_adaptive_mesh.py         # [NEW V2] Decimation ratio, vertex indexing, watertightness
├── test_road_slope_limits.py     # [NEW V2] A* gradient limits across steepness
├── test_layout_templates.py      # [NEW V2] 5 zone templates, continuous density, SAT OBB
├── test_adversarial_backend.py   # Adversarial inputs, fuzzing, corrupt payloads
├── test_e2e_pipeline.py          # Tiers 1-4 end-to-end integration scenarios
├── validate_catalog.py           # Standalone CLI catalog validator
└── rubrics/
    ├── frontend_rubric.md        # [V2] Zone CRUD, drag-recompute, adaptive mesh, UI
    └── unity_rubric.md           # [V2] AdaptiveTerrainMesh, UInt32 indices, hierarchy
```

### 4.2 Standard Execution Commands
- **Full Test Suite**:
  ```bash
  uv run --project backend pytest tests/ -v
  ```
- **New V2 Test Suites**:
  ```bash
  uv run --project backend pytest tests/test_map_dimensions.py -v
  uv run --project backend pytest tests/test_adaptive_mesh.py -v
  uv run --project backend pytest tests/test_road_slope_limits.py -v
  uv run --project backend pytest tests/test_layout_templates.py -v
  ```
- **Catalog Validator CLI**:
  ```bash
  python3 tests/validate_catalog.py backend/app/catalog/catalog.json --strict --json
  ```

---

## 5. Real-World Application Scenarios (Tier 4)

| Scenario | Description | Features Tested | Expected Outcome |
|---|---|---|---|
| **Scenario 1: Massive Tactical Operations Base (4.0 km)** | Ultra-large 4.0 km world with resolution 513, 8 sprawling military bases, continuous density $D = 0.85$, and multi-zone road loops. | 1, 2, 8, 9, 10, 14, 16 | Accurate 4000m coordinate bounds, zero SAT collisions, verified mesh bounds. |
| **Scenario 2: Mountainous Radar Ridge with Strict Slope Limits** | Steep volcanic/mountainous terrain with $\text{max\_road\_slope} = 0.15$ connecting high-altitude radar stations to lowland valley depots. | 3, 5, 6, 7, 8, 19 | Roads route via gentle contour switchbacks; max observed slope $\le 0.15$. |
| **Scenario 3: Island Archipelago with Decimated Waterline Plains** | Island chain featuring extensive flat plains and sea-level terrain surrounded by rugged peaks. | 1, 3, 7, 14, 16 | Flat plains achieve $\ge 50\%$ mesh decimation; rugged peaks retain fine geometry. |
| **Scenario 4: Compact Forward Operating Outpost (0.5 km)** | Ultra-dense 500m map with 4 close-quarter outposts, minimum edge margin offsets, and density $D = 1.0$. | 1, 4, 8, 9, 10 | All buildings stay within zone radius and map bounds without clipping. |
| **Scenario 5: Interactive Drag-and-Drop Live Recompute Pipeline** | Moving zone center coordinate from $(250, 300)$ to $(750, 800)$ triggering live terrain flattening, road re-routing, and templated asset re-population. | 1, 5, 6, 8, 12, 13 | Smooth plateau falloff at new center, roads dynamically reconnect, zero page reload. |

---

## 6. Coverage Thresholds & Quality Gates

| Metric | Threshold | Verification Method |
|---|---|---|
| **Tier 1 (Feature Functional)** | $\ge 100$ test cases | Automated Pytest run |
| **Tier 2 (Boundary & Limits)** | $\ge 100$ test cases | Automated Pytest run with edge inputs |
| **Tier 3 (Combinatorial Matrix)** | $\ge 25$ test cases | Parametric pairwise matrix test |
| **Tier 4 (Real-World Scenarios)** | $\ge 5$ end-to-end scenarios | Full multi-module pipeline execution |
| **Total Test Count** | **$\ge 300$ test assertions** | Aggregated `pytest` suite |
| **Pass Rate Target** | **100%** | Zero failures, zero unexpected skips |
| **Frontend Agent-as-Judge Score** | $\ge 85 / 100$ | `tests/rubrics/frontend_rubric.md` |
| **Unity Importer Agent-as-Judge Score**| $\ge 85 / 100$ | `tests/rubrics/unity_rubric.md` |
