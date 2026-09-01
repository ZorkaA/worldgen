## 2026-09-01T18:23:32Z
You are teamwork_preview_challenger (Challenger 2: Frontend & Unity Importer Edge-Case Challenger).
Your working directory is: /Users/jack/worldgen/.agents/challenger_2

Read the authoritative requirements at: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md
Also read:
- /Users/jack/worldgen/PROJECT.md
- /Users/jack/worldgen/TEST_READY.md

Your mission:
1. Stress test and adversarially verify the Unity importer and Frontend data ingestion under edge cases:
   - Malformed, empty, or corrupted `world_manifest.json` inputs.
   - 1D vs 2D heightmaps, non-square resolutions, negative terrain dimensions.
   - Unknown/missing prefab names, missing textures, non-standard faction/destruction codes.
   - Frontend Three.js memory management (object cleanup, dispose calls), container query responsiveness, and offline fallback synthesis.
2. Write and execute adversarial test scripts to verify these edge cases.
3. Record your findings, test results, and final verdict (APPROVE or REQUEST_CHANGES) in `/Users/jack/worldgen/.agents/challenger_2/handoff.md`.
4. Send a message to your parent when done.
