# BRIEFING — 2026-09-01T21:55:00Z

## Mission
Mine, define, and document precise architectural and technical specifications for R3 (Vite + Three.js Frontend), R4 (Unity C# Importer Package), and Acceptance Criteria & E2E Testing Suite for the procedural military world generator.

## 🔒 My Identity
- Archetype: teamwork_preview_spec_miner
- Roles: survey_spec_miner_3
- Working directory: /Users/jack/worldgen/.agents/survey_spec_miner_3
- Original parent: 069e459b-a13e-4233-a11c-5b3b3a0ba591
- Milestone: Survey Phase (Survey Spec Miner 3)

## 🔒 Key Constraints
- Authoritative specification discovery only — do not implement anything.
- Follow modern-web-guidance skill rules for UI/layout.
- Produce comprehensive feature tables and edge case tables.
- Detail Unity Importer C# architecture including `PrefabUtility.InstantiatePrefab`, `TerrainData` heightmap creation, material swap for factions A/B/C and destruction 01-04.
- Detail acceptance criteria test suites (`test_manifest_schema.py`, `test_generator.py`, `validate_catalog.py`, review rubrics).

## Current Parent
- Conversation ID: 069e459b-a13e-4233-a11c-5b3b3a0ba591
- Updated: 2026-09-01T21:55:00Z

## Loaded Skills
- **Source**: /Users/jack/.gemini/config/plugins/modern-web-guidance-plugin/skills/modern-web-guidance/SKILL.md
- **Local copy**: /Users/jack/worldgen/.agents/survey_spec_miner_3/skills/modern-web-guidance/SKILL.md
- **Core methodology**: Mandatory execution before implementing UI/layout, searching best-practice guides for modern CSS/HTML/JS, container queries, native popovers/dialogs, scrollbar-gutter, fluid typography.

## Task Summary
- **What to build**: Full technical specification for R3 (Interactive 3D Frontend), R4 (Unity Importer C#), and E2E Test Suite / Acceptance Criteria.
- **Success criteria**: Detailed, actionable, complete `spec_report.md` and `handoff.md` covering all requirements, edge cases, contracts, data schemas, and review rubrics.
- **Interface contracts**: REST API schemas (`/manifest`, `/generate`, `/catalog`), `world_manifest.json` schema, `catalog.json` schema, Unity importer API.
- **Code layout**: Frontend in `frontend/`, Unity Importer in `unity_package/` or `unity/`, Tests in `tests/`.

## Key Decisions Made
- Discovered Synty PolygonMilitary assets at `/Users/jack/Downloads/assetripper_export/ExportedProject/Assets/PolygonMilitary` with textures `PolygonMilitary_Texture_0[1-4]_[A-C].png`, materials `PolygonMilitary_Mat_0[1-4]_[A-C].mat`, and standard prefabs.
- Queried `modern-web-guidance` for CSS layout, native overlays, scrollbar management, container queries, and responsive panel structures.

## Artifact Index
- /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md — Original User Requirements
- /Users/jack/worldgen/.agents/survey_spec_miner_3/spec_report.md — Architectural and Technical Specification Report
- /Users/jack/worldgen/.agents/survey_spec_miner_3/handoff.md — 5-Component Handoff Report
