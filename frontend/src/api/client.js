/**
 * API Client for WorldGen Backend with Complete Standalone Offline Fallback
 * Connects to FastAPI endpoints (/generate, /manifest, /catalog, /health)
 * Fallback to bundled sample data and client-side procedural synthesis when offline.
 */

export class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.isOnline = false;
    this.cachedCatalog = null;
    this.activeManifest = null;
  }

  /**
   * Check connection to backend
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: AbortSignal.timeout(2000),
      });
      if (response.ok) {
        const data = await response.json();
        this.isOnline = true;
        return { online: true, data };
      }
    } catch (err) {
      // Backend unavailable
    }
    this.isOnline = false;
    return { online: false, data: null };
  }

  /**
   * Fetch asset catalog metadata
   */
  async getCatalog() {
    if (this.cachedCatalog) return this.cachedCatalog;

    if (this.isOnline) {
      try {
        const res = await fetch(`${this.baseUrl}/api/catalog`, {
          signal: AbortSignal.timeout(4000),
        });
        if (res.ok) {
          const data = await res.json();
          this.cachedCatalog = data;
          return data;
        }
      } catch (e) {
        console.warn('Failed to fetch catalog from online backend, falling back to sample catalog', e);
      }
    }

    // Offline fallback: load bundled sample_catalog.json
    try {
      const res = await fetch('/sample_catalog.json');
      if (res.ok) {
        const data = await res.json();
        this.cachedCatalog = data;
        return data;
      }
    } catch (e) {
      console.warn('Failed to fetch bundled sample catalog, creating synthetic fallback', e);
    }

    // Minimal synthetic catalog if sample file fetch fails
    const synthetic = {
      version: '1.0.0',
      asset_count: 5,
      assets: {
        'SM_Bld_Tent_01': {
          name: 'SM_Bld_Tent_01',
          category: 'building',
          placement_role: 'barracks',
          tags: ['tent', 'military', 'shelter', 'barracks'],
          description: 'Standard military barracks canvas tent.',
          bounding_box: {
            min: [-3.899, -6.015, 0.0],
            max: [3.899, 6.015, 4.072],
            size: [7.799, 12.030, 4.072],
            center: [0.0, 0.0, 2.036]
          },
          render_paths: {
            front: '/renders/SM_Bld_Tent_01_front.png',
            side: '/renders/SM_Bld_Tent_01_side.png',
            top: '/renders/SM_Bld_Tent_01_top.png'
          }
        }
      }
    };
    this.cachedCatalog = synthetic;
    return synthetic;
  }

  /**
   * Fetch active or seed-based manifest
   */
  async getManifest(seed = null) {
    if (this.isOnline) {
      try {
        const url = seed !== null ? `${this.baseUrl}/api/manifest?seed=${seed}` : `${this.baseUrl}/api/manifest`;
        const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          const manifest = await res.json();
          this.activeManifest = manifest;
          return manifest;
        }
      } catch (e) {
        console.warn('Failed to fetch manifest from online backend, falling back', e);
      }
    }

    // Offline fallback: load bundled sample_world_manifest.json
    try {
      const res = await fetch('/sample_world_manifest.json');
      if (res.ok) {
        const manifest = await res.json();
        this.activeManifest = manifest;
        return manifest;
      }
    } catch (e) {
      console.warn('Failed to fetch bundled sample manifest, synthesizing client-side world', e);
    }

    // Synthesize client-side procedural fallback
    const manifest = this.synthesizeOfflineManifest(seed || 42);
    this.activeManifest = manifest;
    return manifest;
  }

  /**
   * Trigger world generation with parameters
   */
  async generateWorld(config = {}) {
    const effectiveSeed = config.seed !== undefined ? config.seed : Math.floor(Math.random() * 1000000);

    if (this.isOnline) {
      try {
        const res = await fetch(`${this.baseUrl}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...config, seed: effectiveSeed }),
          signal: AbortSignal.timeout(15000),
        });
        if (res.ok) {
          const data = await res.json();
          this.activeManifest = data.manifest;
          return data;
        }
      } catch (e) {
        console.warn('API generate call failed or timed out, generating client-side fallback', e);
      }
    }

    // Client-side procedural generation fallback
    const startTime = performance.now();
    const manifest = this.synthesizeOfflineManifest(effectiveSeed, config);
    const executionTime = (performance.now() - startTime) / 1000;

    this.activeManifest = manifest;
    return {
      success: true,
      seed: effectiveSeed,
      execution_time_seconds: parseFloat(executionTime.toFixed(3)),
      summary: {
        total_execution_time_seconds: executionTime,
        zones_placed: manifest.zones.length,
        buildings_placed: manifest.buildings.length,
        roads_routed: manifest.roads.length,
        generator_mode: 'client_side_offline_fallback'
      },
      manifest
    };
  }

  /**
   * Client-side procedural heightmap, zone, building, and road generator
   * Used for 100% offline standalone capability.
   */
  synthesizeOfflineManifest(seed = 42, config = {}) {
    const res = config.resolution || 129;
    const worldSize = config.world_size || [1000.0, 150.0, 1000.0];
    const octaves = config.octaves || 6;
    const scale = config.scale || 256.0;
    const persistence = config.persistence || 0.5;
    const lacunarity = config.lacunarity || 2.0;
    const heightScale = config.height_scale || 120.0;
    const zoneCount = config.zone_count_target || 5;

    // Simple deterministic PRNG
    let s = seed;
    const rand = () => {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };

    // 2D Simplex / Perlin approximation
    const perm = new Uint8Array(512);
    for (let i = 0; i < 256; i++) perm[i] = i;
    for (let i = 255; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      const tmp = perm[i];
      perm[i] = perm[j];
      perm[j] = tmp;
    }
    for (let i = 0; i < 256; i++) perm[256 + i] = perm[i];

    const grad2 = (hash, x, y) => {
      const h = hash & 7;
      const u = h < 4 ? x : y;
      const v = h < 4 ? y : x;
      return ((h & 1) ? -u : u) + ((h & 2) ? -2.0 * v : 2.0 * v);
    };

    const noise2D = (x, y) => {
      const X = Math.floor(x) & 255;
      const Y = Math.floor(y) & 255;
      const xf = x - Math.floor(x);
      const yf = y - Math.floor(y);
      const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10);
      const v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
      const A = perm[X] + Y;
      const B = perm[X + 1] + Y;
      const g1 = grad2(perm[A], xf, yf);
      const g2 = grad2(perm[B], xf - 1, yf);
      const g3 = grad2(perm[A + 1], xf, yf - 1);
      const g4 = grad2(perm[B + 1], xf - 1, yf - 1);
      const x1 = g1 + u * (g2 - g1);
      const x2 = g3 + u * (g4 - g3);
      return x1 + v * (x2 - x1);
    };

    const fbm = (x, y) => {
      let total = 0;
      let freq = 1.0 / scale;
      let amp = 1.0;
      let maxAmp = 0;
      for (let o = 0; o < octaves; o++) {
        total += noise2D(x * freq, y * freq) * amp;
        maxAmp += amp;
        amp *= persistence;
        freq *= lacunarity;
      }
      return (total / maxAmp) * 0.5 + 0.5;
    };

    // Generate heightmap array
    const heightmap = [];
    for (let z = 0; z < res; z++) {
      const row = [];
      const worldZ = (z / (res - 1)) * worldSize[2];
      for (let x = 0; x < res; x++) {
        const worldX = (x / (res - 1)) * worldSize[0];
        // Domain warping
        const qx = fbm(worldX + 50.0, worldZ + 12.0);
        const qz = fbm(worldX + 80.0, worldZ + 90.0);
        const elevation = fbm(worldX + qx * 60.0, worldZ + qz * 60.0) * heightScale;
        row.push(parseFloat(elevation.toFixed(2)));
      }
      heightmap.push(row);
    }

    const getHeightAt = (wx, wz) => {
      const gx = Math.max(0, Math.min(res - 1, Math.floor((wx / worldSize[0]) * (res - 1))));
      const gz = Math.max(0, Math.min(res - 1, Math.floor((wz / worldSize[2]) * (res - 1))));
      return heightmap[gz][gx] || 0.0;
    };

    // Generate Zones
    const factions = ['A', 'B', 'C'];
    const destructions = ['01', '02', '03', '04'];
    const zoneTypes = ['Military Outpost', 'Supply Depot', 'Command Headquarters', 'Radar Installation', 'Forward Airfield', 'Artillery Bastion'];
    const zones = [];
    const buildings = [];
    const roads = [];

    const zoneRadius = 75.0;
    const margin = 150.0;

    for (let i = 0; i < zoneCount; i++) {
      const zx = margin + rand() * (worldSize[0] - 2 * margin);
      const zz = margin + rand() * (worldSize[2] - 2 * margin);
      const zy = getHeightAt(zx, zz);
      const faction = factions[i % factions.length];
      const destruction = destructions[i % destructions.length];
      const zoneId = `zone_${i}`;
      const zoneName = `${zoneTypes[i % zoneTypes.length]} ${String.fromCharCode(65 + i)}`;

      // Generate footprint points on circle
      const footprintPoints = [];
      const numPts = 32;
      for (let p = 0; p < numPts; p++) {
        const angle = (p / numPts) * Math.PI * 2;
        const px = zx + Math.cos(angle) * (zoneRadius * (0.85 + rand() * 0.15));
        const pz = zz + Math.sin(angle) * (zoneRadius * (0.85 + rand() * 0.15));
        footprintPoints.push([parseFloat(px.toFixed(1)), parseFloat(pz.toFixed(1))]);
      }

      zones.push({
        id: zoneId,
        name: zoneName,
        faction: faction,
        destruction: destruction,
        density: i % 2 === 0 ? 'high' : 'medium',
        center: [parseFloat(zx.toFixed(1)), parseFloat(zy.toFixed(1)), parseFloat(zz.toFixed(1))],
        radius: zoneRadius,
        footprint_points: footprintPoints
      });

      // Place buildings in zone
      const prefabs = [
        { name: 'SM_Bld_Tent_01', size: [7.8, 4.1, 12.0], role: 'barracks' },
        { name: 'SM_Bld_Watchtower_01', size: [6.5, 14.2, 6.5], role: 'tower' },
        { name: 'SM_Bld_Hangar_01', size: [18.0, 9.5, 24.0], role: 'hangar' },
        { name: 'SM_Bld_CommandCenter_01', size: [14.0, 6.0, 16.0], role: 'command' },
        { name: 'SM_Prop_Barricade_01', size: [3.5, 1.2, 1.0], role: 'prop' },
      ];

      const bldCount = 4 + Math.floor(rand() * 8);
      for (let b = 0; b < bldCount; b++) {
        const pInfo = prefabs[Math.floor(rand() * prefabs.length)];
        const bAngle = rand() * Math.PI * 2;
        const bDist = rand() * (zoneRadius * 0.7);
        const bx = zx + Math.cos(bAngle) * bDist;
        const bz = zz + Math.sin(bAngle) * bDist;
        const by = getHeightAt(bx, bz);
        const yaw = rand() * 360.0;

        buildings.push({
          id: `bld_${i}_${b}`,
          zone_id: zoneId,
          prefab_name: pInfo.name,
          category: 'building',
          placement_role: pInfo.role,
          position: [parseFloat(bx.toFixed(1)), parseFloat(by.toFixed(1)), parseFloat(bz.toFixed(1))],
          rotation: [0.0, parseFloat(yaw.toFixed(1)), 0.0],
          scale: [1.0, 1.0, 1.0],
          bounding_box: {
            size: pInfo.size,
            center: [0.0, pInfo.size[1] / 2, 0.0],
            min: [-pInfo.size[0] / 2, 0, -pInfo.size[2] / 2],
            max: [pInfo.size[0] / 2, pInfo.size[1], pInfo.size[2] / 2]
          },
          faction: faction,
          destruction: destruction
        });
      }
    }

    // Generate Roads connecting consecutive zones
    for (let i = 0; i < zones.length - 1; i++) {
      const zA = zones[i];
      const zB = zones[i + 1];
      const waypoints = [];
      const numSteps = 8;
      for (let s = 0; s <= numSteps; s++) {
        const t = s / numSteps;
        const wx = zA.center[0] + (zB.center[0] - zA.center[0]) * t;
        const wz = zA.center[2] + (zB.center[2] - zA.center[2]) * t;
        const wy = getHeightAt(wx, wz);
        waypoints.push([parseFloat(wx.toFixed(1)), parseFloat(wy.toFixed(1)), parseFloat(wz.toFixed(1))]);
      }

      roads.push({
        id: `road_${i}_${i + 1}`,
        from_zone: zA.id,
        to_zone: zB.id,
        width: 6.0,
        waypoints: waypoints
      });
    }

    return {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      metadata: {
        version: '1.0.0',
        seed: seed,
        created_at: new Date().toISOString(),
        generator: 'FastAPI Procedural WorldGen v1.0 (Client Fallback)',
        bounds: [0.0, 0.0, 0.0, worldSize[0], worldSize[1], worldSize[2]],
        world_size_meters: worldSize[0],
        max_elevation_meters: heightScale,
        zone_count: zones.length,
        building_count: buildings.length,
        road_segment_count: roads.length
      },
      terrain: {
        resolution: res,
        world_size: worldSize,
        height_scale: heightScale,
        min_height: 0.0,
        max_height: heightScale,
        heightmap: heightmap
      },
      zones: zones,
      buildings: buildings,
      roads: roads
    };
  }
}
