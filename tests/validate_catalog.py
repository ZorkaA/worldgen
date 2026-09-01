#!/usr/bin/env python3
"""
tests/validate_catalog.py - Standalone CLI validator for asset catalog JSON files.

Usage:
    python3 tests/validate_catalog.py <path/to/catalog.json>
    python3 tests/validate_catalog.py <path/to/catalog.json> --strict --json

Exit Codes:
    0: Catalog is 100% valid.
    1: Validation errors detected.
"""

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def is_valid_finite_float(val: Any) -> bool:
    """Checks if a value is a valid, finite float or int (not bool, NaN, Inf)."""
    if isinstance(val, bool) or val is None:
        return False
    if isinstance(val, (int, float)):
        return not (math.isnan(val) or math.isinf(val))
    return False


def validate_3d_vector(vec: Any, field_name: str, item_name: str) -> List[str]:
    """Validates a 3-element float array [x, y, z]."""
    errors: List[str] = []
    if not isinstance(vec, (list, tuple)):
        return [f"[{item_name}] {field_name} must be a list/tuple of 3 numbers, got {type(vec).__name__}"]
    if len(vec) != 3:
        return [f"[{item_name}] {field_name} must contain exactly 3 numbers, got {len(vec)} items: {vec}"]
    for idx, axis in enumerate(["x", "y", "z"]):
        val = vec[idx]
        if not is_valid_finite_float(val):
            errors.append(
                f"[{item_name}] {field_name}[{idx}] ({axis}) must be a valid finite float, got {repr(val)}"
            )
    return errors


def validate_bounding_box(bbox: Any, item_name: str, strict: bool = False) -> List[str]:
    """Validates bounding box structure: min, max, size/dimensions, center."""
    errors: List[str] = []
    if not isinstance(bbox, dict):
        return [f"[{item_name}] bounding_box must be an object/dict, got {type(bbox).__name__}"]

    # min check
    if "min" in bbox:
        errors.extend(validate_3d_vector(bbox["min"], "bounding_box.min", item_name))
    else:
        errors.append(f"[{item_name}] bounding_box missing required key 'min'")

    # max check
    if "max" in bbox:
        errors.extend(validate_3d_vector(bbox["max"], "bounding_box.max", item_name))
    else:
        errors.append(f"[{item_name}] bounding_box missing required key 'max'")

    # size / dimensions check
    size_key = "size" if "size" in bbox else ("dimensions" if "dimensions" in bbox else None)
    if size_key is not None:
        errors.extend(validate_3d_vector(bbox[size_key], f"bounding_box.{size_key}", item_name))
    else:
        errors.append(f"[{item_name}] bounding_box missing required key 'size' or 'dimensions'")

    # center check (optional if calculable from min/max, but validated if present)
    if "center" in bbox:
        errors.extend(validate_3d_vector(bbox["center"], "bounding_box.center", item_name))

    # Relational & geometric checks if no vector errors so far
    if not errors and "min" in bbox and "max" in bbox and size_key:
        min_v = bbox["min"]
        max_v = bbox["max"]
        sz_v = bbox[size_key]

        for i, axis in enumerate(["x", "y", "z"]):
            if max_v[i] < min_v[i]:
                errors.append(
                    f"[{item_name}] bounding_box.max[{i}] ({max_v[i]}) is less than min[{i}] ({min_v[i]})"
                )
            expected_size = max_v[i] - min_v[i]
            if sz_v[i] < -1e-5:
                errors.append(
                    f"[{item_name}] bounding_box.{size_key}[{i}] is negative: {sz_v[i]}"
                )
            if strict and abs(sz_v[i] - expected_size) > 1e-3:
                errors.append(
                    f"[{item_name}] bounding_box.{size_key}[{i}] ({sz_v[i]}) does not match max-min ({expected_size})"
                )

        if "center" in bbox:
            ctr = bbox["center"]
            for i, axis in enumerate(["x", "y", "z"]):
                expected_ctr = (min_v[i] + max_v[i]) / 2.0
                if strict and abs(ctr[i] - expected_ctr) > 1e-3:
                    errors.append(
                        f"[{item_name}] bounding_box.center[{i}] ({ctr[i]}) does not match (min+max)/2 ({expected_ctr})"
                    )

    return errors


def validate_tags_and_affinities(item: Dict[str, Any], item_name: str) -> List[str]:
    """Validates that tags, affinities, and roles are arrays of non-empty strings."""
    errors: List[str] = []

    # Tags validation
    if "tags" in item:
        tags = item["tags"]
        if not isinstance(tags, list):
            errors.append(f"[{item_name}] 'tags' must be a list/array of strings, got {type(tags).__name__}")
        else:
            if len(tags) == 0:
                errors.append(f"[{item_name}] 'tags' array must not be empty")
            for idx, tag in enumerate(tags):
                if not isinstance(tag, str) or not tag.strip():
                    errors.append(f"[{item_name}] tag at index {idx} must be a non-empty string, got {repr(tag)}")
    else:
        errors.append(f"[{item_name}] missing required field 'tags'")

    # Affinities validation (if present)
    if "affinities" in item:
        aff = item["affinities"]
        if isinstance(aff, list):
            for idx, entry in enumerate(aff):
                if not isinstance(entry, str) or not entry.strip():
                    errors.append(f"[{item_name}] affinity at index {idx} must be a non-empty string, got {repr(entry)}")
        elif isinstance(aff, dict):
            for k, v in aff.items():
                if not isinstance(k, str) or not k.strip():
                    errors.append(f"[{item_name}] affinity key {repr(k)} must be non-empty string")
                if not is_valid_finite_float(v):
                    errors.append(f"[{item_name}] affinity value for {k} must be finite float, got {repr(v)}")
        else:
            errors.append(f"[{item_name}] 'affinities' must be a list of strings or dict of floats, got {type(aff).__name__}")

    # Placement roles / category validation
    for key in ["placement_role", "placement_roles", "category"]:
        if key in item:
            val = item[key]
            if isinstance(val, str):
                if not val.strip():
                    errors.append(f"[{item_name}] '{key}' must not be blank")
            elif isinstance(val, list):
                for idx, r in enumerate(val):
                    if not isinstance(r, str) or not r.strip():
                        errors.append(f"[{item_name}] '{key}' element at {idx} must be a non-empty string")
            else:
                errors.append(f"[{item_name}] '{key}' must be a string or list of strings, got {type(val).__name__}")

    return errors


def validate_catalog_item(item: Any, item_name: str, strict: bool = False) -> List[str]:
    """Validates an individual catalog item / prefab record."""
    errors: List[str] = []
    if not isinstance(item, dict):
        return [f"[{item_name}] Item must be an object/dict, got {type(item).__name__}"]

    # Check bounding box
    bbox = item.get("bounding_box") or item.get("bbox")
    if bbox is not None:
        errors.extend(validate_bounding_box(bbox, item_name, strict=strict))
    else:
        errors.append(f"[{item_name}] missing bounding_box / bbox object")

    # Check tags, affinities, roles
    errors.extend(validate_tags_and_affinities(item, item_name))

    # Optional render paths validation
    renders = item.get("render_paths") or item.get("thumbnails") or item.get("multi_angle_renders")
    if renders is not None:
        if not isinstance(renders, dict):
            errors.append(f"[{item_name}] render_paths / thumbnails must be an object, got {type(renders).__name__}")
        else:
            for angle in ["front", "side", "top"]:
                if angle in renders:
                    val = renders[angle]
                    if not isinstance(val, str) or not val.strip():
                        errors.append(f"[{item_name}] render path for '{angle}' must be a non-empty string")

    return errors


def extract_items_map(data: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extracts a uniform dictionary of {item_name: item_dict} from catalog JSON root."""
    if not isinstance(data, dict):
        if isinstance(data, list):
            # Array of item objects
            res = {}
            for idx, elem in enumerate(data):
                if isinstance(elem, dict):
                    name = elem.get("name") or elem.get("prefab_name") or f"item_{idx}"
                    res[name] = elem
                else:
                    return None, f"Item at index {idx} is not a dictionary"
            return res, None
        return None, f"Catalog root must be a JSON object or array, got {type(data).__name__}"

    if "assets" in data and isinstance(data["assets"], dict):
        return data["assets"], None
    if "prefabs" in data and isinstance(data["prefabs"], dict):
        return data["prefabs"], None

    # Check if root is already mapping of prefab_name -> dict
    all_dicts = all(isinstance(v, dict) for v in data.values())
    if all_dicts and len(data) > 0:
        return data, None

    return data, None


def validate_catalog_dict(data: Any, strict: bool = False) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validates a catalog data dictionary.
    Returns: (is_valid, list_of_error_strings, summary_dict)
    """
    errors: List[str] = []
    items_map, extract_err = extract_items_map(data)
    if extract_err or items_map is None:
        return False, [extract_err or "Failed to parse catalog items structure"], {"total_items": 0, "valid_items": 0, "error_count": 1}

    total_items = len(items_map)
    valid_items = 0

    if total_items == 0:
        errors.append("Catalog contains zero items/assets")

    for item_name, item_dict in items_map.items():
        item_errors = validate_catalog_item(item_dict, item_name, strict=strict)
        if item_errors:
            errors.extend(item_errors)
        else:
            valid_items += 1

    summary = {
        "total_items": total_items,
        "valid_items": valid_items,
        "error_count": len(errors),
    }
    return (len(errors) == 0), errors, summary


def validate_catalog_file(file_path: str, strict: bool = False) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Loads and validates a catalog JSON file from disk."""
    if not os.path.exists(file_path):
        return False, [f"Catalog file does not exist at: {file_path}"], {"total_items": 0, "valid_items": 0, "error_count": 1}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return False, [f"Invalid JSON syntax in {file_path}: {str(exc)}"], {"total_items": 0, "valid_items": 0, "error_count": 1}
    except Exception as exc:
        return False, [f"Failed to read {file_path}: {str(exc)}"], {"total_items": 0, "valid_items": 0, "error_count": 1}

    return validate_catalog_dict(data, strict=strict)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate asset catalog JSON for valid float bounding boxes, string array tags, and metadata integrity."
    )
    parser.add_argument("catalog_path", help="Path to catalog.json file to validate")
    parser.add_argument("--strict", action="store_true", help="Enable strict mathematical consistency checks")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    is_valid, errors, summary = validate_catalog_file(args.catalog_path, strict=args.strict)

    if args.json:
        out = {
            "valid": is_valid,
            "catalog_path": os.path.abspath(args.catalog_path),
            "summary": summary,
            "errors": errors,
        }
        print(json.dumps(out, indent=2))
    else:
        print("=" * 60)
        print("  ASSET CATALOG VALIDATOR (R1 Acceptance Verification)")
        print("=" * 60)
        print(f"File: {os.path.abspath(args.catalog_path)}")
        print(f"Total Assets Inspected: {summary['total_items']}")
        print(f"Valid Assets:          {summary['valid_items']}")
        print(f"Errors Encountered:    {summary['error_count']}")
        print("-" * 60)

        if is_valid:
            print(">>> STATUS: PASS (Catalog is 100% valid)")
            print("=" * 60)
            return 0
        else:
            print(">>> STATUS: FAIL (Validation violations detected):")
            for idx, err in enumerate(errors, 1):
                print(f"  {idx}. {err}")
            print("=" * 60)
            return 1


if __name__ == "__main__":
    sys.exit(main())
