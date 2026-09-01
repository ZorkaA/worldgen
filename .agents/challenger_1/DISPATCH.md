## 2026-09-01T18:23:32Z
You are teamwork_preview_challenger (Challenger 1: Backend Stress & Adversarial Verification).
Your working directory is: /Users/jack/worldgen/.agents/challenger_1

Read the authoritative requirements at: /Users/jack/worldgen/.agents/ORIGINAL_REQUEST.md
Also read:
- /Users/jack/worldgen/PROJECT.md
- /Users/jack/worldgen/TEST_READY.md

Your mission:
1. Stress test and adversarially verify the procedural generator algorithms and backend endpoints:
   - Extreme seeds (negative, massive, 0).
   - High resolutions and extreme droplet counts for Numba hydraulic erosion (check numerical stability, NaN/Inf avoidance).
   - High zone density and building counts (check that SAT OBB collision avoidance never allows overlapping buildings).
   - Slope-aware A* road pathfinding (verify that roads never violate maximum slope gradients and always connect all zones).
   - API endpoints under invalid payloads, missing fields, out-of-bound coordinates.
2. Write and execute stress testing scripts to empirically test these limits.
3. Record your findings, test results, and final verdict (APPROVE or REQUEST_CHANGES) in `/Users/jack/worldgen/.agents/challenger_1/handoff.md`.
4. Send a message to your parent when done.
