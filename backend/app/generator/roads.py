"""Slope-Aware A* Road Network Pathfinding and Catmull-Rom Spline Smoothing."""

import heapq
import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Set

from ..core.schemas import RoadSegment, Zone, TerrainConfig
from .zones import _sample_heightmap_bilinear


def _catmull_rom_spline(
    points: List[Tuple[float, float, float]],
    num_samples_per_seg: int = 6,
) -> List[Tuple[float, float, float]]:
    """Compute 3D Catmull-Rom spline interpolation through waypoints."""
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

        for s in range(num_samples_per_seg):
            t = s / float(num_samples_per_seg)
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

    max_expansions = 12000
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

            tentative_g = cur_g + step_dist * penalty

            if tentative_g < g_score.get(neighbor_pos, float("inf")):
                came_from[neighbor_pos] = (cx, cz)
                g_score[neighbor_pos] = tentative_g
                h_new = heuristic(nx, nz)
                heapq.heappush(open_set, (tentative_g + h_new, h_new, neighbor_pos))

    # Reconstruct path
    curr = (gx, gz)
    path_grid = [curr]
    while curr in came_from:
        curr = came_from[curr]
        path_grid.append(curr)
        if curr == (sx, sz):
            break
    path_grid.reverse()

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

    # Apply Catmull-Rom spline interpolation
    smooth_waypoints = _catmull_rom_spline(waypoints_3d, num_samples_per_seg=4)

    # Re-clamp height of spline points onto terrain
    final_waypoints = []
    for sx_pt, sy_pt, sz_pt in smooth_waypoints:
        hy = _sample_heightmap_bilinear(heightmap, sx_pt, sz_pt, world_w, world_l)
        final_waypoints.append([round(sx_pt, 2), round(hy + 0.15, 2), round(sz_pt, 2)])

    if len(final_waypoints) < 2:
        start_h = _sample_heightmap_bilinear(heightmap, start_world[0], start_world[1], world_w, world_l)
        goal_h = _sample_heightmap_bilinear(heightmap, goal_world[0], goal_world[1], world_w, world_l)
        final_waypoints = [
            [round(start_world[0], 2), round(start_h + 0.15, 2), round(start_world[1], 2)],
            [round(goal_world[0], 2), round(goal_h + 0.15, 2), round(goal_world[1], 2)],
        ]

    return final_waypoints


def _delaunay_triangulation_2d(points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    """Pure Python / NumPy Bowyer-Watson 2D Delaunay Triangulation."""
    num_pts = len(points)
    if num_pts < 2:
        return []
    if num_pts == 2:
        return [(0, 1)]
    if num_pts == 3:
        return [(0, 1), (1, 2), (0, 2)]

    pts = np.array(points, dtype=np.float64)

    min_x, min_y = np.min(pts, axis=0) - 100.0
    max_x, max_y = np.max(pts, axis=0) + 100.0
    dx = max_x - min_x
    dy = max_y - min_y
    dmax = max(dx, dy)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0

    st_p1 = (mid_x - 20.0 * dmax, mid_y - dmax)
    st_p2 = (mid_x, mid_y + 20.0 * dmax)
    st_p3 = (mid_x + 20.0 * dmax, mid_y - dmax)

    all_pts = list(points) + [st_p1, st_p2, st_p3]
    st_indices = {num_pts, num_pts + 1, num_pts + 2}

    triangles: List[Tuple[int, int, int]] = [(num_pts, num_pts + 1, num_pts + 2)]

    def in_circumcircle(p_idx: int, tri: Tuple[int, int, int]) -> bool:
        ax, ay = all_pts[tri[0]]
        bx, by = all_pts[tri[1]]
        cx, cy = all_pts[tri[2]]
        d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-9:
            return False
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
        r_sq = (ax - ux) ** 2 + (ay - uy) ** 2
        px, py = all_pts[p_idx]
        dist_sq = (px - ux) ** 2 + (py - uy) ** 2
        return dist_sq <= r_sq

    for i in range(num_pts):
        bad_triangles = []
        for tri in triangles:
            if in_circumcircle(i, tri):
                bad_triangles.append(tri)

        polygon_edges: List[Tuple[int, int]] = []
        for tri in bad_triangles:
            edges = [
                (min(tri[0], tri[1]), max(tri[0], tri[1])),
                (min(tri[1], tri[2]), max(tri[1], tri[2])),
                (min(tri[2], tri[0]), max(tri[2], tri[0])),
            ]
            for edge in edges:
                shared = False
                for other_tri in bad_triangles:
                    if other_tri == tri:
                        continue
                    other_edges = [
                        (min(other_tri[0], other_tri[1]), max(other_tri[0], other_tri[1])),
                        (min(other_tri[1], other_tri[2]), max(other_tri[1], other_tri[2])),
                        (min(other_tri[2], other_tri[0]), max(other_tri[2], other_tri[0])),
                    ]
                    if edge in other_edges:
                        shared = True
                        break
                if not shared:
                    polygon_edges.append(edge)

        triangles = [t for t in triangles if t not in bad_triangles]

        for edge in polygon_edges:
            triangles.append((edge[0], edge[1], i))

    final_edges: Set[Tuple[int, int]] = set()
    for tri in triangles:
        if not (tri[0] in st_indices or tri[1] in st_indices or tri[2] in st_indices):
            final_edges.add((min(tri[0], tri[1]), max(tri[0], tri[1])))
            final_edges.add((min(tri[1], tri[2]), max(tri[1], tri[2])))
            final_edges.add((min(tri[2], tri[0]), max(tri[2], tri[0])))

    return list(final_edges)


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

    for edge_idx, (u_idx, v_idx) in enumerate(edges):
        zone_u = zones[u_idx]
        zone_v = zones[v_idx]

        start_pt = (zone_u.center[0], zone_u.center[2])
        goal_pt = (zone_v.center[0], zone_v.center[2])

        waypoints_3d = _find_slope_aware_astar_path(
            heightmap=heightmap,
            start_world=start_pt,
            goal_world=goal_pt,
            terrain_config=terrain_config,
            water_level=2.0,
            slope_weight=20.0,
            max_grade=0.25,
        )

        formatted_waypoints = [[p[0], p[1], p[2]] for p in waypoints_3d]

        road_seg = RoadSegment(
            id=f"road_{zone_u.id}_{zone_v.id}",
            from_zone=zone_u.id,
            to_zone=zone_v.id,
            width=6.0,
            waypoints=formatted_waypoints,
        )
        roads.append(road_seg)

    return roads
