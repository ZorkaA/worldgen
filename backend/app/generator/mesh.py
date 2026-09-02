"""Slope and Curvature-Adaptive Terrain Mesh Decimation."""

import math
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from ..core.schemas import DecimatedMesh


def generate_adaptive_mesh(
    heightmap: np.ndarray,
    world_size: List[float],
    max_error: float = 1.0,
    min_cell_size: int = 1,
) -> DecimatedMesh:
    """Quadtree-based slope/curvature adaptive terrain mesh decimator.

    Recursively subdivides heightmap quad cells where vertical height error > max_error.
    Produces variable-density indexed triangle mesh with watertight boundaries.

    Args:
        heightmap: 2D NumPy array of shape (res_z, res_x) containing elevation in meters.
        world_size: [world_width, height_scale, world_length] in meters.
        max_error: Max vertical height deviation (in meters) before subdividing a quad.
        min_cell_size: Minimum grid cell resolution (in grid units).

    Returns:
        DecimatedMesh Pydantic model with vertices, indices, normals, UVs, and decimation statistics.
    """
    res_z, res_x = heightmap.shape
    world_w, world_h, world_l = float(world_size[0]), float(world_size[1]), float(world_size[2])

    vertex_map: Dict[Tuple[int, int], int] = {}
    vertices: List[List[float]] = []
    normals: List[List[float]] = []
    uvs: List[List[float]] = []
    triangles: List[int] = []

    scale_x = (2.0 * world_w) / max(1, res_x - 1)
    scale_z = (2.0 * world_l) / max(1, res_z - 1)

    def get_or_create_vertex(gx: int, gz: int) -> int:
        key = (gx, gz)
        if key in vertex_map:
            return vertex_map[key]

        wx = (gx / float(res_x - 1)) * world_w
        wz = (gz / float(res_z - 1)) * world_l
        wy = float(heightmap[gz, gx])

        # Compute normal via central differences
        dx_h = float(heightmap[gz, min(res_x - 1, gx + 1)]) - float(heightmap[gz, max(0, gx - 1)])
        dz_h = float(heightmap[min(res_z - 1, gz + 1), gx]) - float(heightmap[max(0, gz - 1), gx])

        norm_vec = np.array([-dx_h / scale_x, 1.0, -dz_h / scale_z], dtype=np.float64)
        norm_len = np.linalg.norm(norm_vec)
        if norm_len > 1e-6:
            norm_vec /= norm_len
        else:
            norm_vec = np.array([0.0, 1.0, 0.0])

        idx = len(vertices)
        vertices.append([round(wx, 3), round(wy, 3), round(wz, 3)])
        normals.append([round(float(norm_vec[0]), 4), round(float(norm_vec[1]), 4), round(float(norm_vec[2]), 4)])
        uvs.append([round(gx / float(res_x - 1), 4), round(gz / float(res_z - 1), 4)])
        vertex_map[key] = idx
        return idx

    def evaluate_quad_error(x0: int, z0: int, x1: int, z1: int) -> float:
        """Computes max vertical deviation from bilinear interpolation plane."""
        if x1 - x0 <= min_cell_size and z1 - z0 <= min_cell_size:
            return 0.0

        h00 = heightmap[z0, x0]
        h10 = heightmap[z0, x1]
        h01 = heightmap[z1, x0]
        h11 = heightmap[z1, x1]

        sub_h = heightmap[z0 : z1 + 1, x0 : x1 + 1]
        sz_z, sz_x = sub_h.shape
        if sz_z <= 1 or sz_x <= 1:
            return 0.0

        xs = np.linspace(0.0, 1.0, sz_x)
        zs = np.linspace(0.0, 1.0, sz_z)
        gx, gz = np.meshgrid(xs, zs)

        # Bilinear interpolation plane
        interp = (
            h00 * (1.0 - gx) * (1.0 - gz)
            + h10 * gx * (1.0 - gz)
            + h01 * (1.0 - gx) * gz
            + h11 * gx * gz
        )
        error = np.max(np.abs(sub_h - interp))
        return float(error)

    leaf_quads: List[Tuple[int, int, int, int]] = []

    def subdivide(x0: int, z0: int, x1: int, z1: int):
        if x1 <= x0 or z1 <= z0:
            return

        can_split_x = (x1 - x0 > min_cell_size) and (x1 - x0 >= 2)
        can_split_z = (z1 - z0 > min_cell_size) and (z1 - z0 >= 2)

        err = evaluate_quad_error(x0, z0, x1, z1)
        if err > max_error and (can_split_x or can_split_z):
            if can_split_x and can_split_z:
                xm = (x0 + x1) // 2
                zm = (z0 + z1) // 2
                subdivide(x0, z0, xm, zm)
                subdivide(xm, z0, x1, zm)
                subdivide(x0, zm, xm, z1)
                subdivide(xm, zm, x1, z1)
            elif can_split_x:
                xm = (x0 + x1) // 2
                subdivide(x0, z0, xm, z1)
                subdivide(xm, z0, x1, z1)
            elif can_split_z:
                zm = (z0 + z1) // 2
                subdivide(x0, z0, x1, zm)
                subdivide(x0, zm, x1, z1)
        else:
            # Register corner vertices
            get_or_create_vertex(x0, z0)
            get_or_create_vertex(x1, z0)
            get_or_create_vertex(x0, z1)
            get_or_create_vertex(x1, z1)
            leaf_quads.append((x0, z0, x1, z1))

    subdivide(0, 0, res_x - 1, res_z - 1)

    def get_quad_perimeter_vertices(x0: int, z0: int, x1: int, z1: int) -> List[int]:
        # CCW order in XZ:
        # Left edge: (x0, z) for z in z0..z1
        left_pts = [(x0, z) for z in range(z0, z1 + 1) if (x0, z) in vertex_map]
        left_pts.sort(key=lambda p: p[1])

        # Bottom edge: (x, z1) for x in x0..x1
        bottom_pts = [(x, z1) for x in range(x0, x1 + 1) if (x, z1) in vertex_map]
        bottom_pts.sort(key=lambda p: p[0])

        # Right edge: (x1, z) for z in z1..z0
        right_pts = [(x1, z) for z in range(z0, z1 + 1) if (x1, z) in vertex_map]
        right_pts.sort(key=lambda p: p[1], reverse=True)

        # Top edge: (x, z0) for x in x1..x0
        top_pts = [(x, z0) for x in range(x0, x1 + 1) if (x, z0) in vertex_map]
        top_pts.sort(key=lambda p: p[0], reverse=True)

        ordered_keys: List[Tuple[int, int]] = []
        for p in left_pts + bottom_pts + right_pts + top_pts:
            if not ordered_keys or p != ordered_keys[-1]:
                ordered_keys.append(p)
        if len(ordered_keys) > 1 and ordered_keys[0] == ordered_keys[-1]:
            ordered_keys.pop()

        return [vertex_map[k] for k in ordered_keys]

    # Emit watertight manifold triangles
    for x0, z0, x1, z1 in leaf_quads:
        poly = get_quad_perimeter_vertices(x0, z0, x1, z1)
        if len(poly) == 4:
            v00, v01, v11, v10 = poly[0], poly[1], poly[2], poly[3]
            if v00 != v01 and v00 != v10 and v01 != v10:
                triangles.extend([v00, v01, v10])
            if v10 != v01 and v10 != v11 and v01 != v11:
                triangles.extend([v10, v01, v11])
        elif len(poly) > 4:
            xm = (x0 + x1) // 2
            zm = (z0 + z1) // 2
            vm = get_or_create_vertex(xm, zm)
            for k in range(len(poly)):
                k_next = (k + 1) % len(poly)
                v_curr = poly[k]
                v_next = poly[k_next]
                if v_curr != v_next and v_curr != vm and v_next != vm:
                    triangles.extend([vm, v_curr, v_next])

    full_grid_triangles = 2 * (res_x - 1) * (res_z - 1)
    actual_triangles = len(triangles) // 3
    decimation_ratio = round(actual_triangles / max(1, full_grid_triangles), 4)

    return DecimatedMesh(
        vertices=vertices,
        indices=triangles,
        normals=normals,
        uvs=uvs,
        vertex_count=len(vertices),
        triangle_count=actual_triangles,
        full_grid_triangles=full_grid_triangles,
        decimation_ratio=decimation_ratio,
    )
