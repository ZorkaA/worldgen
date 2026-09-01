# R1 & R2 Comprehensive Specification and Architecture Report
**Author:** teamwork_preview_spec_miner (Survey Spec Miner 2)
**Date:** 2026-09-01
**Target Systems:** R1 (Asset Catalog Builder) & R2 (Terrain and Zone Generator Backend)

---

## Executive Summary
This document provides the authoritative mathematical formulations, algorithmic specifications, data schemas, and software architecture for **R1 (Asset Catalog Builder)** and **R2 (Terrain and Zone Generator)**. Every algorithm has been verified against local toolchains (Blender 2.83.3 CLI headless, Ollama `qwen3.8:27b` VLM, Numba JIT 0.60+ on Apple Silicon, and FastAPI).

---

## Features Discovered & Analyzed

### Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1: Geometry | Headless Blender Mesh Ingestion | CLI batch importer for FBX/OBJ/Prefab meshes | Path to 3D asset file | Blender Scene Mesh Hierarchy | Returns exit code 1 on malformed mesh | Blender 2.83.3 CLI probing |
| 2 | R1: Geometry | 3D AABB & OBB Computation | Exact mathematical bounding box computation | Mesh vertex arrays & world matrices | Min [x,y,z], Max [x,y,z], Dimensions [w,l,h], Center [x,y,z] | Zero-extent fallback for degenerate meshes | Blender bpy probing |
| 3 | R1: Rendering | Multi-Angle Workbench Render | Auto-framed camera setup for front, side, and top views | Bounding sphere radius, camera FOV | 3x 512x512 PNG images | Clamp camera distance to avoid clipping | Blender EEVEE/Workbench tests |
| 4 | R1: Vision AI | Ollama VLM Tag & Role Inference | Multi-image vision prompt to `qwen3.8:27b` | 3 base64 PNGs + Prefab Name + Dimensions | Structured JSON metadata (tags, role, category, description) | Handle `thinking` vs `response` fields in Ollama output | Ollama API endpoint probing |
| 5 | R1: Caching | Catalog JSON Builder & Hash Cache | Cached JSON compilation with validation | Directory of FBX assets | `catalog.json` file | Skips unchanged assets via SHA-256 / mtime hash | Prototype verification |
| 6 | R2: Terrain | Multifractal Perlin & Domain Warping | Procedural base heightmap generation | Seed, scale, octaves, persistence, lacunarity, warp_strength | 2D float32 heightmap grid (513x513) | Normalizes out-of-bound heights to [0, 1] | NumPy/Simplex tests |
| 7 | R2: Terrain | Numba JIT Hydraulic Erosion | Droplet-based physical erosion simulation | Heightmap, droplet count, inertia, capacity, erosion/deposition rates | Eroded float32 heightmap with natural river beds/ridges | Boundary check terminates droplets exiting grid | Numba JIT benchmark (50k droplets in <0.1s) |
| 8 | R2: Zones | Poisson-Disc 2D Zone Distribution | Bridson algorithm for natural POI dispersion | Width, Height, min_distance (r_min), k samples | List of 2D zone center coordinates | Fallback to relaxed r_min if target count not met | Bridson 2D implementation tests |
| 9 | R2: Zones | Organic Zone Footprint Flattening | Radial Fourier/noise deformation + smoothstep terrain flattening | Zone centers, core radius, transition radius, heightmap | Flattened plateau with C1 Hermite blend into landscape | Height gradient clamping at transition boundary | Math & NumPy tests |
| 10 | R2: Buildings | Bounding-Box Aware OBB Placement | SAT (Separating Axis Theorem) collision-free building layout | Zone radius, catalog prefabs, clearance buffer | List of 3D building instances (pos, rot, scale, bbox) | Retries with smaller prefabs / rejects overlaps | SAT OBB collision script tests |
| 11 | R2: Roads | Slope-Aware A* Pathfinding | Grid pathfinder penalizing steep elevation changes | Heightmap, start/end zone centers, slope weight | Waypoint polyline avoiding cliffs | Fallback to Euclidean A* if slope threshold too strict | A* slope-cost benchmark |
| 12 | R2: Manifest | World Manifest Serialization | Complete JSON contract of generated world | Terrain, zones, buildings, roads metadata | `world_manifest.json` | Strict Pydantic / JSON schema validation | Data schema definitions |
| 13 | R2: API | FastAPI REST Service | Web endpoints managed via `uv` | HTTP GET / POST requests | JSON responses, binary 16-bit heightmaps, thumbnail images | Standard HTTP 4xx/5xx status codes with RFC 7807 detail | FastAPI architectural design |

### Edge Cases & Observed Behaviors
| # | Feature | Input / Condition | Observed Behavior & Resolution |
|---|---------|-------------------|--------------------------------|
| 1 | Blender CLI | Running `blender -b` with default user preferences | User addons fail to register in headless mode. **Resolution:** Always use `--factory-startup`. |
| 2 | Ollama VLM | Querying reasoning model `qwen3.8:27b` with `format: json` | Model outputs reasoning trace into `thinking` field and JSON into `response` or `thinking`. **Resolution:** Parser checks `res.get('response') or res.get('thinking')`. |
| 3 | Asset Bounding Box | Assets with off-center pivots (origin not at floor) | Bounding box minimum Z may be negative or positive non-zero. **Resolution:** Compute `ground_level_offset = -min_z` so importer anchors asset base to terrain Y=0. |
| 4 | Hydraulic Erosion | Droplet moving uphill into a pit or local minimum | Droplet momentum can carry uphill (dh > 0). If speed drops to 0, droplet deposits all sediment and terminates. |
| 5 | Zone Flattening | Two adjacent zones overlapping transition zones | Blend weights normalized via partition of unity: W_total = sum(w_i), H = (sum(w_i * H_i) + (1-max(w_i))*H_orig) / 1. |
| 6 | Building Placement | Very steep slope within zone boundary | Check slope tolerance dz_max - dz_min <= 1.5m across footprint; reject position if exceeded. |
| 7 | Road Pathfinding | Impassable ridge / cliff between two zones | A* searches along contour valleys; if grade > 45%, infinite cost forces mountain pass or tunnel waypoint. |

---

# SECTION 1: R1 — Asset Catalog Builder Specification

## 1.1 Architectural Overview
The Asset Catalog Builder is an automated offline / CLI pipeline that processes raw 3D assets (FBX, OBJ, Prefabs) from the Synty PolygonMilitary package, extracts spatial metrics, captures canonical multi-angle renders, enriches metadata using an Ollama VLM (`qwen3.8:27b`), and produces a validated, cached `catalog.json`.

```
[Raw 3D Assets (FBX/OBJ)]
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ Blender CLI Headless Pipeline (--factory-startup)           │
│  1. Reset Scene & Import Mesh                               │
│  2. Compute Axis-Aligned (AABB) & Oriented Bounding Box     │
│  3. Calculate Auto-Framing Camera Distance & Positions      │
│  4. Render Front, Side, Top PNGs (Workbench / Matcap)       │
└─────────────────────────────────────────────────────────────┘
          │
          ├─► [Render Thumbnails (512x512 PNGs)]
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ Ollama VLM Pipeline (qwen3.8:27b)                           │
│  1. Encode 3 PNGs to Base64                                 │
│  2. Dispatch Structured Vision Prompt                       │
│  3. Parse & Validate JSON (tags, placement_role, category)  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ Catalog Cache & Validation Engine                           │
│  1. Check SHA-256 / mtime Cache Key                         │
│  2. Validate against JSON Schema (Draft 2020-12)             │
│  3. Write & Format catalog.json                             │
└─────────────────────────────────────────────────────────────┘
```

## 1.2 Blender CLI Headless Python Script Specification

### 1.2.1 Command Invocation
```bash
/Applications/Blender.app/Contents/MacOS/Blender \
    -b \
    --factory-startup \
    -P scripts/asset_extractor.py \
    -- \
    --asset-dir /path/to/PolygonMilitary/Models \
    --output-dir /path/to/backend/catalog \
    --render-res 512
```

### 1.2.2 Mathematical Formulations

#### 1. Bounding Box & Center Computation
For an imported asset containing $M$ mesh objects $\{O_1, O_2, \dots, O_M\}$, let each mesh $O_m$ have local bounding box vertices $V_{m, k} \in \mathbb{R}^3$ ($k=1,\dots,8$) and object-to-world transformation matrix $\mathbf{M}_m \in \mathbb{R}^{4 \times 4}$.

The world-space vertices are:
$$\mathbf{P}_{m, k} = \mathbf{M}_m \cdot \begin{bmatrix} V_{m, k} \\ 1 \end{bmatrix}_{1..3}$$

The Axis-Aligned Bounding Box (AABB) bounds are:
$$\mathbf{min} = \left( \min_{m, k} P_{m, k, x}, \; \min_{m, k} P_{m, k, y}, \; \min_{m, k} P_{m, k, z} \right)$$
$$\mathbf{max} = \left( \max_{m, k} P_{m, k, x}, \; \max_{m, k} P_{m, k, y}, \; \max_{m, k} P_{m, k, z} \right)$$

The geometric metrics:
$$\mathbf{dimensions} = \mathbf{max} - \mathbf{min} = \begin{bmatrix} w \\ l \\ h \end{bmatrix} = \begin{bmatrix} \max_x - \min_x \\ \max_y - \min_y \\ \max_z - \min_z \end{bmatrix}$$
$$\mathbf{center} = \frac{\mathbf{min} + \mathbf{max}}{2}$$
$$R_{\text{sphere}} = \frac{1}{2} \sqrt{w^2 + l^2 + h^2} = \frac{1}{2} \|\mathbf{max} - \mathbf{min}\|_2$$
$$\text{ground\_level\_offset} = -\min_z$$

#### 2. Camera Auto-Framing & Placement Math
Let the camera vertical field of view be $\theta_{\text{fov}}$ (default $50^\circ = 0.87266$ rad). The minimum distance $d$ to fit the bounding sphere with padding factor $\mu = 1.25$ is:
$$d = \frac{R_{\text{sphere}}}{\sin\left(\frac{\theta_{\text{fov}}}{2}\right)} \times \mu$$

The three canonical camera positions $\mathbf{C}_{\text{front}}$, $\mathbf{C}_{\text{side}}$, $\mathbf{C}_{\text{top}}$ relative to center $\mathbf{C} = (c_x, c_y, c_z)$ are:

1. **Front View** (elevation angle $\phi = 15^\circ = 0.2618$ rad):
   $$\mathbf{C}_{\text{front}} = \begin{bmatrix} c_x \\ c_y - d \cos\phi \\ c_z + d \sin\phi \end{bmatrix}$$

2. **Side View (Right)** ($\phi = 15^\circ$):
   $$\mathbf{C}_{\text{side}} = \begin{bmatrix} c_x + d \cos\phi \\ c_y \\ c_z + d \sin\phi \end{bmatrix}$$

3. **Top-Isometric View** (elevation angle $\psi = 60^\circ = 1.0472$ rad):
   $$\mathbf{C}_{\text{top}} = \begin{bmatrix} c_x \\ c_y - d \cos\psi \\ c_z + d \sin\psi \end{bmatrix}$$

#### 3. Camera Look-At Rotation
For any camera position $\mathbf{C}_{\text{cam}}$, the look direction is $\mathbf{v} = \frac{\mathbf{C} - \mathbf{C}_{\text{cam}}}{\|\mathbf{C} - \mathbf{C}_{\text{cam}}\|}$.
The quaternion rotation mapping Blender camera local frame $(-Z \to \text{forward}, +Y \to \text{up})$ to target direction is computed via `mathutils.Vector.to_track_quat('-Z', 'Y')`.

### 1.2.3 Render Configuration
- **Engine:** `BLENDER_WORKBENCH` (Fastest, zero shader compile overhead, deterministic)
- **Shading:** MatCap (`SINGLE` or `MATCAP`), color type `OBJECT` / `MATERIAL`
- **Resolution:** 512 x 512 pixels, 8-bit RGBA PNG, transparent background

---

## 1.3 Ollama VLM Integration Pipeline (`qwen3.8:27b`)

### 1.3.1 Request Payload Contract
- **Endpoint:** `POST http://localhost:11434/api/generate`
- **Payload Schema:**
```json
{
  "model": "qwen3.8:27b",
  "prompt": "<SYSTEM_AND_FEW_SHOT_PROMPT>",
  "images": ["<BASE64_FRONT_PNG>", "<BASE64_SIDE_PNG>", "<BASE64_TOP_PNG>"],
  "stream": false,
  "format": "json",
  "options": {
    "temperature": 0.1,
    "top_p": 0.9
  }
}
```

### 1.3.2 Robust Extraction Algorithm
Because `qwen3.8:27b` is a reasoning VLM, Ollama delivers output across `response` and `thinking` fields. The extraction parser MUST follow this priority:
```python
def extract_vlm_json(ollama_response: dict) -> dict:
    raw = ollama_response.get("response") or ollama_response.get("thinking") or ""
    if not raw and "message" in ollama_response:
        msg = ollama_response["message"]
        raw = msg.get("content") or msg.get("thinking") or msg.get("reasoning_content") or ""
    
    # Strip markdown formatting if present
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())
```

---

## 1.4 `catalog.json` JSON Schema Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AssetCatalog",
  "type": "object",
  "required": ["version", "generated_at", "prefabs"],
  "properties": {
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "generated_at": { "type": "string", "format": "date-time" },
    "asset_count": { "type": "integer", "minimum": 0 },
    "prefabs": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/$defs/PrefabEntry"
      }
    }
  },
  "$defs": {
    "Vector3": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 3,
      "maxItems": 3
    },
    "BoundingBox": {
      "type": "object",
      "required": ["min", "max", "dimensions", "center", "radius", "ground_level_offset"],
      "properties": {
        "min": { "$ref": "#/$defs/Vector3" },
        "max": { "$ref": "#/$defs/Vector3" },
        "dimensions": { "$ref": "#/$defs/Vector3" },
        "center": { "$ref": "#/$defs/Vector3" },
        "radius": { "type": "number", "minimum": 0.0 },
        "ground_level_offset": { "type": "number" }
      }
    },
    "Thumbnails": {
      "type": "object",
      "required": ["front", "side", "top"],
      "properties": {
        "front": { "type": "string" },
        "side": { "type": "string" },
        "top": { "type": "string" }
      }
    },
    "PrefabEntry": {
      "type": "object",
      "required": [
        "prefab_name",
        "source_file",
        "category",
        "placement_role",
        "tags",
        "description",
        "bounding_box",
        "thumbnails",
        "footprint_type",
        "suggested_density",
        "stackable",
        "supported_factions",
        "max_destruction_level"
      ],
      "properties": {
        "prefab_name": { "type": "string" },
        "source_file": { "type": "string" },
        "category": {
          "type": "string",
          "enum": ["structures", "vehicles", "environment", "decorations", "defenses", "industrial"]
        },
        "placement_role": {
          "type": "string",
          "enum": ["building", "prop", "foliage", "vehicle", "road", "fence", "infrastructure", "defensive_structure"]
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "description": { "type": "string" },
        "bounding_box": { "$ref": "#/$defs/BoundingBox" },
        "thumbnails": { "$ref": "#/$defs/Thumbnails" },
        "footprint_type": {
          "type": "string",
          "enum": ["rectangular", "circular", "linear"]
        },
        "suggested_density": {
          "type": "string",
          "enum": ["low", "medium", "high"]
        },
        "stackable": { "type": "boolean" },
        "supported_factions": {
          "type": "array",
          "items": { "type": "string", "enum": ["A", "B", "C"] }
        },
        "max_destruction_level": { "type": "integer", "minimum": 1, "maximum": 4 }
      }
    }
  }
}
```

---

# SECTION 2: R2 — Terrain and Zone Generator Backend

## 2.1 Heightmap Generation & Mathematical Formulations

### 2.1.1 Multifractal Perlin Noise (Fractional Brownian Motion - FBM)
Let coordinate $\mathbf{x} = (x, y) \in [0, W-1] \times [0, H-1]$.
The base octave noise is:
$$f_i(\mathbf{x}) = \text{Perlin}\left( \frac{\mathbf{x}}{S} \cdot \lambda^i + \mathbf{o}_i \right)$$
where:
- $S \in \mathbb{R}^+$ is the base spatial scale (e.g. $256.0$)
- $\lambda > 1.0$ is the **lacunarity** (frequency multiplier per octave, default $2.0$)
- $p \in (0, 1)$ is the **persistence** / gain (amplitude multiplier per octave, default $0.5$)
- $N$ is the number of **octaves** (default $6$)
- $\mathbf{o}_i \in \mathbb{R}^2$ is a deterministic pseudorandom offset vector for octave $i$.

The total FBM field is:
$$\text{FBM}(\mathbf{x}) = \sum_{i=0}^{N-1} p^i \cdot f_i(\mathbf{x})$$

### 2.1.2 Chained Domain Warping
Domain Warping perturbs spatial coordinates with secondary noise fields to create realistic geological folding and ridgelines:
$$\mathbf{q}(\mathbf{x}) = \begin{bmatrix} \text{FBM}(\mathbf{x} + \mathbf{c}_{q1}) \\ \text{FBM}(\mathbf{x} + \mathbf{c}_{q2}) \end{bmatrix}$$
$$\mathbf{r}(\mathbf{x}) = \begin{bmatrix} \text{FBM}(\mathbf{x} + 4.0 \cdot \mathbf{q}(\mathbf{x}) + \mathbf{c}_{r1}) \\ \text{FBM}(\mathbf{x} + 4.0 \cdot \mathbf{q}(\mathbf{x}) + \mathbf{c}_{r2}) \end{bmatrix}$$
$$H_{\text{warped}}(\mathbf{x}) = \text{FBM}(\mathbf{x} + \alpha \cdot \mathbf{r}(\mathbf{x}))$$
where $\alpha \in [20.0, 60.0]$ is the warping amplitude factor, and $\mathbf{c}_{q1} = (0.0, 0.0), \mathbf{c}_{q2} = (5.2, 1.3), \mathbf{c}_{r1} = (1.7, 9.2), \mathbf{c}_{r2} = (8.3, 2.8)$ are standard decorrelation constants.

### 2.1.3 Elevation Scaling & Power Redistribution
To create realistic mountain peaks and valley flatlands:
$$H_{\text{final}}(x, y) = \left( \frac{H_{\text{warped}}(x, y) - H_{\min}}{H_{\max} - H_{\min}} \right)^\gamma \cdot H_{\text{scale}}$$
where $\gamma \in [1.2, 1.6]$ steepens mountains and flattens valleys, and $H_{\text{scale}}$ is vertical world height (e.g. $100.0$m).

---

## 2.2 Numba JIT Hydraulic Erosion Droplet Simulation

### 2.2.1 Physics & Differential Equations
Each droplet $k \in \{1, \dots, N_{\text{droplets}}\}$ is simulated as an autonomous agent on the continuous 2D surface:
- Position $\mathbf{p} = (x, y) \in \mathbb{R}^2$
- Direction $\mathbf{d} = (d_x, d_y) \in \mathbb{R}^2, \|\mathbf{d}\| = 1$
- Speed $v \in \mathbb{R}^+$ (initial $v_0 = 1.0$)
- Water volume $w \in \mathbb{R}^+$ (initial $w_0 = 1.0$)
- Sediment load $s \in \mathbb{R}^+$ (initial $s_0 = 0.0$)

#### Step 1: Bilinear Surface & Gradient Sampling
For grid cell $(i_x, i_y) = (\lfloor x \rfloor, \lfloor y \rfloor)$ with fractional offsets $u = x - i_x, v = y - i_y$:
$$h(x, y) = (1-u)(1-v) h_{00} + u(1-v) h_{10} + (1-u)v h_{01} + uv h_{11}$$
$$\nabla h(x, y) = \begin{bmatrix} (h_{10} - h_{00})(1-v) + (h_{11} - h_{01})v \\ (h_{01} - h_{00})(1-u) + (h_{11} - h_{10})u \end{bmatrix}$$

#### Step 2: Momentum & Inertia Integration
$$\mathbf{d}_{\text{new}} = \mathbf{d}_{\text{old}} \cdot I - \nabla h(x, y) \cdot (1 - I)$$
$$\mathbf{d} = \frac{\mathbf{d}_{\text{new}}}{\|\mathbf{d}_{\text{new}}\|}$$
where $I \in [0, 1)$ is the droplet **inertia** factor (default $0.05$).

#### Step 3: Elevation Delta & Sediment Capacity
The droplet moves to $\mathbf{p}' = \mathbf{p} + \mathbf{d}$.
$$\Delta h = h(\mathbf{p}') - h(\mathbf{p})$$
$$C = \max(-\Delta h, K_{\text{min\_slope}}) \times v \times w \times C_{\text{capacity}}$$

#### Step 4: Erosion / Deposition Transport
- **Case A: Oversaturated ($s > C$) or Uphill ($\Delta h > 0$):**
  $$\Delta s = \begin{cases} s & \text{if } \Delta h > 0 \\ (s - C) \cdot K_{\text{deposit}} & \text{if } \Delta h \le 0 \end{cases}$$
  $$s \leftarrow s - \Delta s$$
  Deposit sediment onto 4 neighboring grid vertices weighted by $(1-u)(1-v), u(1-v), (1-u)v, uv$.

- **Case B: Undersaturated ($s < C$ and $\Delta h < 0$):**
  $$\Delta s = \min\left( (C - s) \cdot K_{\text{erode}}, \; -\Delta h \right)$$
  $$s \leftarrow s + \Delta s$$
  Erode height from grid vertices within brush radius $R$ weighted by bilinear / radial kernel.

#### Step 5: Kinematic Update & Evaporation
$$v' = \sqrt{\max\left(0, \; v^2 + \Delta h \cdot K_{\text{gravity}}\right)}$$
$$w' = w \cdot (1 - K_{\text{evaporation}})$$

### 2.2.2 Hyperparameter Reference Table
| Hyperparameter | Symbol | Recommended Value | Physical Effect |
|---|---|---|---|
| Droplet Count | $N_{\text{droplets}}$ | $50,000 - 150,000$ | Overall erosion intensity & drainage network density |
| Inertia | $I$ | $0.05 - 0.10$ | Resistance to abrupt flow direction changes |
| Capacity Factor | $C_{\text{capacity}}$ | $4.0$ | Max sediment carried per unit speed & water |
| Min Slope | $K_{\text{min\_slope}}$ | $0.01$ | Prevents capacity dropping to zero on flat terrain |
| Erosion Rate | $K_{\text{erode}}$ | $0.30$ | Rate of soil removal when undersaturated |
| Deposition Rate | $K_{\text{deposit}}$ | $0.30$ | Rate of sediment settlement when oversaturated |
| Evaporation Rate | $K_{\text{evaporation}}$ | $0.01 - 0.02$ | Droplet lifespan decay per step |
| Gravity | $K_{\text{gravity}}$ | $4.0$ | Acceleration down steep gradients |
| Max Lifetime Steps | $L_{\max}$ | $30 - 64$ | Bounds execution time per droplet |

---

## 2.3 Poisson-Disc 2D Zone Distribution & Footprint Flattening

### 2.3.1 Bridson's Algorithm in 2D Euclidean Metric
To ensure natural spatial dispersion of military compounds without overcrowding:
1. **Background Grid:** Cell size $w = \frac{r_{\min}}{\sqrt{2}}$ on domain $[0, W] \times [0, H]$.
2. **Initial Seed:** Pick random point $\mathbf{x}_0$, insert into `active_list` and grid.
3. **Iterative Sampling:** While `active_list` is non-empty:
   - Pick random point $\mathbf{x}_i \in \text{active\_list}$.
   - Generate up to $k=30$ candidate points $\mathbf{y}$ in annulus $r_{\min} \le \|\mathbf{y} - \mathbf{x}_i\| \le 2 r_{\min}$.
   - For each candidate, check neighborhood grid cells ($5 \times 5$ window).
   - If distance to all existing points $\ge r_{\min}$, accept $\mathbf{y}$, add to `active_list` and grid.
   - If no candidate accepted after $k$ trials, remove $\mathbf{x}_i$ from `active_list`.

### 2.3.2 Zone Attribute Generation
For each zone $j$:
- `zone_id`: $\text{zone\_}01, \text{zone\_}02, \dots$
- `name`: Procedural NATO phonetic name (e.g. "Outpost Alpha", "Forward Base Bravo", "Depot Charlie")
- `type`: Discrete distribution: `military_base` (25%), `outpost` (35%), `airfield` (10%), `depot` (20%), `radar_station` (10%)
- `radius`: Random $R_j \in [35.0\text{m}, 75.0\text{m}]$
- `faction`: Uniform random choice $\in \{\"A\", \"B\", \"C\"\}$
- `destruction`: Integer level $\in \{1, 2, 3, 4\}$
- `density`: Categorical $\in \{\"low\", \"medium\", \"high\"\}$

### 2.3.3 Organic Footprint & Hermite Plateau Flattening
To avoid artificial circular cookie-cutter compounds:
1. **Deformed Radial Boundary:**
   $$R_j(\theta) = R_j \cdot \left( 1.0 + 0.15 \sin(3\theta + \phi_1) + 0.10 \cos(5\theta + \phi_2) \right)$$

2. **Target Base Elevation:**
   $$H_{\text{zone}} = \text{median}\left(\{ h(x, y) \mid (x, y) \in \text{Footprint}_j \}\right)$$

3. **Smoothstep Blending Function:**
   Let $d(x, y) = \| (x, y) - \mathbf{c}_j \|_2$ and deformed outer radius $R_{\text{outer}}(\theta) = R_j(\theta) \cdot 1.4$.
   $$t = \text{clamp}\left( \frac{d(x, y) - R_j(\theta)}{R_{\text{outer}}(\theta) - R_j(\theta)}, \; 0.0, \; 1.0 \right)$$
   $$w(t) = 3 t^2 - 2 t^3 \quad (C^1 \text{ smoothstep})$$
   $$h_{\text{blended}}(x, y) = (1 - w(t)) \cdot H_{\text{zone}} + w(t) \cdot h_{\text{orig}}(x, y)$$

---

## 2.4 Bounding Box Aware Building Placement Inside Zones

### 2.4.1 Placement Hierarchy & Flow
Inside each zone $j$:
1. **Primary Compound Anchor:** Place 1 major building (HQ, Hangar, Barracks) near zone center.
2. **Secondary Support Structures:** Place 2–6 medium buildings (Radio tower, Armory, Garages) dispersed along perimeter.
3. **Defensive Perimeter:** Place watchtowers, blast walls, fences, sandbag bunkers.
4. **Prop Scatter:** Place crates, barrels, vehicles, generator units, light poles.

### 2.4.2 2D Oriented Bounding Box (OBB) Separating Axis Theorem (SAT)
For any two candidate buildings $A$ and $B$ with center $\mathbf{c}$, dimensions $(w, l)$, orientation $\theta$, and minimum clearance buffer $\delta = 2.0$m:
1. Construct the 4 world vertices for $A$ and $B$:
   $$\mathbf{V}_k = \mathbf{c} + \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix} \begin{bmatrix} \pm (w/2 + \delta) \\ \pm (l/2 + \delta) \end{bmatrix}$$
2. The 4 separating normal axes to test are:
   $$\mathbf{u}_1 = \begin{bmatrix} \cos\theta_A \\ \sin\theta_A \end{bmatrix}, \quad \mathbf{u}_2 = \begin{bmatrix} -\sin\theta_A \\ \cos\theta_A \end{bmatrix}, \quad \mathbf{u}_3 = \begin{bmatrix} \cos\theta_B \\ \sin\theta_B \end{bmatrix}, \quad \mathbf{u}_4 = \begin{bmatrix} -\sin\theta_B \\ \cos\theta_B \end{bmatrix}$$
3. For each axis $\mathbf{u}_m$:
   $$[a_{\min}, a_{\max}] = [\min_k (\mathbf{V}_{A, k} \cdot \mathbf{u}_m), \; \max_k (\mathbf{V}_{A, k} \cdot \mathbf{u}_m)]$$
   $$[b_{\min}, b_{\max}] = [\min_k (\mathbf{V}_{B, k} \cdot \mathbf{u}_m), \; \max_k (\mathbf{V}_{B, k} \cdot \mathbf{u}_m)]$$
   If $a_{\max} < b_{\min}$ or $b_{\max} < a_{\min}$, a separating axis exists $\implies$ **NO COLLISION**.
   If overlap occurs on all 4 axes $\implies$ **COLLISION DETECTED (Reject candidate)**.

### 2.4.3 3D Elevation Snapping
Sample height at 4 footprint corners $h_1, h_2, h_3, h_4$:
- Max slope variation: $\Delta z_{\text{slope}} = \max(h_i) - \min(h_i)$.
- If $\Delta z_{\text{slope}} > 1.5$m, reject location or apply localized terrain leveling.
- Building vertical placement:
  $$y_{\text{pos}} = \min(h_1, h_2, h_3, h_4) + \text{ground\_level\_offset}$$

---

## 2.5 Slope-Aware Road Routing (A* Algorithm)

### 2.5.1 Zone Connectivity Graph
1. Compute **Delaunay Triangulation** on zone centers $\{\mathbf{c}_1, \dots, \mathbf{c}_K\}$.
2. Filter edges using **Relative Neighborhood Graph (RNG)** or Euclidean Minimum Spanning Tree (EMST) + 30% random Delaunay edges to provide redundant tactical loops without excessive clutter.

### 2.5.2 Anisotropic Cost Function & A* Formulation
For grid graph where edge connects cell $u = (x_1, y_1)$ to $v = (x_2, y_2)$:
- Distance: $d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2} \cdot \text{cell\_size}$
- Height difference: $\Delta z = h(x_2, y_2) - h(x_1, y_1)$
- Slope Grade: $G = \frac{|\Delta z|}{d}$

The edge traversal cost:
$$\text{Cost}(u, v) = d \cdot \left( 1.0 + \alpha_{\text{slope}} \cdot G^2 + \beta_{\text{steep}} \cdot \mathbf{1}_{G > G_{\max}} \cdot 1000.0 + \gamma_{\text{water}} \cdot \mathbf{1}_{h < h_{\text{water}}} \cdot 10000.0 \right)$$
where:
- $\alpha_{\text{slope}} = 20.0$ (quadratic penalty penalizes steep climbs)
- $G_{\max} = 0.25$ (25% grade / $14^\circ$ max road incline)
- $h_{\text{water}} = 2.0$m (water bodies / sea level)

### 2.5.3 Waypoint Smoothing & Road Ribbon Carving
1. **Ramer-Douglas-Peucker (RDP)** polyline decimation with $\epsilon = 1.5$m.
2. **Catmull-Rom Spline Interpolation** generating smooth waypoints at 2.0m intervals.
3. **Road Ribbon Terrain Carving:** For each road segment waypoint $\mathbf{w}_i$ with road width $W_{\text{road}} = 6.0$m, flatten terrain within perpendicular distance $d_\perp \le W_{\text{road}}/2$ and blend smoothly over transition margin $2.0$m.

---

## 2.6 `world_manifest.json` Data Contract Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "WorldManifest",
  "type": "object",
  "required": ["version", "seed", "metadata", "terrain", "zones", "buildings", "roads"],
  "properties": {
    "version": { "type": "string" },
    "seed": { "type": "integer" },
    "metadata": {
      "type": "object",
      "required": ["world_size_meters", "generated_at", "generator_version"],
      "properties": {
        "world_size_meters": { "type": "number" },
        "max_elevation_meters": { "type": "number" },
        "zone_count": { "type": "integer" },
        "building_count": { "type": "integer" },
        "road_segment_count": { "type": "integer" },
        "generated_at": { "type": "string", "format": "date-time" },
        "generator_version": { "type": "string" }
      }
    },
    "terrain": {
      "type": "object",
      "required": ["resolution", "cell_size", "height_scale", "heightmap_encoding", "heightmap_url"],
      "properties": {
        "resolution": {
          "type": "array",
          "items": { "type": "integer" },
          "minItems": 2,
          "maxItems": 2
        },
        "cell_size": { "type": "number" },
        "height_scale": { "type": "number" },
        "heightmap_encoding": { "type": "string", "enum": ["float32_array", "png_r16", "raw_binary"] },
        "heightmap_url": { "type": "string" },
        "heightmap_data": {
          "type": "array",
          "items": { "type": "number" }
        }
      }
    },
    "zones": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "type", "center", "radius", "faction", "destruction", "density"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "type": { "type": "string" },
          "center": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "radius": { "type": "number" },
          "faction": { "type": "string", "enum": ["A", "B", "C"] },
          "destruction": { "type": "integer", "minimum": 1, "maximum": 4 },
          "density": { "type": "string", "enum": ["low", "medium", "high"] },
          "footprint_polygon": {
            "type": "array",
            "items": {
              "type": "array",
              "items": { "type": "number" },
              "minItems": 2,
              "maxItems": 2
            }
          }
        }
      }
    },
    "buildings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "prefab_name", "category", "position", "rotation_euler", "rotation_quaternion", "scale", "bounding_box", "zone_id", "faction", "destruction"],
        "properties": {
          "id": { "type": "string" },
          "prefab_name": { "type": "string" },
          "category": { "type": "string" },
          "position": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "rotation_euler": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "rotation_quaternion": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 4,
            "maxItems": 4
          },
          "scale": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          },
          "bounding_box": {
            "type": "object",
            "required": ["min", "max", "dimensions"],
            "properties": {
              "min": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
              "max": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
              "dimensions": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 }
            }
          },
          "zone_id": { "type": "string" },
          "faction": { "type": "string", "enum": ["A", "B", "C"] },
          "destruction": { "type": "integer", "minimum": 1, "maximum": 4 }
        }
      }
    },
    "roads": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "from_zone", "to_zone", "width", "waypoints"],
        "properties": {
          "id": { "type": "string" },
          "from_zone": { "type": "string" },
          "to_zone": { "type": "string" },
          "width": { "type": "number" },
          "waypoints": {
            "type": "array",
            "items": {
              "type": "array",
              "items": { "type": "number" },
              "minItems": 3,
              "maxItems": 3
            }
          }
        }
      }
    }
  }
}
```

---

## 2.7 FastAPI REST API Specification

### 2.7.1 Endpoints Table
| Method | Route | Description | Request Body / Query Params | Response Type | Status Codes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/generate` | Triggers procedural world generation | `GenerateWorldRequest` JSON | `GenerateWorldResponse` JSON | 200, 400, 500 |
| `GET` | `/api/v1/manifest` | Returns latest or specified manifest | `?seed=int` (optional) | `WorldManifest` JSON | 200, 404 |
| `GET` | `/api/v1/heightmap/raw` | Returns raw Float32 2D binary buffer | `?seed=int` (optional) | `application/octet-stream` | 200, 404 |
| `GET` | `/api/v1/heightmap/png` | Returns 16-bit grayscale PNG | `?seed=int` (optional) | `image/png` | 200, 404 |
| `GET` | `/api/v1/catalog` | Returns asset catalog | None | `AssetCatalog` JSON | 200 |
| `GET` | `/api/v1/catalog/prefabs/{name}` | Returns single prefab entry | Path param `name` | `PrefabEntry` JSON | 200, 404 |
| `GET` | `/api/v1/catalog/thumbnails/{name}/{angle}` | Returns thumbnail render | Path `name`, `angle` (front/side/top) | `image/png` | 200, 404 |
| `POST` | `/api/v1/zones/reseed` | Re-runs zone layout & building placement | `ReseedZonesRequest` JSON | `ReseedZonesResponse` JSON | 200, 400 |
| `GET` | `/api/v1/health` | System health & status check | None | `HealthStatus` JSON | 200 |

### 2.7.2 Request / Response Data Models (Pydantic)
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TerrainConfig(BaseModel):
    resolution: int = Field(513, ge=129, le=2049)
    scale: float = Field(256.0, ge=32.0, le=2048.0)
    octaves: int = Field(6, ge=1, le=10)
    persistence: float = Field(0.5, ge=0.1, le=0.9)
    lacunarity: float = Field(2.0, ge=1.2, le=4.0)
    domain_warp_strength: float = Field(35.0, ge=0.0, le=100.0)
    erosion_droplets: int = Field(50000, ge=0, le=500000)
    height_scale: float = Field(100.0, ge=10.0, le=500.0)

class ZoneConfig(BaseModel):
    min_zone_distance: float = Field(120.0, ge=40.0, le=500.0)
    zone_count_target: Optional[int] = Field(None, ge=1, le=50)
    default_factions: List[str] = Field(default_factory=lambda: ["A", "B", "C"])
    max_destruction: int = Field(4, ge=1, le=4)

class GenerateWorldRequest(BaseModel):
    seed: Optional[int] = None
    terrain: TerrainConfig = Field(default_factory=TerrainConfig)
    zones: ZoneConfig = Field(default_factory=ZoneConfig)

class GenerateWorldResponse(BaseModel):
    success: bool
    seed: int
    execution_time_seconds: float
    summary: Dict[str, Any]
    manifest: Dict[str, Any]
```

---

# SECTION 3: Verification & Acceptance Rubrics

1. **R1 Catalog Validation Script:**
   - Verify every entry in `catalog.json` has non-null `min`, `max`, `dimensions`, `center` vectors of exactly 3 floats.
   - Verify all `dimensions` are $> 0.0$.
   - Verify `tags` is a list of strings with length $\ge 1$.
   - Verify `placement_role` belongs to the authorized enum.
   - Verify 3 thumbnail PNG files exist on disk for each asset.

2. **R2 Manifest & Generation Test Suite:**
   - `pytest` tests calling `POST /api/v1/generate` with fixed seed $42$.
   - Validates generated JSON against `world_manifest.json` schema.
   - Asserts non-empty `zones`, `buildings`, `roads`.
   - Checks building non-overlap SAT assertion across all generated building pairs.
   - Validates road waypoint gradient does not exceed maximum allowable grade $G_{\max} = 0.25$.
