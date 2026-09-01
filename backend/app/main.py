"""FastAPI application entry point."""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import RENDERS_DIR
from .api.routes import router as api_router

# Ensure renders directory exists
RENDERS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Procedural 3D WorldGen Backend",
    version="1.0.0",
    description="FastAPI Backend for procedural terrain generation, Poisson-disc zones, SAT building layout, and slope-aware road networks.",
)

# CORS middleware for Vite frontend (http://localhost:5173) and any local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under both /api and root
app.include_router(api_router, prefix="/api")

# Also mount static renders if available
if RENDERS_DIR.exists():
    app.mount("/renders", StaticFiles(directory=str(RENDERS_DIR)), name="renders")


@app.get("/")
def root():
    return {
        "service": "Procedural 3D WorldGen Backend",
        "version": "1.0.0",
        "endpoints": {
            "generate": "/api/generate",
            "manifest": "/api/manifest",
            "catalog": "/api/catalog",
            "health": "/api/health",
            "docs": "/docs",
        },
    }
