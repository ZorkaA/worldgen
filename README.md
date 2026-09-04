# WorldGen

A tool for generating procedural 3D environments using Synty PolygonMilitary assets. It includes a Python backend for terrain generation, a Vite/Three.js web editor, and a Unity package for importing the final worlds.

## Prerequisites

- **Python 3.10+** and [uv](https://github.com/astral-sh/uv)
- **Node.js 18+** and **npm**
- **Unity 2022.3+**

## 1. Backend (FastAPI)

The backend handles all procedural logic (noise, erosion, road routing, layout).

```bash
cd backend
# Starts the server on http://localhost:8000
uv run uvicorn app.main:app --reload
```

## 2. Frontend (Web Editor)

The frontend provides the 3D viewport and parameter controls. Ensure the backend is running first.

```bash
cd frontend
npm install
npm run dev
```
Open the provided `localhost` link in your browser.

## 3. Unity Importer

Once you have exported a `world_manifest.json` from the web editor, import it into Unity:

1. Open your Unity Project containing the **Synty PolygonMilitary** assets.
2. In Unity, open **Window > Package Manager**.
3. Click the **+** (top-left) and select **"Add package from disk..."**.
4. Select the `package.json` located in `worldgen/unity/`.
5. In the top menu, click **WorldGen > Import World Manifest**.
6. Select your downloaded `world_manifest.json`.

*(Optional) Rebuilding the catalog: Requires Blender at `/Applications/Blender.app` and Ollama running `qwen3.8:27b`. Run `cd backend/app/catalog && uv run python builder.py`.*
