## 2026-09-01T18:01:36Z
You are teamwork_preview_worker (Milestone 2: Terrain & Zone Generator Backend).
Your working directory is: /Users/jack/worldgen/.agents/m2_worker_1

Read the authoritative requirements at: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md
Also read:
- /Users/jack/worldgen/PROJECT.md
- /Users/jack/worldgen/.agents/survey_spec_miner_2/spec_report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your write ownership:
You exclusively own:
- `/Users/jack/worldgen/backend/pyproject.toml`
- `/Users/jack/worldgen/backend/app/__init__.py`
- `/Users/jack/worldgen/backend/app/main.py`
- `/Users/jack/worldgen/backend/app/core/`
- `/Users/jack/worldgen/backend/app/generator/`
- `/Users/jack/worldgen/backend/app/api/`

Your mission:
1. Create `backend/pyproject.toml` managing dependencies with `uv` (fastapi, uvicorn, numba, numpy, scipy, pydantic, pytest, httpx, pillow, jsonschema).
2. Create `backend/app/core/schemas.py`: Pydantic models for `TerrainConfig`, `ZoneConfig`, `BuildingPlacement`, `RoadNetwork`, `WorldManifest`, and export schemas according to Draft 2020-12 `world_manifest.json` contract in `PROJECT.md`.
3. Create `backend/app/generator/terrain.py`: Multifractal Perlin noise (FBM) with configurable octaves, lacunarity, persistence, scale, and chained domain warping ($p' = p + s \cdot (N(p), N(p + \delta))$).
4. Create `backend/app/generator/erosion.py`: Numba JIT (`@njit(fastmath=True)`) droplet hydraulic erosion simulation (momentum, sediment capacity, dissolution, deposition, evaporation) providing high performance (<0.1s for 50k droplets).
5. Create `backend/app/generator/zones.py`: Bridson's 2D Poisson-disc algorithm for military zone centers, organic radial footprint generation, and smooth Hermite plateau terrain height flattening.
6. Create `backend/app/generator/buildings.py`: Bounding-box-aware building placement using Separating Axis Theorem (SAT) 2D Oriented Bounding Box collision avoidance, querying `backend/app/catalog/catalog.json` for dimensions, aligning building bases to terrain elevation, and assigning zone faction (A/B/C) and destruction (01-04).
7. Create `backend/app/generator/roads.py`: Slope-aware A* pathfinding on the 2D heightmap with quadratic slope penalty $d \cdot (1 + 20 \cdot G^2)$ connecting zone centers, with Catmull-Rom spline waypoint smoothing.
8. Create `backend/app/api/routes.py` and `backend/app/main.py`:
   - `POST /api/generate`: Generates full procedural world and returns `WorldManifest`.
   - `GET /api/manifest`: Returns current or cached `world_manifest.json`.
   - `GET /api/catalog`: Returns the asset catalog.
   - `GET /api/health`: Health check.
   - Static mount for `/renders/`.
   - CORS middleware enabled for Vite dev server (`http://localhost:5173`).
9. Run tests using `uv run pytest tests/` or `python3 -m pytest tests/` to verify that all generator modules and endpoints work cleanly.
10. Write your handoff report to `/Users/jack/worldgen/.agents/m2_worker_1/handoff.md` and notify your parent via `send_message`.
