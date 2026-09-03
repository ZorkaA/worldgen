import sys

with open("backend/app/api/routes.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if "existing_zones=request.zones or request.zones_list or request.existing_zones" in line:
        pass # Wait, we need to do this BEFORE gen_req is created!

with open("backend/app/api/routes.py", "r") as f:
    content = f.read()

replacement = """
    effective_seed = request.seed if request.seed is not None else 42

    active_zones = request.zones or request.zones_list or request.existing_zones
    if active_zones is None and _active_manifest:
        active_zones = _active_manifest.zones

    if active_zones and request.zone_id and request.new_position:
        for z in active_zones:
            if z.id == request.zone_id:
                z.center = request.new_position
                break

    # Map RecomputeRequest to GenerateWorldRequest
    gen_req = GenerateWorldRequest(
        seed=effective_seed,
        terrain=request.terrain,
        existing_zones=active_zones,
"""

content = content.replace("""
    effective_seed = request.seed if request.seed is not None else 42

    # Map RecomputeRequest to GenerateWorldRequest
    gen_req = GenerateWorldRequest(
        seed=effective_seed,
        terrain=request.terrain,
        existing_zones=request.zones or request.zones_list or request.existing_zones,""", replacement)

with open("backend/app/api/routes.py", "w") as f:
    f.write(content)
