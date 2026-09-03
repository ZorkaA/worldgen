with open("backend/app/generator/pipeline.py", "r") as f:
    content = f.read()

replacement = """    # 6. Slope-Aware A* Road Network Routing & Spline Smoothing
    t0 = time.perf_counter()
    roads = []
    do_roads = getattr(terrain_config, "generate_roads", True)
    if hasattr(request, "generate_roads") and request.generate_roads is not None:
        do_roads = request.generate_roads

    if do_roads:
        roads = generate_roads(
            heightmap=flattened_heightmap,
            zones=zones,
            terrain_config=terrain_config,
            seed=uint_seed,
        )
    t_roads = time.perf_counter() - t0"""

old = """    # 6. Slope-Aware A* Road Network Routing & Spline Smoothing
    t0 = time.perf_counter()
    roads = generate_roads(
        heightmap=flattened_heightmap,
        zones=zones,
        terrain_config=terrain_config,
        seed=uint_seed,
    )
    t_roads = time.perf_counter() - t0"""

content = content.replace(old, replacement)

with open("backend/app/generator/pipeline.py", "w") as f:
    f.write(content)
print("Pipeline patched for real.")
