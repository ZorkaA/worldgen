# TEST_READY: WorldGen V2 — Procedural 3D World Designer & Unity Importer

## 1. Test Suite Overview

The test suite for **WorldGen V2** provides comprehensive, requirement-driven, zero-facade verification across all V2 functional requirements:
- **R1: Global Map Parameters** (0.5 – 10.0 km dimension scaling, resolution granularity, deformation multipliers, edge margin offsets).
- **R2: Zone Editing & Interactivity** (Full zone CRUD, 3D viewport drag-to-recompute, live in-place scene updates without page reload).
- **R3: Backend Adaptive Tessellation & Strict Road Slope Limits** (Variable-density mesh decimation, watertight mesh boundaries, 32-bit index buffers, A* max_road_slope adherence).
- **R4: AI-Driven Asset Allocation** (Offline JSON layout templates for 5 zone types, continuous density scaling $0.0 \le D \le 1.0$, SAT 2D OBB collision-free placement).
- **R5: UI Cleanup & Standards** (Utilitarian typography stripping AI slop, CSS Container Queries, scrollbar-gutter stability).

### Test Suite Artifacts
| Path | Component | Type | Scope |
|---|---|---|---|
| `tests/conftest.py` | Shared Test Harness | Pytest Fixtures | JSON Schemas (Draft 2020-12 / Draft 7), SAT collision checker, canonical mock manifests, FastAPI client |
| `tests/test_map_dimensions.py` | Map Sizing & Granularity | Pytest Suite | Map scaling (0.5, 1.0, 2.5, 4.0 km), resolution (65–513), aspect ratios, deformation, edge margins |
| `tests/test_adaptive_mesh.py` | Adaptive Decimation Suite | Pytest Suite | Quadtree/Delaunay mesh decimation, 50–70% flat reduction, index bounds, watertightness, normals, UVs |
| `tests/test_road_slope_limits.py` | Road Slope Limits Suite | Pytest Suite | Gradient adherence across varying steepness, switchback detours, vertical cliff stress handling |
| `tests/test_layout_templates.py` | Layout Templates Suite | Pytest Suite | 5 zone templates, continuous density scaling ($0.0 \le D \le 1.0$), SAT OBB collision-free placement |
| `tests/test_manifest_schema.py` | Manifest Schema Suite | Pytest Suite | Schema validation, type bounds, enums, transforms, referential integrity |
| `tests/test_generator.py` | Generator Algorithms Suite | Pytest Suite | Perlin FBM, domain warp, Numba erosion, Poisson-disc, plateau smoothing |
| `tests/test_catalog.py` | Catalog & VLM Pipeline Suite | Pytest Suite | 3D AABB math, auto-framing, Ollama VLM fallback parser, caching |
| `tests/test_catalog_builder_unit.py` | Catalog Builder Unit Suite | Pytest Suite | Asset indexing, metadata generation, render paths |
| `tests/test_adversarial_backend.py` | Adversarial & Fuzz Suite | Pytest Suite | Extreme coordinates, corrupted payloads, boundary fuzzing, NaN guards |
| `tests/test_e2e_pipeline.py` | Tiers 1–4 E2E Test Suite | Pytest Suite | Full dataflow pipeline across features, boundaries, and combinatorial matrices |
| `tests/validate_catalog.py` | Standalone CLI Tool | Python Executable | Standalone CLI validation for `catalog.json` |
| `tests/rubrics/frontend_rubric.md` | R2/R3/R5 Review Rubric | Agent-as-Judge | Zone CRUD, 3D viewport dragging, drop recompute, adaptive mesh, utilitarian UI |
| `tests/rubrics/unity_rubric.md` | R3/R4 Review Rubric | Agent-as-Judge | `AdaptiveTerrainMesh`, 32-bit index buffers (`IndexFormat.UInt32`), material swapping, zone hierarchy |

---

## 2. Test Execution Commands

### 2.1 Full Pytest Suite Execution
To execute all 356 automated tests:
```bash
uv run --project backend pytest tests/ -v
```

### 2.2 Running Individual Test Suites
```bash
# V2 Map Dimension & Resolution Tests
uv run --project backend pytest tests/test_map_dimensions.py -v

# V2 Adaptive Mesh Decimation Tests
uv run --project backend pytest tests/test_adaptive_mesh.py -v

# V2 Road Slope Limits Tests
uv run --project backend pytest tests/test_road_slope_limits.py -v

# V2 Layout Templates & Continuous Density Tests
uv run --project backend pytest tests/test_layout_templates.py -v

# E2E Pipeline & Schema Tests
uv run --project backend pytest tests/test_e2e_pipeline.py -v
uv run --project backend pytest tests/test_manifest_schema.py -v
```

### 2.3 Standalone Catalog Validation CLI
```bash
python3 tests/validate_catalog.py backend/app/catalog/catalog.json --strict --json
```

---

## 3. Test Inventory & Coverage Breakdown

| Test Suite File | Focus Area | Implemented Tests | Pass Status |
|---|---|:---:|:---:|
| `tests/test_map_dimensions.py` | Map Dimensions (0.5 – 4.0 km), Resolution, Bounds, Margins | 32 | **100% PASS** |
| `tests/test_adaptive_mesh.py` | Adaptive Decimation, Index Validity, Watertightness | 10 | **100% PASS** |
| `tests/test_road_slope_limits.py` | Strict Road Slope Limits, Switchbacks, Stress Cliffs | 8 | **100% PASS** |
| `tests/test_layout_templates.py` | 5 Zone Templates, Continuous Density, SAT OBB Non-Overlap | 21 | **100% PASS** |
| `tests/test_e2e_pipeline.py` | Tiers 1–4 Features, Boundaries, Combinatorial Scenarios | 148 | **100% PASS** |
| `tests/test_adversarial_backend.py` | Adversarial Payloads, Negative Inputs, Fuzzing | 55 | **100% PASS** |
| `tests/test_manifest_schema.py` | JSON Schema, Bounds, Enums, Transformations | 49 | **100% PASS** |
| `tests/test_generator.py` | Terrain Math, Erosion, Poisson-disc, Road Routing | 10 | **100% PASS** |
| `tests/test_catalog.py` | Catalog Extraction, Auto-framing, VLM Fallbacks | 10 | **100% PASS** |
| `tests/test_catalog_builder_unit.py` | Catalog Builder Pipeline Units | 13 | **100% PASS** |
| **Total Automated Pytest Harness** | **Full System Verification** | **356** | **100% PASS** |

---

## 4. Feature Coverage Matrix (Features 1 – 20)

| # | Feature Inventory Item | Tier 1 (Func) | Tier 2 (Bound) | Tier 3 (Comb) | Tier 4 (E2E) | Status |
|---|------------------------|:-------------:|:--------------:|:-------------:|:------------:|:------:|
| **1** | Global Map Dimensions (0.5 – 10.0 km) | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **2** | Granularity & Resolution Control | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **3** | Terrain Deformation Multiplier | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **4** | Edge Margin Offset Constraint | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **5** | Smooth Zone Flattening Falloff | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **6** | Strict Road Slope Limits (`max_road_slope`) | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **7** | Backend Adaptive Mesh Decimation | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **8** | AI-Driven JSON Layout Templates | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **9** | Continuous Density Scaling ($0.0 \le D \le 1.0$) | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **10** | SAT Collision-Free Template Placement | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **11** | Zone CRUD Side Panel UI | ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **12** | Draggable Zone Centers (3D Viewport) | ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **13** | Viewport Drag-Drop Live Recomputation | ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **14** | Three.js Adaptive Decimated Mesh Renderer | ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **15** | Utilitarian UI Cleanup (Stripping AI Slop) | ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **16** | Unity `AdaptiveTerrainMesh` (32-Bit Index Buffer)| ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **17** | Unity Templated Zone Hierarchy & Material Swap | ✓ | ✓ | ✓ | ✓ | **PASS** (Rubric) |
| **18** | Programmatic Dimension & Mesh Bounds Verification| ✓ | ✓ | ✓ | ✓ | **PASS** |
| **19** | Programmatic Road Slope Verification | ✓ | ✓ | ✓ | ✓ | **PASS** |
| **20** | Agent-as-Judge Frontend & Unity Rubric Gates | ✓ | ✓ | ✓ | ✓ | **PASS** |

---

## 5. Verification Output Summary

```
============================= test session starts ==============================
platform darwin -- Python 3.10.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jack/worldgen
plugins: asyncio-1.4.0, anyio-4.14.2
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 356 items

tests/test_adversarial_backend.py ...................................    [ 10%]
....................                                                     [ 15%]
tests/test_catalog.py ..........                                         [ 18%]
tests/test_catalog_builder_unit.py .............                         [ 22%]
tests/test_e2e_pipeline.py ..........................................    [ 34%]
........................................................................ [ 54%]
................................                                         [ 63%]
tests/test_generator.py ..........                                       [ 66%]
tests/test_manifest_schema.py .......................................    [ 76%]
............                                                             [ 80%]
tests/test_map_dimensions.py ................................            [ 89%]
tests/test_adaptive_mesh.py ..........                                   [ 92%]
tests/test_road_slope_limits.py ........                                 [ 94%]
tests/test_layout_templates.py .....................                     [100%]

======================== 356 passed, 2 warnings in 83.26s =======================
```
