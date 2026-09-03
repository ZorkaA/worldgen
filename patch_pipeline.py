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
content = content.replace("""
    # 7. Generate roads between zones
    roads = generate_roads(
        heightmap=flattened_heightmap,
        zones=zones,
        terrain_config=terrain_config,
        seed=seed
    )""", replacement)

with open("backend/app/generator/pipeline.py", "w") as f:
    f.write(content)
