"""
Blender 2.83.3 CLI Headless Extraction Script.
Extracts 3D Axis-Aligned Bounding Boxes (AABB) and renders 3 canonical multi-angle
Workbench MatCap thumbnails (front, side, top) for 3D FBX assets.

Usage (invoked via Blender CLI):
    /Applications/Blender.app/Contents/MacOS/Blender \\
        --background \\
        --factory-startup \\
        -P backend/app/catalog/blender_extract.py \\
        -- \\
        --models-dir /path/to/PolygonMilitary/Models \\
        --renders-dir backend/app/catalog/renders \\
        --out-json backend/app/catalog/extracted_metrics.json
"""

import os
import sys
import math
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple

try:
    import bpy
    import mathutils
    IN_BLENDER = True
except ImportError:
    bpy = None
    mathutils = None
    IN_BLENDER = False


def setup_camera(
    scene: "bpy.types.Scene",
    cam_name: str = "CatalogRenderCam",
    fov_deg: float = 50.0
) -> "bpy.types.Object":
    """Create or reuse an auto-framing render camera."""
    cam_data = bpy.data.cameras.get(cam_name)
    if cam_data is None:
        cam_data = bpy.data.cameras.new(cam_name)
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(fov_deg)
    
    cam_obj = bpy.data.objects.get(cam_name)
    if cam_obj is None:
        cam_obj = bpy.data.objects.new(cam_name, cam_data)
        scene.collection.objects.link(cam_obj)
    
    scene.camera = cam_obj
    return cam_obj


def look_at(cam_obj: "bpy.types.Object", target_pos: "mathutils.Vector", eye_pos: "mathutils.Vector") -> None:
    """Orient camera to look directly at target_pos from eye_pos."""
    cam_obj.location = eye_pos
    direction = target_pos - eye_pos
    if direction.length > 1e-6:
        rot_quat = direction.to_track_quat("-Z", "Y")
        cam_obj.rotation_euler = rot_quat.to_euler()


def compute_world_bounds(scene: "bpy.types.Scene") -> Tuple[List[float], List[float], List[float], List[float], float, float]:
    """
    Computes combined world-space AABB across all MESH objects in the scene.
    Returns: (min_coord, max_coord, size, center, radius, ground_level_offset)
    """
    mesh_objs = [obj for obj in scene.objects if obj.type == "MESH"]
    if not mesh_objs:
        return (
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.5, 0.5, 0.5],
            0.866,
            0.0
        )

    min_coord = [float("inf")] * 3
    max_coord = [float("-inf")] * 3

    for obj in mesh_objs:
        for corner in obj.bound_box:
            world_pt = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_coord[i] = min(min_coord[i], float(world_pt[i]))
                max_coord[i] = max(max_coord[i], float(world_pt[i]))

    # Clean near-zero precision artifacts
    min_coord = [0.0 if abs(c) < 1e-5 else c for c in min_coord]
    max_coord = [0.0 if abs(c) < 1e-5 else c for c in max_coord]

    size = [max(1e-4, max_coord[i] - min_coord[i]) for i in range(3)]
    center = [(min_coord[i] + max_coord[i]) / 2.0 for i in range(3)]
    radius = 0.5 * math.sqrt(sum(s ** 2 for s in size))
    ground_level_offset = -min_coord[2]

    return min_coord, max_coord, size, center, radius, ground_level_offset


def configure_workbench_render(scene: "bpy.types.Scene", resolution: int = 512) -> None:
    """Configure Workbench MatCap renderer for fast, crisp multi-angle renders."""
    scene.render.engine = "BLENDER_WORKBENCH"
    
    # Shading options
    if hasattr(scene.display, "shading"):
        scene.display.shading.light = "MATCAP"
        scene.display.shading.color_type = "OBJECT"
    
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render_multi_angle(
    scene: "bpy.types.Scene",
    cam_obj: "bpy.types.Object",
    center: List[float],
    radius: float,
    asset_name: str,
    renders_dir: str
) -> Dict[str, str]:
    """
    Renders 3 multi-angle views (front, side, top) and saves PNGs.
    Returns dictionary with relative and absolute render paths.
    """
    os.makedirs(renders_dir, exist_ok=True)
    center_vec = mathutils.Vector(center)
    fov = cam_obj.data.angle
    padding = 1.25
    dist = max(0.5, (radius / math.sin(fov / 2.0)) * padding)

    front_path = os.path.join(renders_dir, f"{asset_name}_front.png")
    side_path = os.path.join(renders_dir, f"{asset_name}_side.png")
    top_path = os.path.join(renders_dir, f"{asset_name}_top.png")

    # 1. Front View (azimuth 0 deg, slight elevation 15 deg)
    phi_front = math.radians(15.0)
    eye_front = mathutils.Vector((
        center[0],
        center[1] - dist * math.cos(phi_front),
        center[2] + dist * math.sin(phi_front)
    ))
    look_at(cam_obj, center_vec, eye_front)
    scene.render.filepath = front_path
    bpy.ops.render.render(write_still=True)

    # 2. Side View (azimuth 90 deg, slight elevation 15 deg)
    phi_side = math.radians(15.0)
    eye_side = mathutils.Vector((
        center[0] + dist * math.cos(phi_side),
        center[1],
        center[2] + dist * math.sin(phi_side)
    ))
    look_at(cam_obj, center_vec, eye_side)
    scene.render.filepath = side_path
    bpy.ops.render.render(write_still=True)

    # 3. Top View (elevation 75 deg)
    phi_top = math.radians(75.0)
    eye_top = mathutils.Vector((
        center[0],
        center[1] - dist * math.cos(phi_top),
        center[2] + dist * math.sin(phi_top)
    ))
    look_at(cam_obj, center_vec, eye_top)
    scene.render.filepath = top_path
    bpy.ops.render.render(write_still=True)

    return {
        "front": os.path.abspath(front_path),
        "side": os.path.abspath(side_path),
        "top": os.path.abspath(top_path),
        "rel_front": f"renders/{asset_name}_front.png",
        "rel_side": f"renders/{asset_name}_side.png",
        "rel_top": f"renders/{asset_name}_top.png",
    }


def process_fbx_file(
    fbx_path: str,
    renders_dir: str,
    resolution: int = 512,
    skip_render: bool = False
) -> Dict[str, Any]:
    """Process a single FBX file: load, compute bounds, render views."""
    asset_name = os.path.splitext(os.path.basename(fbx_path))[0]
    
    # Reset factory scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    
    # Import FBX
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    
    # Compute bounds
    min_c, max_c, size, center, radius, ground_offset = compute_world_bounds(scene)
    
    render_info = {}
    if not skip_render:
        cam_obj = setup_camera(scene, fov_deg=50.0)
        configure_workbench_render(scene, resolution=resolution)
        render_info = render_multi_angle(scene, cam_obj, center, radius, asset_name, renders_dir)
    
    return {
        "name": asset_name,
        "source_file": os.path.abspath(fbx_path),
        "bounding_box": {
            "min": [round(c, 3) for c in min_c],
            "max": [round(c, 3) for c in max_c],
            "size": [round(s, 3) for s in size],
            "dimensions": [round(s, 3) for s in size],
            "center": [round(c, 3) for c in center],
            "radius": round(radius, 3),
            "ground_level_offset": round(ground_offset, 3)
        },
        "render_paths": {
            "front": render_info.get("rel_front", f"renders/{asset_name}_front.png"),
            "side": render_info.get("rel_side", f"renders/{asset_name}_side.png"),
            "top": render_info.get("rel_top", f"renders/{asset_name}_top.png")
        },
        "thumbnails": {
            "front": render_info.get("rel_front", f"renders/{asset_name}_front.png"),
            "side": render_info.get("rel_side", f"renders/{asset_name}_side.png"),
            "top": render_info.get("rel_top", f"renders/{asset_name}_top.png")
        },
        "abs_render_paths": {
            "front": render_info.get("front", ""),
            "side": render_info.get("side", ""),
            "top": render_info.get("top", "")
        }
    }


def find_fbx_files(models_dir: str, filter_assets: Optional[List[str]] = None) -> List[str]:
    """Find FBX files matching filter or all in directory."""
    fbx_files = []
    if not os.path.exists(models_dir):
        return fbx_files

    for root, _, files in os.walk(models_dir):
        for f in sorted(files):
            if f.lower().endswith(".fbx"):
                base_name = os.path.splitext(f)[0]
                if filter_assets is None or base_name in filter_assets or f in filter_assets:
                    fbx_files.append(os.path.join(root, f))
    return fbx_files


def parse_cli_args() -> argparse.Namespace:
    """Parse command-line arguments passed after '--' in Blender invocation."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Headless Blender 3D Asset Extractor")
    parser.add_argument("--models-dir", type=str, default="/Users/jack/Downloads/assetripper_export/ExportedProject/Assets/PolygonMilitary/Models", help="Path to FBX models directory")
    parser.add_argument("--renders-dir", type=str, default="/Users/jack/worldgen/backend/app/catalog/renders", help="Directory to save rendered PNGs")
    parser.add_argument("--out-json", type=str, default="/Users/jack/worldgen/backend/app/catalog/extracted_metrics.json", help="Path to write output JSON")
    parser.add_argument("--assets", type=str, default="", help="Comma-separated list of asset names to extract")
    parser.add_argument("--single-file", type=str, default="", help="Path to single FBX file")
    parser.add_argument("--max-assets", type=int, default=0, help="Max assets to extract (0 for unlimited)")
    parser.add_argument("--resolution", type=int, default=512, help="Render resolution (default: 512)")
    parser.add_argument("--skip-renders", action="store_true", help="Skip rendering thumbnails")
    
    return parser.parse_args(argv)


def main() -> None:
    if not IN_BLENDER:
        print("[ERROR] blender_extract.py must be run inside Blender CLI environment.")
        print("Example: /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup -P backend/app/catalog/blender_extract.py -- [args]")
        sys.exit(1)

    args = parse_cli_args()
    os.makedirs(args.renders_dir, exist_ok=True)
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)

    filter_list = [a.strip() for a in args.assets.split(",") if a.strip()] if args.assets else None

    if args.single_file and os.path.isfile(args.single_file):
        files_to_process = [args.single_file]
    else:
        files_to_process = find_fbx_files(args.models_dir, filter_list)

    if args.max_assets > 0:
        files_to_process = files_to_process[:args.max_assets]

    print(f"[BlenderExtract] Found {len(files_to_process)} FBX files to process.")
    results: Dict[str, Any] = {}

    for idx, fbx_path in enumerate(files_to_process, 1):
        name = os.path.splitext(os.path.basename(fbx_path))[0]
        print(f"[{idx}/{len(files_to_process)}] Processing: {name}")
        try:
            metrics = process_fbx_file(
                fbx_path=fbx_path,
                renders_dir=args.renders_dir,
                resolution=args.resolution,
                skip_render=args.skip_renders
            )
            results[name] = metrics
        except Exception as e:
            print(f"[ERROR] Failed processing {fbx_path}: {e}")

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[BlenderExtract] Saved extracted metrics for {len(results)} assets to {args.out_json}")

    print("[BlenderExtract] Done.")


if __name__ == "__main__":
    main()
