with open("backend/app/generator/roads.py", "r") as f:
    content = f.read()

# Let's add zones to `_find_slope_aware_astar_path` signature
content = content.replace("def _find_slope_aware_astar_path(", "def _find_slope_aware_astar_path(\n    zones: List[Zone],")

# Let's add obstacle penalty
replacement = """
    # Create zone obstacle mask
    zone_obstacles = np.zeros((res_y, res_x), dtype=bool)
    for z in zones:
        zx = int(round((z.center[0] / world_w) * (res_x - 1)))
        zz = int(round((z.center[2] / world_l) * (res_y - 1)))
        zr = int(round((z.radius / world_w) * (res_x - 1)))
        # Only mask inner core (e.g. 50% of radius) to avoid blocking
        for dx in range(-zr, zr+1):
            for dz in range(-zr, zr+1):
                if dx*dx + dz*dz <= (zr*0.5)**2:
                    if 0 <= zx+dx < res_x and 0 <= zz+dz < res_y:
                        zone_obstacles[zz+dz, zx+dx] = True
    
    # Allow start and goal to be inside obstacle
    for dx in range(-5, 6):
        for dz in range(-5, 6):
            if 0 <= sx+dx < res_x and 0 <= sz+dz < res_y:
                zone_obstacles[sz+dz, sx+dx] = False
            if 0 <= gx+dx < res_x and 0 <= gz+dz < res_y:
                zone_obstacles[gz+dz, gx+dx] = False

    def get_h(ix: int, iz: int) -> float:
"""
content = content.replace("    def get_h(ix: int, iz: int) -> float:", replacement)

replacement_penalty = """
            # Cost formulation: d * (1 + 20*G^2 + 1000*(G > Gmax) + 10000*(h < water))
            penalty = 1.0 + slope_weight * (grade * grade)
            if grade > max_grade:
                penalty += 1000.0 * (grade - max_grade)
            if next_h < water_level:
                penalty += 10000.0
            if zone_obstacles[nz, nx]:
                penalty += 5000.0
"""
content = content.replace("""
            # Cost formulation: d * (1 + 20*G^2 + 1000*(G > Gmax) + 10000*(h < water))
            penalty = 1.0 + slope_weight * (grade * grade)
            if grade > max_grade:
                penalty += 1000.0 * (grade - max_grade)
            if next_h < water_level:
                penalty += 10000.0""", replacement_penalty)

# And pass zones in generate_roads
content = content.replace("waypoints_3d = _find_slope_aware_astar_path(", "waypoints_3d = _find_slope_aware_astar_path(\n            zones=zones,")

with open("backend/app/generator/roads.py", "w") as f:
    f.write(content)
