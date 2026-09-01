#!/usr/bin/env python3
"""
CLI Runner for Asset Catalog Builder.
"""
import sys
import os

# Add repo root to python path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.app.catalog.builder import build_catalog, get_catalog

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Asset Catalog Builder CLI Runner")
    parser.add_argument("--models-dir", type=str, default="/Users/jack/Downloads/assetripper_export/ExportedProject/Assets/PolygonMilitary/Models")
    parser.add_argument("--renders-dir", type=str, default=os.path.join(repo_root, "backend/app/catalog/renders"))
    parser.add_argument("--catalog-out", type=str, default=os.path.join(repo_root, "backend/app/catalog/catalog.json"))
    parser.add_argument("--use-vlm", action="store_true", help="Enable Ollama VLM enrichment for sample assets")
    parser.add_argument("--vlm-samples", type=int, default=3, help="Number of VLM queries")
    parser.add_argument("--force", action="store_true", help="Force rebuild")
    
    args = parser.parse_args()
    build_catalog(
        models_dir=args.models_dir,
        renders_dir=args.renders_dir,
        catalog_path=args.catalog_out,
        use_vlm=args.use_vlm,
        vlm_sample_limit=args.vlm_samples,
        force_rebuild=args.force
    )
