import re

with open("backend/app/generator/pipeline.py", "r") as f:
    content = f.read()

replacement = """
    # 7. Generate roads between zones
    roads = []
    do_roads = getattr(terrain_config, "generate_roads", True)
    if hasattr(request, "generate_roads") and request.generate_roads is not None:
        do_roads = request.generate_roads

    if do_roads:
        roads = generate_roads(
            heightmap=flattened_heightmap,
            zones=zones,
            terrain_config=terrain_config,
            seed=seed
        )
"""

content = re.sub(r'    # [0-9]+\. Generate roads between zones\s+roads = generate_roads\(\s+heightmap=flattened_heightmap,\s+zones=zones,\s+terrain_config=terrain_config,\s+seed=seed\s+\)', replacement, content, flags=re.MULTILINE)

with open("backend/app/generator/pipeline.py", "w") as f:
    f.write(content)
print("Pipeline patched!")
