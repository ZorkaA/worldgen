# E2E Test Infra: Procedural 3D Military World Designer

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.

## Feature Inventory Mapping
| # | Feature | Requirement Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|-------------------|:------:|:------:|:------:|:------:|
| 1 | Asset Catalog Bounding Boxes | ORIGINAL_REQUEST § R1 | 5 | 5 | ✓ | ✓ |
| 2 | Multi-Angle Render Pipeline | ORIGINAL_REQUEST § R1 | 5 | 5 | ✓ | ✓ |
| 3 | Ollama VLM Enrichment & Caching | ORIGINAL_REQUEST § R1 | 5 | 5 | ✓ | ✓ |
| 4 | Terrain Heightmap (Perlin + Warp) | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ | ✓ |
| 5 | Numba Hydraulic Erosion | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ | ✓ |
| 6 | Poisson-Disc Zone Distribution | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ | ✓ |
| 7 | SAT OBB Building Placement | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ | ✓ |
| 8 | Slope-Aware A* Road Routing | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ | ✓ |
| 9 | World Manifest Export Endpoints | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ | ✓ |
| 10 | Frontend Three.js Scene | ORIGINAL_REQUEST § R3 | 5 | 5 | ✓ | ✓ |
| 11 | Frontend HUD Side Panels | ORIGINAL_REQUEST § R3 | 5 | 5 | ✓ | ✓ |
| 12 | Catalog Browser UI | ORIGINAL_REQUEST § R3 | 5 | 5 | ✓ | ✓ |
| 13 | Unity Terrain Instantiation | ORIGINAL_REQUEST § R4 | 5 | 5 | ✓ | ✓ |
| 14 | Unity PrefabUtility Spawning | ORIGINAL_REQUEST § R4 | 5 | 5 | ✓ | ✓ |
| 15 | Unity Faction/Damage Material Swapping | ORIGINAL_REQUEST § R4 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: `pytest` with `httpx`, `jsonschema`, and custom assertion helpers.
- Catalog validator: `python3 tests/validate_catalog.py backend/app/catalog/catalog.json`.
- Agent-as-Judge Rubrics: `tests/rubrics/frontend_rubric.md` and `tests/rubrics/unity_rubric.md`.
- E2E Integration runner: `pytest -v tests/`.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Large Desert Outpost (Faction A, Destruction 01) | Perlin, Erosion, Poisson, BBox, Roads, Manifest | High |
| 2 | Battle-Scarred Urban Compound (Faction C, Destruction 04) | Erosion, Dense SAT BBox, Roads, Manifest | High |
| 3 | Multi-Faction Island Archipelago | Chained Domain Warp, Poisson, Road routing, Manifest | High |
| 4 | Mountainous Radar Base with Steep Slopes | Slope-aware A* Roads, Plateau flattening, Manifest | High |
| 5 | Full Pipeline End-to-End | Catalog -> FastAPI Gen -> Three.js Frontend -> Unity C# Importer | Critical |

## Coverage Thresholds
- Tier 1: ≥5 per feature (Total ≥ 75 test cases)
- Tier 2: ≥5 per feature boundary (Total ≥ 75 test cases)
- Tier 3: Pairwise coverage of major feature interactions (Total ≥ 15 test cases)
- Tier 4: ≥5 realistic application scenarios (Total ≥ 5 test cases)
- Total minimum target: ≥ 170 test assertions/cases
