## 2026-09-02T08:00:41Z
<USER_REQUEST>
You are survey_spec_miner_3, an exploration and spec mining agent for Unity and AI Layouts.
Working directory: /Users/jack/worldgen/.agents/survey_spec_miner_3
Authoritative User Request: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md
PROJECT.md: /Users/jack/worldgen/PROJECT.md

Task:
Conduct a comprehensive technical survey of the Unity Importer, C# test harness, and AI layout template generation for WorldGen V2.

Investigate:
1. Current Unity importer in `unity/Assets/Editor/WorldManifestImporter.cs` and C# tests in `unity/`.
2. How to update Unity Importer for R3: Handling adaptive decimated mesh data (custom vertices, triangles/indices, or adaptive terrain mesh) alongside or within Unity Terrain / MeshFilter, ensuring variable-sized triangles/quads load correctly in Unity.
3. How to generate and structure offline JSON layout templates using the local Qwen model (or Ollama `qwen3.8:27b` / Python template generator script) for structured, realistic environments by zone type (e.g. military base, airfield, outpost, radar station, depot) with continuous density scaling (R4).
4. Review rubrics in `tests/rubrics/` and how to update frontend & Unity verification rubrics for V2 acceptance criteria (zone drag/recompute and adaptive mesh loading).

Deliverables:
- Maintain progress.md in your working directory.
- Write a detailed survey report to `/Users/jack/worldgen/.agents/survey_spec_miner_3/handoff.md`.
- Send a completion message to parent when finished.
</USER_REQUEST>
