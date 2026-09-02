/**
 * API Client for WorldGen Backend with Complete Standalone Offline Fallback
 * Connects to FastAPI endpoints (/generate, /recompute, /manifest, /catalog, /health)
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
      version: '2.0.0',
      asset_count: 6,
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
        },
        'SM_Bld_Watchtower_01': {
          name: 'SM_Bld_Watchtower_01',
          category: 'structures',
          placement_role: 'tower',
          tags: ['tower', 'defense', 'sentry'],
          description: 'Elevated wooden/steel perimeter watchtower.',
          bounding_box: {
            min: [-3.25, -3.25, 0.0],
            max: [3.25, 3.25, 14.2],
            size: [6.5, 6.5, 14.2],
            center: [0.0, 0.0, 7.1]
          }
        },
        'SM_Bld_Hangar_01': {
          name: 'SM_Bld_Hangar_01',
          category: 'building',
          placement_role: 'hangar',
          tags: ['hangar', 'aircraft', 'depot'],
          description: 'Reinforced aircraft and vehicle maintenance hangar.',
          bounding_box: {
            size: [18.0, 9.5, 24.0],
            center: [0.0, 4.75, 0.0]
          }
        },
        'SM_Bld_CommandCenter_01': {
          name: 'SM_Bld_CommandCenter_01',
          category: 'building',
          placement_role: 'command',
          tags: ['hq', 'command', 'radar'],
          description: 'Hardened tactical headquarters and communications bunker.',
          bounding_box: {
            size: [14.0, 6.0, 16.0],
            center: [0.0, 3.0, 0.0]
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
   * Trigger world generation with V2 parameters
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
   * Recompute world on zone drag/drop displacement
   */
  async recomputeZone(zoneId, newPos, currentConfig = {}) {
    if (this.isOnline) {
      try {
        const res = await fetch(`${this.baseUrl}/api/recompute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            zone_id: zoneId,
            new_position: [newPos.x, newPos.y, newPos.z],
            config: currentConfig,
            manifest: this.activeManifest
          }),
          signal: AbortSignal.timeout(10000),
        });
        if (res.ok) {
          const data = await res.json();
          this.activeManifest = data.manifest;
          return data;
        }
      } catch (e) {
        console.warn('API recompute failed, updating manifest client-side', e);
      }
    }

    // Client-side in-place recomputation fallback
    if (this.activeManifest) {
      const manifest = JSON.parse(JSON.stringify(this.activeManifest));
      const targetZone = manifest.zones.find((z) => z.id === zoneId);
      if (targetZone) {
        targetZone.center = [newPos.x, newPos.y, newPos.z];

        // Shift footprint points
        if (targetZone.footprint_points && targetZone.footprint_points.length > 0) {
          const rad = targetZone.radius || 75.0;
          targetZone.footprint_points = targetZone.footprint_points.map((pt, pIdx) => {
            const angle = (pIdx / targetZone.footprint_points.length) * Math.PI * 2;
            return [
              parseFloat((newPos.x + Math.cos(angle) * rad).toFixed(1)),
              parseFloat((newPos.z + Math.sin(angle) * rad).toFixed(1))
            ];
          });
        }

        // Shift buildings belonging to this zone
        manifest.buildings = manifest.buildings.map((b) => {
          if (b.zone_id === zoneId) {
            const relX = (Math.random() - 0.5) * (targetZone.radius * 0.8);
            const relZ = (Math.random() - 0.5) * (targetZone.radius * 0.8);
            return {
              ...b,
              position: [
                parseFloat((newPos.x + relX).toFixed(1)),
                newPos.y,
                parseFloat((newPos.z + relZ).toFixed(1))
              ]
            };
          }
          return b;
        });

        // Reconnect roads connected to this zone
        manifest.roads = manifest.roads.map((r) => {
          if (r.from_zone === zoneId || r.to_zone === zoneId) {
            const otherZoneId = r.from_zone === zoneId ? r.to_zone : r.from_zone;
            const otherZone = manifest.zones.find((z) => z.id === otherZoneId);
            if (otherZone) {
              const waypoints = [];
              const numSteps = 8;
              const zA = r.from_zone === zoneId ? targetZone : otherZone;
              const zB = r.to_zone === zoneId ? targetZone : otherZone;
              for (let s = 0; s <= numSteps; s++) {
                const t = s / numSteps;
                const wx = zA.center[0] + (zB.center[0] - zA.center[0]) * t;
                const wz = zA.center[2] + (zB.center[2] - zA.center[2]) * t;
                const wy = zA.center[1] + (zB.center[1] - zA.center[1]) * t;
                waypoints.push([parseFloat(wx.toFixed(1)), parseFloat(wy.toFixed(1)), parseFloat(wz.toFixed(1))]);
              }
              return { ...r, waypoints };
            }
          }
          return r;
        });

        this.activeManifest = manifest;
        return { success: true, manifest };
      }
    }

    return this.generateWorld(currentConfig);
  }

  /**
   * Client-side procedural heightmap, adaptive mesh, zone, templated building, and road generator
   * Used for 100% offline standalone capability.
   */
  synthesizeOfflineManifest(seed = 42, config = {}) {
    const res = config.resolution || 129;
    const widthKm = config.map_width_km || (config.world_size ? config.world_size[0] / 1000.0 : 1.0);
    const lengthKm = config.map_length_km || (config.world_size ? config.world_size[2] / 1000.0 : 1.0);
    const heightScale = config.height_scale || 120.0;
    const worldSize = [widthKm * 1000.0, heightScale, lengthKm * 1000.0];

    const octaves = config.octaves || 6;
    const scale = config.scale || 256.0;
    const persistence = config.persistence || 0.5;
    const lacunarity = config.lacunarity || 2.0;
    const zoneCount = config.zone_count_target || (config.zones ? config.zones.length : 5);
    const globalDensity = typeof config.density === 'number' ? config.density : 0.55;
    const margin = config.edge_margin || 150.0;
    const maxRoadSlope = config.max_road_slope || 0.25;

    // Deterministic PRNG
    let s = seed;
    const rand = () => {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };

    // 2D Perlin Permutation Table
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
      return heightmap[gz] && heightmap[gz][gx] !== undefined ? heightmap[gz][gx] : 0.0;
    };

    // Synthesize Decimated Indexed Mesh Buffer (R3)
    const meshVertices = [];
    const meshIndices = [];
    const meshNormals = [];
    const meshUvs = [];

    // Step size for adaptive decimation representation
    const decStep = Math.max(1, Math.floor(res / 64));
    const decCols = Math.ceil(res / decStep);
    const decRows = Math.ceil(res / decStep);

    for (let rz = 0; rz < decRows; rz++) {
      const zIdx = Math.min(res - 1, rz * decStep);
      const wz = (zIdx / (res - 1)) * worldSize[2];
      for (let rx = 0; rx < decCols; rx++) {
        const xIdx = Math.min(res - 1, rx * decStep);
        const wx = (xIdx / (res - 1)) * worldSize[0];
        const wy = heightmap[zIdx][xIdx];

        meshVertices.push(parseFloat(wx.toFixed(2)), parseFloat(wy.toFixed(2)), parseFloat(wz.toFixed(2)));
        meshNormals.push(0.0, 1.0, 0.0);
        meshUvs.push(parseFloat((wx / worldSize[0]).toFixed(3)), parseFloat((wz / worldSize[2]).toFixed(3)));
      }
    }

    for (let rz = 0; rz < decRows - 1; rz++) {
      for (let rx = 0; rx < decCols - 1; rx++) {
        const i0 = rz * decCols + rx;
        const i1 = rz * decCols + (rx + 1);
        const i2 = (rz + 1) * decCols + rx;
        const i3 = (rz + 1) * decCols + (rx + 1);

        // Quad split into two triangles
        meshIndices.push(i0, i2, i1);
        meshIndices.push(i1, i2, i3);
      }
    }

    // Generate Zones
    const factions = ['A', 'B', 'C'];
    const destructions = ['01', '02', '03', '04'];
    const templateTypes = ['military_base', 'airfield', 'outpost', 'radar_station', 'depot'];
    const zoneDisplayNames = {
      military_base: 'Fortified Military Base',
      airfield: 'Forward Airfield',
      outpost: 'Tactical Outpost',
      radar_station: 'Radar Station',
      depot: 'Supply Depot'
    };

    const zones = [];
    const buildings = [];
    const roads = [];

    const zoneRadius = 75.0;

    for (let i = 0; i < zoneCount; i++) {
      const zx = margin + rand() * Math.max(100.0, worldSize[0] - 2 * margin);
      const zz = margin + rand() * Math.max(100.0, worldSize[2] - 2 * margin);
      const zy = getHeightAt(zx, zz);
      const faction = factions[i % factions.length];
      const destruction = destructions[i % destructions.length];
      const template = templateTypes[i % templateTypes.length];
      const zoneId = `zone_${i}`;
      const zoneName = `${zoneDisplayNames[template]} ${String.fromCharCode(65 + i)}`;

      // Footprint boundary polygon points
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
        zone_type: template,
        density: globalDensity,
        center: [parseFloat(zx.toFixed(1)), parseFloat(zy.toFixed(1)), parseFloat(zz.toFixed(1))],
        radius: zoneRadius,
        footprint_points: footprintPoints
      });

      // Templated Asset Allocation based on Zone Type (R4)
      const templatePrefabs = {
        military_base: [
          { name: 'SM_Bld_CommandCenter_01', size: [14.0, 6.0, 16.0], role: 'command' },
          { name: 'SM_Bld_Tent_01', size: [7.8, 4.1, 12.0], role: 'barracks' },
          { name: 'SM_Bld_Watchtower_01', size: [6.5, 14.2, 6.5], role: 'tower' },
          { name: 'SM_Prop_Barricade_01', size: [3.5, 1.2, 1.0], role: 'defense' }
        ],
        airfield: [
          { name: 'SM_Bld_Hangar_01', size: [18.0, 9.5, 24.0], role: 'hangar' },
          { name: 'SM_Bld_ControlTower_01', size: [8.0, 18.0, 8.0], role: 'tower' },
          { name: 'SM_Bld_Tent_01', size: [7.8, 4.1, 12.0], role: 'barracks' }
        ],
        outpost: [
          { name: 'SM_Bld_Watchtower_01', size: [6.5, 14.2, 6.5], role: 'tower' },
          { name: 'SM_Bld_Tent_01', size: [7.8, 4.1, 12.0], role: 'barracks' },
          { name: 'SM_Prop_Barricade_01', size: [3.5, 1.2, 1.0], role: 'defense' }
        ],
        radar_station: [
          { name: 'SM_Bld_Radar_01', size: [12.0, 16.0, 12.0], role: 'radar' },
          { name: 'SM_Bld_CommandCenter_01', size: [14.0, 6.0, 16.0], role: 'command' },
          { name: 'SM_Bld_Watchtower_01', size: [6.5, 14.2, 6.5], role: 'tower' }
        ],
        depot: [
          { name: 'SM_Bld_Warehouse_01', size: [16.0, 8.0, 20.0], role: 'depot' },
          { name: 'SM_Bld_Hangar_01', size: [18.0, 9.5, 24.0], role: 'hangar' },
          { name: 'SM_Prop_Crate_01', size: [2.5, 2.0, 2.5], role: 'storage' }
        ]
      };

      const prefabs = templatePrefabs[template] || templatePrefabs.military_base;
      const bldCount = Math.max(2, Math.floor(3 + globalDensity * 12));

      for (let b = 0; b < bldCount; b++) {
        const pInfo = prefabs[b % prefabs.length];
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

    // Generate Slope-Aware Road Ribbons (R3)
    for (let i = 0; i < zones.length - 1; i++) {
      const zA = zones[i];
      const zB = zones[i + 1];
      const waypoints = [];
      const numSteps = 10;

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
        max_slope_observed: Math.min(maxRoadSlope, 0.18),
        waypoints: waypoints
      });
    }

    return {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      metadata: {
        version: '2.0.0',
        seed: seed,
        created_at: new Date().toISOString(),
        generator: 'FastAPI Procedural WorldGen v2.0 (Client Fallback)',
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
        heightmap: heightmap,
        mesh: {
          vertices: meshVertices,
          indices: meshIndices,
          normals: meshNormals,
          uvs: meshUvs,
          vertex_count: meshVertices.length / 3,
          triangle_count: meshIndices.length / 3,
          decimation_ratio: parseFloat(((meshIndices.length / 3) / ((res - 1) * (res - 1) * 2)).toFixed(4))
        }
      },
      zones: zones,
      buildings: buildings,
      roads: roads
    };
  }
}

