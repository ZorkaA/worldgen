"""
VLM Enrichment Module.
Integrates with local Ollama daemon (qwen3.8:27b) with multi-image vision analysis,
and provides a high-fidelity, deterministic heuristic fallback classifier based on
Synty PolygonMilitary naming conventions.
"""

import os
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional


def encode_image_base64(image_path: str) -> Optional[str]:
    """Read an image file and return its base64-encoded string."""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"[VLMEnrich] Failed to encode image {image_path}: {e}")
        return None


def clean_vlm_json_string(raw_text: str) -> str:
    """Extract and sanitize JSON from VLM responses (stripping markdown fences)."""
    cleaned = raw_text.strip()
    if "```json" in cleaned:
        parts = cleaned.split("```json")
        cleaned = parts[1].split("```")[0].strip()
    elif "```" in cleaned:
        parts = cleaned.split("```")
        cleaned = parts[1].split("```")[0].strip()
    
    # Locate first '{' and last '}'
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]
    
    return cleaned


def parse_vlm_response(ollama_resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse and extract structured JSON from Ollama API response."""
    # Priority: message.content -> response -> message.thinking -> thinking
    candidates = []
    
    msg = ollama_resp.get("message", {})
    if isinstance(msg, dict):
        if msg.get("content"):
            candidates.append(msg["content"])
        if msg.get("thinking"):
            candidates.append(msg["thinking"])
        if msg.get("reasoning_content"):
            candidates.append(msg["reasoning_content"])
            
    if ollama_resp.get("response"):
        candidates.append(ollama_resp["response"])
    if ollama_resp.get("thinking"):
        candidates.append(ollama_resp["thinking"])
        
    for text in candidates:
        if not text or not isinstance(text, str):
            continue
        cleaned = clean_vlm_json_string(text)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
            
    return None


def heuristic_enrich_asset(asset_name: str, dimensions: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    High-fidelity, deterministic rule-based asset classifier.
    Understands all Synty PolygonMilitary naming conventions.
    """
    name_lower = asset_name.lower()
    is_destroyed = "destroyed" in name_lower or "damaged" in name_lower or "debris" in name_lower
    
    # Defaults
    category = "structures"
    placement_role = "building"
    tags = ["military", "structure"]
    description = f"PolygonMilitary asset: {asset_name}."
    affinities = ["military_base", "outpost"]
    suggested_density = "medium"
    footprint_type = "rectangular"
    stackable = False
    supported_factions = ["A", "B", "C"]
    max_destruction_level = 4 if is_destroyed else 3

    # 1. Buildings & Structures
    if "tent" in name_lower:
        category = "structures"
        placement_role = "building"
        tags = ["tent", "military", "shelter", "barracks", "fabric", "canvas"]
        description = "Standard military canvas tent used for personnel quarters, field hospital, or logistics staging."
        affinities = ["military_base", "outpost", "checkpoint"]
        suggested_density = "medium"
        footprint_type = "rectangular"
    elif "barracks" in name_lower:
        category = "structures"
        placement_role = "building"
        tags = ["barracks", "military", "quarters", "housing", "compound", "building"]
        description = "Reinforced military barracks building for troop housing and operations."
        affinities = ["military_base", "outpost"]
        suggested_density = "medium"
        footprint_type = "rectangular"
    elif "controltower" in name_lower or "clock_tower" in name_lower or "tower" in name_lower:
        category = "structures"
        placement_role = "defensive_structure"
        tags = ["tower", "control", "surveillance", "observation", "radar", "lookout"]
        description = "Elevated observation and airfield control tower providing strategic sightlines."
        affinities = ["military_base", "airfield", "radar_station"]
        suggested_density = "low"
        footprint_type = "circular"
    elif "village_house" in name_lower or "house" in name_lower:
        category = "structures"
        placement_role = "building"
        tags = ["house", "village", "residential", "urban", "compound", "building"]
        description = "Urban village compound residential structure."
        affinities = ["outpost", "depot"]
        suggested_density = "high"
        footprint_type = "rectangular"
    elif "watertank" in name_lower or "water_tank" in name_lower:
        category = "industrial"
        placement_role = "infrastructure"
        tags = ["water_tank", "utility", "reservoir", "infrastructure", "industrial"]
        description = "Elevated industrial water storage reservoir."
        affinities = ["military_base", "depot", "outpost"]
        suggested_density = "low"
        footprint_type = "circular"
    elif "hangar" in name_lower:
        category = "structures"
        placement_role = "building"
        tags = ["hangar", "aviation", "aircraft", "maintenance", "shelter"]
        description = "Large aircraft hangar and heavy vehicle maintenance facility."
        affinities = ["airfield", "military_base"]
        suggested_density = "low"
        footprint_type = "rectangular"
    elif "archway" in name_lower or "gate" in name_lower or "wall" in name_lower or "fence" in name_lower or "barrier" in name_lower:
        if "fence" in name_lower or "barrier" in name_lower:
            category = "defenses"
            placement_role = "fence"
            tags = ["fence", "barrier", "perimeter", "security", "wire", "obstacle"]
            description = "Perimeter security fence barrier for base boundary fortification."
            affinities = ["military_base", "outpost", "checkpoint", "airfield"]
            suggested_density = "high"
            footprint_type = "linear"
        else:
            category = "defenses"
            placement_role = "defensive_structure"
            tags = ["wall", "gate", "defense", "barrier", "fortification", "archway"]
            description = "Reinforced perimeter fortification wall and compound gate."
            affinities = ["military_base", "outpost", "checkpoint"]
            suggested_density = "high"
            footprint_type = "linear"
    elif "bridge" in name_lower:
        category = "industrial"
        placement_role = "infrastructure"
        tags = ["bridge", "crossing", "road", "infrastructure"]
        description = "Heavy tactical crossing bridge segment."
        affinities = ["military_base", "outpost", "checkpoint"]
        suggested_density = "low"
        footprint_type = "linear"
    elif "sandbag" in name_lower or "bunker" in name_lower or "trench" in name_lower:
        category = "defenses"
        placement_role = "defensive_structure"
        tags = ["sandbag", "fortification", "bunker", "defense", "cover", "trench"]
        description = "Fortified defensive sandbag position providing combat ballistic cover."
        affinities = ["military_base", "outpost", "checkpoint"]
        suggested_density = "high"
        footprint_type = "linear"
    elif "pipeline" in name_lower or "pipe" in name_lower:
        category = "industrial"
        placement_role = "infrastructure"
        tags = ["pipeline", "fuel", "industrial", "utility", "pipe"]
        description = "Fuel and industrial utility delivery pipeline."
        affinities = ["depot", "military_base", "airfield"]
        suggested_density = "medium"
        footprint_type = "linear"
    elif "crate" in name_lower or "barrel" in name_lower or "pallet" in name_lower or "storage" in name_lower or "cargo" in name_lower:
        category = "decorations"
        placement_role = "prop"
        tags = ["crate", "cargo", "supply", "storage", "logistics", "ammo", "barrel"]
        description = "Logistics supply cargo container and storage crate."
        affinities = ["military_base", "depot", "airfield", "outpost"]
        suggested_density = "high"
        footprint_type = "rectangular"
    elif "bed" in name_lower or "chair" in name_lower or "table" in name_lower or "desk" in name_lower:
        category = "decorations"
        placement_role = "prop"
        tags = ["furniture", "interior", "military", "barracks"]
        description = "Military field furniture and barracks interior equipment."
        affinities = ["military_base", "outpost"]
        suggested_density = "medium"
        footprint_type = "rectangular"
    elif "antenna" in name_lower or "radar" in name_lower or "radio" in name_lower or "dish" in name_lower:
        category = "industrial"
        placement_role = "infrastructure"
        tags = ["antenna", "communication", "radar", "signal", "radio", "electronic"]
        description = "Tactical communications antenna array and long-range radar relay."
        affinities = ["military_base", "radar_station", "outpost"]
        suggested_density = "low"
        footprint_type = "circular"
    elif "veh" in name_lower or "tank" in name_lower or "truck" in name_lower or "jeep" in name_lower or "heli" in name_lower or "jet" in name_lower or "apc" in name_lower:
        category = "vehicles"
        placement_role = "vehicle"
        if "tank" in name_lower:
            tags = ["tank", "armor", "combat", "vehicle", "military", "heavy", "tracked"]
            description = "Main battle tank heavily armored fighting vehicle."
            affinities = ["military_base", "checkpoint", "depot"]
            suggested_density = "low"
        elif "heli" in name_lower:
            tags = ["helicopter", "aircraft", "rotary", "aviation", "military", "air"]
            description = "Military rotary-wing tactical assault and transport helicopter."
            affinities = ["airfield", "military_base"]
            suggested_density = "low"
            footprint_type = "circular"
        elif "jet" in name_lower:
            tags = ["jet", "fighter", "aircraft", "aviation", "military", "supersonic"]
            description = "Multi-role combat fighter jet aircraft."
            affinities = ["airfield", "military_base"]
            suggested_density = "low"
        else:
            tags = ["vehicle", "transport", "military", "truck", "logistics", "wheels"]
            description = "Tactical military wheeled transport vehicle."
            affinities = ["military_base", "depot", "outpost", "checkpoint"]
            suggested_density = "medium"
    elif "env_" in name_lower or "rock" in name_lower or "tree" in name_lower or "ground" in name_lower or "grass" in name_lower:
        category = "environment"
        placement_role = "foliage"
        tags = ["nature", "rock", "terrain", "cover", "environment", "natural"]
        description = "Natural environmental terrain feature and organic cover."
        affinities = ["military_base", "outpost", "airfield", "depot", "checkpoint"]
        suggested_density = "medium"
    elif "debris" in name_lower or "rubble" in name_lower:
        category = "decorations"
        placement_role = "prop"
        tags = ["debris", "rubble", "ruins", "combat_damage", "destroyed"]
        description = "Combat blast debris and rubble scatter."
        affinities = ["military_base", "outpost", "checkpoint", "depot"]
        suggested_density = "high"
    elif "sm_prop_" in name_lower:
        category = "decorations"
        placement_role = "prop"
        tags = ["prop", "military", "utility", "tactical"]
        description = f"Military compound utility prop: {asset_name}."
        affinities = ["military_base", "outpost", "depot"]
        suggested_density = "medium"
    elif "sm_bld_" in name_lower:
        category = "structures"
        placement_role = "building"
        tags = ["building", "military", "structure", "compound"]
        description = f"Military base building structure: {asset_name}."
        affinities = ["military_base", "outpost"]
        suggested_density = "medium"

    if is_destroyed:
        if "destroyed" not in tags:
            tags.append("destroyed")
        if "ruins" not in tags:
            tags.append("ruins")
        if "battle_damage" not in tags:
            tags.append("battle_damage")
        description += " Shows severe combat destruction and structural damage."
        max_destruction_level = 4

    # Ensure tags array is unique
    unique_tags = []
    for t in tags:
        if t not in unique_tags:
            unique_tags.append(t)

    return {
        "category": category,
        "placement_role": placement_role,
        "tags": unique_tags,
        "description": description,
        "affinities": affinities,
        "suggested_density": suggested_density,
        "footprint_type": footprint_type,
        "stackable": stackable,
        "supported_factions": supported_factions,
        "max_destruction_level": max_destruction_level
    }


def enrich_asset_vlm(
    asset_name: str,
    dimensions: List[float],
    render_paths: Dict[str, str],
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen3.8:27b",
    timeout_sec: float = 15.0
) -> Dict[str, Any]:
    """
    Enriches asset metadata using local Ollama VLM vision inference.
    Falls back gracefully to the heuristic classifier on timeout or error.
    """
    fallback_data = heuristic_enrich_asset(asset_name, dimensions)

    # Encode images
    front_b64 = encode_image_base64(render_paths.get("front", ""))
    side_b64 = encode_image_base64(render_paths.get("side", ""))
    top_b64 = encode_image_base64(render_paths.get("top", ""))

    images = [img for img in [front_b64, side_b64, top_b64] if img is not None]
    if not images:
        return fallback_data

    prompt = f"""You are an expert 3D asset metadata classifier for procedural military game worlds.
Analyze the provided multi-angle renders (front, side, top) of the 3D asset '{asset_name}' with dimensions [W: {dimensions[0]:.2f}m, L: {dimensions[1]:.2f}m, H: {dimensions[2]:.2f}m].

Respond ONLY with a valid JSON object matching this schema:
{{
  "category": "structures" | "vehicles" | "environment" | "decorations" | "defenses" | "industrial",
  "placement_role": "building" | "prop" | "foliage" | "vehicle" | "road" | "fence" | "infrastructure" | "defensive_structure",
  "tags": ["string", ...],
  "description": "A concise description of the asset.",
  "affinities": ["military_base", "outpost", "airfield", "depot", "checkpoint", "radar_station"],
  "suggested_density": "low" | "medium" | "high",
  "footprint_type": "rectangular" | "circular" | "linear",
  "stackable": false,
  "supported_factions": ["A", "B", "C"],
  "max_destruction_level": 4
}}
"""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": images
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    try:
        req = urllib.request.Request(
            f"{ollama_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            parsed = parse_vlm_response(resp_data)
            if parsed and isinstance(parsed, dict) and "tags" in parsed and "category" in parsed:
                # Merge with fallbacks for missing keys
                for k, v in fallback_data.items():
                    if k not in parsed or parsed[k] is None:
                        parsed[k] = v
                # Ensure tags is list of strings
                if not isinstance(parsed.get("tags"), list) or len(parsed["tags"]) == 0:
                    parsed["tags"] = fallback_data["tags"]
                else:
                    parsed["tags"] = [str(t) for t in parsed["tags"]]
                return parsed
    except Exception as e:
        print(f"[VLMEnrich] Ollama inference skipped/failed ({e}), using heuristic.")

    return fallback_data
