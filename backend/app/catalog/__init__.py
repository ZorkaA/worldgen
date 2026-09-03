"""
Asset Catalog Package.
Provides Blender bounding box extraction, multi-angle MatCap rendering,
VLM enrichment (Ollama qwen3.8:27b with heuristic fallback), and catalog caching.
"""
from .builder import get_catalog, build_catalog

__all__ = ["get_catalog", "build_catalog"]
