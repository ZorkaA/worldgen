"""Slope-Aware A* Road Network Pathfinding and Catmull-Rom Spline Smoothing."""

import heapq
import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Set
from scipy.spatial import Delaunay

from ..core.schemas import RoadSegment, Zone, TerrainConfig
from .zones import _sample_heightmap_bilinear


def _sample_terrain_straight_line(
    heightmap: np.ndarray,
    start_world: Tuple[float, float],
    goal_world: Tuple[float, float],
    world_w: float,
    world_l: float,
    sample_spacing: float = 8.0,
) -> List[List[float]]:
    """Sample the heightmap along a straight line every sample_spacing meters (5-10m)."""
    dx = goal_world[0] - start_world[0]
    dz = goal_world[1] - start_world[1]
    dist = math.hypot(dx, dz)
    num_steps = max(2, int(math.ceil(dist / max(1.0, sample_spacing))))
    waypoints: List[List[float]] = []
    for s in range(num_steps + 1):
        t = s / float(num_steps)
        wx = start_world[0] + dx * t
        wz = start_world[1] + dz * t
        wy = _sample_heightmap_bilinear(heightmap, wx, wz, world_w, world_l)
        waypoints.append([round(wx, 2), round(wy + 0.15, 2), round(wz, 2)])
    return waypoints


def _catmull_rom_spline(
    points: List[Tuple[float, float, float]],
    num_samples_per_seg: Optional[int] = None,
    sample_spacing: float = 8.0,
) -> List[Tuple[float, float, float]]:
    """Compute 3D Catmull-Rom spline interpolation through waypoints with dense terrain elevation sampling."""
    if len(points) < 2:
        return points

    # Duplicate start and end for boundary conditions
    p = [points[0]] + list(points) + [points[-1]]
    spline_pts: List[Tuple[float, float, float]] = []

    for i in range(1, len(p) - 2):
        p0 = p[i - 1]
        p1 = p[i]
        p2 = p[i + 1]
        p3 = p[i + 2]

        seg_dist = math.hypot(p2[0] - p1[0], p2[2] - p1[2])
        if num_samples_per_seg is not None:
            n_samples = max(num_samples_per_seg, int(math.ceil(seg_dist / max(1.0, sample_spacing))))
        else:
            n_samples = max(2, int(math.ceil(seg_dist / max(1.0, sample_spacing))))

        for s in range(n_samples):
            t = s / float(n_samples)
            t2 = t * t
            t3 = t2 * t

            # Standard Catmull-Rom matrix coefficients
            x = 0.5 * (
                (2.0 * p1[0]) +
                (-p0[0] + p2[0]) * t +
                (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * t2 +
                (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2.0 * p1[1]) +
                (-p0[1] + p2[1]) * t +
                (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * t2 +
                (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * t3
            )
            z = 0.5 * (
                (2.0 * p1[2]) +
                (-p0[2] + p2[2]) * t +
                (2.0 * p0[2] - 5.0 * p1[2] + 4.0 * p2[2] - p3[2]) * t2 +
                (-p0[2] + 3.0 * p1[2] - 3.0 * p2[2] + p3[2]) * t3
            )
            spline_pts.append((x, y, z))

    spline_pts.append(points[-1])
    return spline_pts


def _rdp_simplify_2d(
    points: List[Tuple[float, float]],
    epsilon: float = 2.0,
) -> List[Tuple[float, float]]:
    """Ramer-Douglas-Peucker 2D polyline simplification."""
    if len(points) <= 2:
        return points

    p_start = np.array(points[0])
    p_end = np.array(points[-1])
    line_vec = p_end - p_start
    line_len = np.linalg.norm(line_vec)

    max_dist = 0.0
    index = 0

    if line_len > 1e-6:
        line_unit = line_vec / line_len
        for i in range(1, len(points) - 1):
            p = np.array(points[i])
            v = p - p_start
            proj = np.dot(v, line_unit)
            proj = np.clip(proj, 0.0, line_len)
            closest = p_start + proj * line_unit
            d = np.linalg.norm(p - closest)
            if d > max_dist:
                max_dist = d
                index = i
    else:
        for i in range(1, len(points) - 1):
            d = np.linalg.norm(np.array(points[i]) - p_start)
            if d > max_dist:
                max_dist = d
                index = i

    if max_dist > epsilon:
        left = _rdp_simplify_2d(points[:index + 1], epsilon)
        right = _rdp_simplify_2d(points[index:], epsilon)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


def _find_slope_aware_astar_path(
    zones: List[Zone],
    heightmap: np.ndarray,
    start_world: Tuple[float, float],
    goal_world: Tuple[float, float],
    terrain_config: TerrainConfig,
    water_level: float = 2.0,
    slope_weight: float = 20.0,
    max_grade: float = 0.25,
) -> List[Tuple[float, float, float]]:
    """A* grid pathfinding with quadratic slope cost penalty."""
    orig_res_y, orig_res_x = heightmap.shape
    world_w = terrain_config.world_size[0]
    world_l = terrain_config.world_size[2]

    # Stride factor to optimize grid search on large resolutions (e.g. 513)
    stride = 2 if orig_res_x >= 513 else 1
    res_x = (orig_res_x - 1) // stride + 1
    res_y = (orig_res_y - 1) // stride + 1

    # Convert world coordinates to grid cell coordinates
    sx = int(round((start_world[0] / world_w) * (res_x - 1)))
    sz = int(round((start_world[1] / world_l) * (res_y - 1)))
    gx = int(round((goal_world[0] / world_w) * (res_x - 1)))
    gz = int(round((goal_world[1] / world_l) * (res_y - 1)))

    sx = max(0, min(res_x - 1, sx))
    sz = max(0, min(res_y - 1, sz))
    gx = max(0, min(res_x - 1, gx))
    gz = max(0, min(res_y - 1, gz))

    cell_w = world_w / (res_x - 1)
    cell_l = world_l / (res_y - 1)
    diag_dist = math.sqrt(cell_w * cell_w + cell_l * cell_l)

    # 8-connected neighbor offsets
    neighbors = [
        (1, 0, cell_w), (-1, 0, cell_w),
        (0, 1, cell_l), (0, -1, cell_l),
        (1, 1, diag_dist), (-1, 1, diag_dist),
        (1, -1, diag_dist), (-1, -1, diag_dist),
    ]


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

        return float(heightmap[iz * stride, ix * stride])

    def heuristic(cx: int, cz: int) -> float:
        dx = (cx - gx) * cell_w
        dz = (cz - gz) * cell_l
        dh = get_h(cx, cz) - get_h(gx, gz)
        return math.sqrt(dx * dx + dz * dz + dh * dh)

    # Priority queue storing (f_score, h_score, (cx, cz))
    open_set = []
    start_h = heuristic(sx, sz)
    heapq.heappush(open_set, (start_h, start_h, (sx, sz)))

    g_score: Dict[Tuple[int, int], float] = {(sx, sz): 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    visited = set()

    max_expansions = 250000
    expansions = 0

    while open_set and expansions < max_expansions:
        expansions += 1
        f, h_val, current = heapq.heappop(open_set)
        cx, cz = current

        if current in visited:
            continue
        visited.add(current)

        if (cx, cz) == (gx, gz) or (abs(cx - gx) <= 1 and abs(cz - gz) <= 1):
            came_from[(gx, gz)] = current
            break

        cur_g = g_score[(cx, cz)]
        cur_h = get_h(cx, cz)

        for ndx, ndz, step_dist in neighbors:
            nx, nz = cx + ndx, cz + ndz
            if nx < 0 or nx >= res_x or nz < 0 or nz >= res_y:
                continue

            neighbor_pos = (nx, nz)
            if neighbor_pos in visited:
                continue

            next_h = get_h(nx, nz)
            dz = next_h - cur_h
            grade = abs(dz) / max(1e-4, step_dist)

            # Cost formulation: d * (1 + 20*G^2 + 1000*(G > Gmax) + 10000*(h < water))
            penalty = 1.0 + slope_weight * (grade * grade)
            if grade > max_grade:
                penalty += 1000.0 * (grade - max_grade)
            if next_h < water_level:
                penalty += 10000.0
            if zone_obstacles[nz, nx]:
                penalty += 5000.0


            tentative_g = cur_g + step_dist * penalty

            if tentative_g < g_score.get(neighbor_pos, float("inf")):
                came_from[neighbor_pos] = (cx, cz)
                g_score[neighbor_pos] = tentative_g
                h_new = heuristic(nx, nz)
                heapq.heappush(open_set, (tentative_g + h_new, h_new, neighbor_pos))

    # If goal was never reached, fallback to heightmap-sampled straight line
    if (gx, gz) not in came_from and (gx, gz) != (sx, sz):
        return _sample_terrain_straight_line(
            heightmap=heightmap,
            start_world=start_world,
            goal_world=goal_world,
            world_w=world_w,
            world_l=world_l,
            sample_spacing=8.0,
        )

    # Reconstruct path
    curr = (gx, gz)
    path_grid = [curr]
    while curr in came_from:
        curr = came_from[curr]
        path_grid.append(curr)
        if curr == (sx, sz):
            break
    path_grid.reverse()

    if not path_grid or path_grid[0] != (sx, sz):
        return _sample_terrain_straight_line(
            heightmap=heightmap,
            start_world=start_world,
            goal_world=goal_world,
            world_w=world_w,
            world_l=world_l,
            sample_spacing=8.0,
        )

    # Convert grid points to world points (2D)
    points_2d = [
        ((px / (res_x - 1)) * world_w, (pz / (res_y - 1)) * world_l)
        for px, pz in path_grid
    ]

    # Simplify using RDP
    simplified_2d = _rdp_simplify_2d(points_2d, epsilon=2.5)

    # Convert to 3D with continuous terrain elevation sampling
    waypoints_3d = []
    for wx, wz in simplified_2d:
        wy = _sample_heightmap_bilinear(heightmap, wx, wz, world_w, world_l)
        waypoints_3d.append((wx, wy + 0.15, wz))

    # Apply Catmull-Rom spline interpolation with 5-10m sample spacing
    smooth_waypoints = _catmull_rom_spline(waypoints_3d, sample_spacing=8.0)

    # Re-clamp height of spline points onto terrain
    final_waypoints = []
    for sx_pt, sy_pt, sz_pt in smooth_waypoints:
        hy = _sample_heightmap_bilinear(heightmap, sx_pt, sz_pt, world_w, world_l)
        final_waypoints.append([round(sx_pt, 2), round(hy + 0.15, 2), round(sz_pt, 2)])

    if len(final_waypoints) < 2:
        return _sample_terrain_straight_line(
            heightmap=heightmap,
            start_world=start_world,
            goal_world=goal_world,
            world_w=world_w,
            world_l=world_l,
            sample_spacing=8.0,
        )

    return final_waypoints


def _delaunay_triangulation_2d(points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    """2D Delaunay Triangulation using scipy.spatial.Delaunay."""
    num_pts = len(points)
    if num_pts < 2:
        return []
    if num_pts == 2:
        return [(0, 1)]

    pts = np.array(points, dtype=np.float64)
    try:
        tri = Delaunay(pts)
        edges: Set[Tuple[int, int]] = set()
        for simplex in tri.simplices:
            i0, i1, i2 = int(simplex[0]), int(simplex[1]), int(simplex[2])
            edges.add((min(i0, i1), max(i0, i1)))
            edges.add((min(i1, i2), max(i1, i2)))
            edges.add((min(i2, i0), max(i2, i0)))
        return list(edges)
    except Exception:
        # Fallback for collinear/degenerate point sets: sort along principal coordinate
        sorted_indices = sorted(range(num_pts), key=lambda i: (points[i][0], points[i][1]))
        fallback_edges: List[Tuple[int, int]] = []
        for i in range(num_pts - 1):
            u, v = sorted_indices[i], sorted_indices[i + 1]
            if u != v:
                edge = (min(u, v), max(u, v))
                if edge not in fallback_edges:
                    fallback_edges.append(edge)
        return fallback_edges if fallback_edges else ([(0, 1)] if num_pts >= 2 else [])


def _generate_zone_edges(zones: List[Zone], seed: int = 42) -> List[Tuple[int, int]]:
    """Compute Euclidean Minimum Spanning Tree (EMST) + 30% random Delaunay edges."""
    num_zones = len(zones)
    if num_zones < 2:
        return []
    if num_zones == 2:
        return [(0, 1)]

    coords = [(float(z.center[0]), float(z.center[2])) for z in zones]
    delaunay_edges = _delaunay_triangulation_2d(coords)

    if not delaunay_edges:
        return [(i, i + 1) for i in range(num_zones - 1)]

    # Kruskal's MST algorithm
    edge_weights = []
    for u, v in delaunay_edges:
        p1, p2 = coords[u], coords[v]
        dist = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        edge_weights.append((dist, u, v))

    edge_weights.sort(key=lambda x: x[0])

    parent = list(range(num_zones))

    def find_p(i: int) -> int:
        if parent[i] == i:
            return i
        parent[i] = find_p(parent[i])
        return parent[i]

    def union_p(i: int, j: int) -> bool:
        root_i = find_p(i)
        root_j = find_p(j)
        if root_i != root_j:
            parent[root_i] = root_j
            return True
        return False

    mst_edges: Set[Tuple[int, int]] = set()
    remaining_edges: List[Tuple[int, int]] = []

    for dist, u, v in edge_weights:
        edge = (min(u, v), max(u, v))
        if union_p(u, v):
            mst_edges.add(edge)
        else:
            remaining_edges.append(edge)

    # Add 30% of remaining Delaunay edges for tactical loops
    rng = np.random.RandomState((int(seed) + 500) & 0x7FFFFFFF)
    extra_count = int(math.ceil(len(remaining_edges) * 0.30))
    if extra_count > 0 and remaining_edges:
        indices = rng.choice(len(remaining_edges), size=min(extra_count, len(remaining_edges)), replace=False)
        for idx in indices:
            mst_edges.add(remaining_edges[idx])

    return list(mst_edges)


def compute_max_observed_slope(waypoints: List[List[float]]) -> float:
    """Computes the maximum vertical slope (rise / run) along consecutive waypoints."""
    slopes: List[float] = []
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]
        dx = p2[0] - p1[0]
        dz = p2[2] - p1[2] if len(p2) >= 3 else p2[1] - p1[1]
        dy = abs(p2[1] - p1[1]) if len(p2) >= 3 else 0.0
        dist = math.hypot(dx, dz)
        if dist > 1e-4:
            slopes.append(dy / dist)
    return float(max(slopes)) if slopes else 0.0


def generate_roads(
    heightmap: np.ndarray,
    zones: List[Zone],
    terrain_config: TerrainConfig,
    seed: int = 42,
) -> List[RoadSegment]:
    """Generate slope-aware road network connecting military zones.

    Returns a list of RoadSegment models.
    """
    if len(zones) < 2:
        return []

    edges = _generate_zone_edges(zones, seed=seed)
    roads: List[RoadSegment] = []
    max_slope_limit = getattr(terrain_config, "max_road_slope", 0.25) or 0.25

    for edge_idx, (u_idx, v_idx) in enumerate(edges):
        zone_u = zones[u_idx]
        zone_v = zones[v_idx]

        start_pt = (zone_u.center[0], zone_u.center[2])
        goal_pt = (zone_v.center[0], zone_v.center[2])

        waypoints_3d = _find_slope_aware_astar_path(
            zones=zones,
            heightmap=heightmap,
            start_world=start_pt,
            goal_world=goal_pt,
            terrain_config=terrain_config,
            water_level=2.0,
            slope_weight=200.0,
            max_grade=max_slope_limit,
        )

        formatted_waypoints = [[p[0], p[1], p[2]] for p in waypoints_3d]
        max_slope_obs = compute_max_observed_slope(formatted_waypoints)

        road_seg = RoadSegment(
            id=f"road_{zone_u.id}_{zone_v.id}",
            from_zone=zone_u.id,
            to_zone=zone_v.id,
            width=6.0,
            waypoints=formatted_waypoints,
            max_slope_observed=round(max_slope_obs, 3),
        )
        roads.append(road_seg)

    return roads
