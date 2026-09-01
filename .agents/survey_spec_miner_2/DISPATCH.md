## 2026-09-01T21:53:52+04:00
<USER_REQUEST>
You are teamwork_preview_spec_miner (Survey Spec Miner 2: R1 & R2 Specs and Architecture).
Your working directory is: /Users/jack/worldgen/.agents/survey_spec_miner_2

Read the authoritative requirements at: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md

Your mission:
1. Mine and define precise mathematical, algorithmic, and architectural specifications for:
   - R1: Asset Catalog Builder (Blender CLI headless Python script to load 3D assets, compute oriented/axis-aligned 3D bounding boxes [min, max, dimensions, center], set up camera & lighting for multi-angle renders [front, side, top] saved as PNGs, invoke Ollama VLM `qwen3.8:27b` with vision prompt to infer tags, placement role, category, description, and output/cache in `catalog.json`). Detail the exact JSON schema of `catalog.json` and validation rules.
   - R2: Terrain and Zone Generator (FastAPI backend managed via `uv`):
     * Multifractal Perlin noise parameters (octaves, persistence, lacunarity, scale) + Domain Warping formula (perturbing coordinates with secondary noise).
     * Hydraulic erosion implementation using Numba JIT (droplet simulation: inertia, capacity, erosion, deposition, evaporation over iterations).
     * Poisson-disc 2D zone distribution (Bridson's algorithm, minimum distance between zone centers, zone radius/organic footprint generation, terrain flattening/smoothing under zone footprints).
     * Bounding box aware building placement inside zones (non-overlapping placement, rotation, terrain elevation alignment, density/faction/destruction assignment).
     * Slope-aware road routing (A* or Dijkstra pathfinding on 2D grid/heightmap with slope penalty and cost function connecting zone centers).
     * `world_manifest.json` schema: full data contract containing terrain metadata (resolution, heightmap array or raw/png), zones list (id, center, radius, faction, destruction, density), buildings list (prefab_name, position [x,y,z], rotation [x,y,z,w or euler], scale, bounding_box, zone_id), roads list (waypoints, width), and metadata.
     * FastAPI endpoints: `/generate`, `/manifest`, `/catalog`, `/health`, etc.
2. Write a detailed specification and architecture report to `/Users/jack/worldgen/.agents/survey_spec_miner_2/spec_report.md` and handoff to `/Users/jack/worldgen/.agents/survey_spec_miner_2/handoff.md`.
3. Send a message to your parent when done.
</USER_REQUEST>
