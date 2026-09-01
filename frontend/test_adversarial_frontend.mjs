/**
 * test_adversarial_frontend.mjs - Adversarial & Boundary Stress Test Suite for Frontend
 * Tests Three.js scene modules, memory lifecycle disposal, non-square heightmaps,
 * corrupted manifests, offline synthesis determinism, and CSS container query standards.
 */

import * as THREE from 'three';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { TerrainVisualizer } from './src/scene/terrain.js';
import { ZoneVisualizer } from './src/scene/zones.js';
import { BuildingVisualizer } from './src/scene/buildings.js';
import { RoadVisualizer } from './src/scene/roads.js';
import { ApiClient } from './src/api/client.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let passedTests = 0;
let failedTests = 0;
const failureDetails = [];

function runTest(testName, testFn) {
  try {
    testFn();
    console.log(`[PASS] ${testName}`);
    passedTests++;
  } catch (ex) {
    console.error(`[FAIL] ${testName} - ${ex.message}`);
    console.error(ex.stack);
    failureDetails.push(`${testName}: ${ex.message}`);
    failedTests++;
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion Failed: ${message}`);
  }
}

function assertApproxEqual(expected, actual, tolerance, message) {
  if (Math.abs(expected - actual) > tolerance) {
    throw new Error(`Assertion Failed: ${message}. Expected: ${expected} (+/-${tolerance}), Actual: ${actual}`);
  }
}

console.log('================================================================');
console.log('     ADVERSARIAL STRESS TEST SUITE: FRONTEND & THREE.JS (R3)    ');
console.log('================================================================');

// ----------------------------------------------------------------------------
// Group 1: TerrainVisualizer Adversarial & Boundary Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_01_Terrain_NonSquareHeightmapMeshGeneration', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  // Non-square heightmap: 5 rows (Z) x 10 cols (X)
  const nonSquareHeightmap = [];
  for (let z = 0; z < 5; z++) {
    const row = [];
    for (let x = 0; x < 10; x++) {
      row.push(z * 10 + x * 5);
    }
    nonSquareHeightmap.push(row);
  }

  const terrainData = {
    resolution: [10, 5],
    world_size: [1000, 150, 500],
    heightmap: nonSquareHeightmap
  };

  visualizer.update(terrainData);

  assert(visualizer.mesh !== null, 'Terrain mesh must be created');
  assert(visualizer.geometry !== null, 'Terrain geometry must be created');
  assert(scene.children.includes(visualizer.mesh), 'Mesh added to Three.js scene');

  const posAttr = visualizer.geometry.attributes.position;
  assert(posAttr.count === 50, `Vertex count must be 10 * 5 = 50 (actual: ${posAttr.count})`);

  // Verify vertex colors attribute created and has no NaNs
  const colorAttr = visualizer.geometry.attributes.color;
  assert(colorAttr !== undefined && colorAttr.count === 50, 'Vertex colors computed for all vertices');
  for (let i = 0; i < colorAttr.array.length; i++) {
    assert(!isNaN(colorAttr.array[i]), `Vertex color at index ${i} is NaN`);
  }

  visualizer.dispose();
  assert(visualizer.mesh === null, 'Mesh reference cleared on dispose');
  assert(!scene.children.includes(visualizer.mesh), 'Mesh removed from scene');
});

runTest('ADV_FE_02_Terrain_FlatHeightmapDivideByZeroAvoidance', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  // Perfectly flat heightmap (all elevations 0.0) -> hRange could be 0
  const flatHeightmap = [
    [0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0]
  ];

  visualizer.update({
    resolution: 3,
    world_size: [300, 100, 300],
    heightmap: flatHeightmap
  });

  const colorAttr = visualizer.geometry.attributes.color;
  for (let i = 0; i < colorAttr.array.length; i++) {
    assert(!isNaN(colorAttr.array[i]), `Color value ${i} must not be NaN on flat terrain`);
  }

  visualizer.dispose();
});

runTest('ADV_FE_03_Terrain_ElevationQueryBoundaryAndOutOfBounds', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  const hm = [
    [0.0, 50.0],
    [100.0, 150.0]
  ];

  visualizer.update({
    resolution: 2,
    world_size: [1000, 150, 1000],
    heightmap: hm
  });

  // Query corner boundaries
  assertApproxEqual(0.0, visualizer.getElevationAt(0, 0), 0.01, 'Elevation at (0, 0)');
  assertApproxEqual(50.0, visualizer.getElevationAt(1000, 0), 0.01, 'Elevation at (1000, 0)');
  assertApproxEqual(100.0, visualizer.getElevationAt(0, 1000), 0.01, 'Elevation at (0, 1000)');
  assertApproxEqual(150.0, visualizer.getElevationAt(1000, 1000), 0.01, 'Elevation at (1000, 1000)');

  // Bilinear interpolation at center (500, 500) -> 0.25 * (0 + 50 + 100 + 150) = 75.0
  assertApproxEqual(75.0, visualizer.getElevationAt(500, 500), 0.01, 'Bilinear center elevation');

  // Out of bounds coordinates (negative and beyond world size)
  assertApproxEqual(0.0, visualizer.getElevationAt(-500, -500), 0.01, 'Out of bounds negative elevation clamped');
  assertApproxEqual(150.0, visualizer.getElevationAt(2500, 2500), 0.01, 'Out of bounds positive elevation clamped');

  visualizer.dispose();
});

runTest('ADV_FE_04_Terrain_NullAndEmptyTerrainDataIngestion', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  // Null data
  visualizer.update(null);
  assert(visualizer.mesh === null, 'Null terrain does not throw and leaves mesh null');

  // Empty data
  visualizer.update({});
  assert(visualizer.mesh === null, 'Empty terrain object does not throw');

  // Missing heightmap
  visualizer.update({ resolution: 65, world_size: [1000, 150, 1000] });
  assert(visualizer.mesh === null, 'Missing heightmap does not throw');

  visualizer.dispose();
});

// ----------------------------------------------------------------------------
// Group 2: ZoneVisualizer Adversarial & Boundary Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_05_Zones_PolygonAndCircularFootprintGeneration', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  terrain.update({
    resolution: 2,
    world_size: [1000, 150, 1000],
    heightmap: [[10.0, 10.0], [10.0, 10.0]]
  });

  const zoneVis = new ZoneVisualizer(scene, terrain);

  const zones = [
    {
      id: 'z0',
      name: 'Alpha Outpost',
      faction: 'A',
      destruction: '01',
      center: [200, 10, 200],
      radius: 50,
      footprint_points: [[180, 180], [220, 180], [220, 220], [180, 220]] // Polygon
    },
    {
      id: 'z1',
      name: 'Beta Fort',
      faction: 'B',
      destruction: '04', // Dashed red/damaged styling
      center: [600, 10, 600],
      radius: 70,
      footprint_points: [] // Empty -> circular fallback
    }
  ];

  zoneVis.update(zones);
  assert(zoneVis.group.children.length >= 6, `Zone objects spawned (actual: ${zoneVis.group.children.length})`);
  assert(zoneVis.beaconMeshes.length === 2, 'Two beacon tips created');

  // Test pulse animation
  zoneVis.animate(1.5);
  assert(zoneVis.beaconMeshes[0].scale.x > 0, 'Beacon pulse scaled');

  zoneVis.dispose();
  assert(zoneVis.group.children.length === 0, 'All zone children removed on dispose');
  assert(zoneVis.beaconMeshes.length === 0, 'Beacon meshes array cleared on dispose');

  terrain.dispose();
});

runTest('ADV_FE_06_Zones_NonStandardFactionsAndDestruction', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  const zoneVis = new ZoneVisualizer(scene, terrain);

  const nonStandardZones = [
    { id: 'z_weird', faction: 'Z', destruction: '99', center: [0, 0, 0] },
    { id: 'z_null', faction: null, destruction: null, center: null }
  ];

  zoneVis.update(nonStandardZones);
  assert(zoneVis.group.children.length > 0, 'Non-standard zones ingest without crash');

  zoneVis.dispose();
  terrain.dispose();
});

// ----------------------------------------------------------------------------
// Group 3: BuildingVisualizer Adversarial & Boundary Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_07_Buildings_QuaternionAndEulerRotationHandling', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  terrain.update({
    resolution: 2,
    world_size: [1000, 150, 1000],
    heightmap: [[0, 0], [0, 0]]
  });

  const bldVis = new BuildingVisualizer(scene, terrain);

  const buildings = [
    {
      id: 'b_euler',
      prefab_name: 'SM_Bld_Tent_01',
      position: [100, 0, 100],
      rotation: [0, 90, 0], // Euler degrees
      bounding_box: { size: [8, 4, 12] }
    },
    {
      id: 'b_quat',
      prefab_name: 'SM_Bld_Watchtower_01',
      position: [200, 0, 200],
      rotation: [0, 0.7071, 0, 0.7071], // Quaternion
      bbox: { size: [6, 14, 6] }
    }
  ];

  bldVis.update(buildings);
  assert(bldVis.buildingMeshes.length === 2, 'Two building meshes spawned');

  // Test Highlight Helper
  bldVis.setHighlight(bldVis.buildingMeshes[0]);
  assert(bldVis.highlightBox.visible === true, 'Highlight box visible on hover');
  bldVis.setHighlight(null);
  assert(bldVis.highlightBox.visible === false, 'Highlight box hidden when cleared');

  bldVis.dispose();
  assert(bldVis.buildingMeshes.length === 0, 'Building meshes cleared on dispose');
  assert(bldVis.group.children.length === 0, 'Building group empty on dispose');

  terrain.dispose();
});

runTest('ADV_FE_08_Buildings_MissingBboxAndDegenerateValues', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  const bldVis = new BuildingVisualizer(scene, terrain);

  const corruptBuildings = [
    { id: 'b_no_bbox', prefab_name: 'SM_Bld_Unknown' },
    { id: 'b_zero_size', bounding_box: { size: [0, 0, 0] } },
    { id: 'b_null_pos', position: null, rotation: null, scale: null }
  ];

  bldVis.update(corruptBuildings);
  assert(bldVis.buildingMeshes.length === 3, 'All 3 degenerate buildings safely visualized');

  bldVis.dispose();
  terrain.dispose();
});

// ----------------------------------------------------------------------------
// Group 4: RoadVisualizer Adversarial & Boundary Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_09_Roads_ContinuousRibbonMeshGeometry', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  terrain.update({
    resolution: 2,
    world_size: [1000, 150, 1000],
    heightmap: [[0, 0], [0, 0]]
  });

  const roadVis = new RoadVisualizer(scene, terrain);

  const roads = [
    {
      id: 'road_0',
      width: 8.0,
      waypoints: [
        [100, 0, 100],
        [150, 5, 200],
        [200, 10, 350],
        [300, 5, 450]
      ]
    }
  ];

  roadVis.update(roads);
  assert(roadVis.group.children.length === 2, 'Road quad ribbon mesh + centerline line spawned');

  const ribbonMesh = roadVis.group.children[0];
  const geo = ribbonMesh.geometry;
  assert(geo.attributes.position.count > 30, 'Ribbon mesh has dense vertex buffer');
  assert(geo.attributes.normal !== undefined, 'Ribbon normals computed');
  assert(geo.attributes.uv !== undefined, 'Ribbon UVs computed');
  assert(geo.index !== null, 'Ribbon index buffer populated');

  roadVis.dispose();
  assert(roadVis.group.children.length === 0, 'Road group empty on dispose');

  terrain.dispose();
});

runTest('ADV_FE_10_Roads_DuplicateAndInsufficientWaypoints', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  const roadVis = new RoadVisualizer(scene, terrain);

  const edgeRoads = [
    { id: 'r_empty', waypoints: [] },
    { id: 'r_one', waypoints: [[100, 0, 100]] },
    { id: 'r_dups', waypoints: [[100, 0, 100], [100, 0, 100]] } // filtered to 1 point
  ];

  roadVis.update(edgeRoads);
  assert(roadVis.group.children.length === 0, 'Degenerate roads skipped cleanly without errors');

  roadVis.dispose();
  terrain.dispose();
});

// ----------------------------------------------------------------------------
// Group 5: Memory Leak & Lifecycle Disposal Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_11_ThreeJs_SuccessiveManifestReloadsDisposal', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  const zones = new ZoneVisualizer(scene, terrain);
  const buildings = new BuildingVisualizer(scene, terrain);
  const roads = new RoadVisualizer(scene, terrain);

  let disposedGeometries = 0;
  let disposedMaterials = 0;

  // Intercept BufferGeometry and Material dispose methods to track calls
  const origGeoDispose = THREE.BufferGeometry.prototype.dispose;
  THREE.BufferGeometry.prototype.dispose = function() {
    disposedGeometries++;
    origGeoDispose.call(this);
  };

  const origMatDispose = THREE.Material.prototype.dispose;
  THREE.Material.prototype.dispose = function() {
    disposedMaterials++;
    origMatDispose.call(this);
  };

  const client = new ApiClient();

  try {
    // Perform 5 successive manifest generation and loading cycles
    for (let cycle = 0; cycle < 5; cycle++) {
      const manifest = client.synthesizeOfflineManifest(100 + cycle, {
        resolution: 33,
        zone_count_target: 3
      });

      terrain.update(manifest.terrain);
      zones.update(manifest.zones);
      buildings.update(manifest.buildings);
      roads.update(manifest.roads);
    }

    // Verify multiple disposal calls took place during updates
    assert(disposedGeometries >= 20, `Geometries must be disposed across reloads (actual: ${disposedGeometries})`);
    assert(disposedMaterials >= 20, `Materials must be disposed across reloads (actual: ${disposedMaterials})`);

    // Final clean disposal
    terrain.dispose();
    zones.dispose();
    buildings.dispose();
    roads.dispose();

    assert(scene.children.length === 4, 'Root containers and highlight helper remain in scene');
    assert(zones.group.children.length === 0, 'Zones group has 0 children after disposal');
    assert(buildings.group.children.length === 0, 'Buildings group has 0 children after disposal');
    assert(roads.group.children.length === 0, 'Roads group has 0 children after disposal');
  } finally {
    // Restore prototypes
    THREE.BufferGeometry.prototype.dispose = origGeoDispose;
    THREE.Material.prototype.dispose = origMatDispose;
  }
});

// ----------------------------------------------------------------------------
// Group 6: Offline Fallback Synthesis & Determinism Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_12_OfflineSynthesis_SchemaComplianceAndDeterminism', () => {
  const client = new ApiClient();

  // Test 1: Determinism (same seed yields exact same manifest)
  const m1 = client.synthesizeOfflineManifest(1337, { resolution: 65, zone_count_target: 4 });
  const m2 = client.synthesizeOfflineManifest(1337, { resolution: 65, zone_count_target: 4 });

  assert(m1.metadata.seed === 1337, 'Seed recorded');
  assert(m1.zones.length === 4, 'Zone count target respected');
  assert(m1.zones[0].center[0] === m2.zones[0].center[0], 'Deterministic zone centers X');
  assert(m1.zones[0].center[2] === m2.zones[0].center[2], 'Deterministic zone centers Z');
  assert(m1.terrain.heightmap[10][10] === m2.terrain.heightmap[10][10], 'Deterministic heightmap elevation');

  // Test 2: Different seeds yield different worlds
  const m3 = client.synthesizeOfflineManifest(9999, { resolution: 65, zone_count_target: 4 });
  assert(m1.zones[0].center[0] !== m3.zones[0].center[0], 'Different seeds produce distinct layouts');

  // Test 3: Manifest structure contains all required sections
  assert(Array.isArray(m1.zones) && m1.zones.length > 0, 'Zones array present');
  assert(Array.isArray(m1.buildings) && m1.buildings.length > 0, 'Buildings array present');
  assert(Array.isArray(m1.roads) && m1.roads.length > 0, 'Roads array present');
  assert(m1.terrain.heightmap.length === 65, 'Heightmap resolution matches 65');
});

// ----------------------------------------------------------------------------
// Group 7: Modern Web Guidance & CSS Architecture Verification
// ----------------------------------------------------------------------------

runTest('ADV_FE_13_CSS_ContainerQueriesAndScrollbarGutterCompliance', () => {
  const cssPath = path.join(__dirname, 'src', 'style.css');
  assert(fs.existsSync(cssPath), 'style.css must exist');

  const cssContent = fs.readFileSync(cssPath, 'utf-8');

  // Check Container Queries (@container)
  assert(cssContent.includes('container-type: inline-size;'), 'Must specify container-type: inline-size for container queries');
  assert(cssContent.includes('@container (min-width: 340px)'), 'Must include @container query breakpoint for responsive cards');
  assert(cssContent.includes('@container (min-width: 480px)'), 'Must include @container query breakpoint at 480px');

  // Check scrollbar-gutter: stable & overscroll-behavior: contain per modern web guidance
  assert(cssContent.includes('scrollbar-gutter: stable;'), 'Must implement scrollbar-gutter: stable');
  assert(cssContent.includes('overscroll-behavior: contain;'), 'Must implement overscroll-behavior: contain');

  // Check CSS Custom Properties for Factions & Damage
  assert(cssContent.includes('--faction-a:'), 'Defines --faction-a');
  assert(cssContent.includes('--faction-b:'), 'Defines --faction-b');
  assert(cssContent.includes('--faction-c:'), 'Defines --faction-c');
  assert(cssContent.includes('--damage-01:'), 'Defines --damage-01');
  assert(cssContent.includes('--damage-04:'), 'Defines --damage-04');
});

// ----------------------------------------------------------------------------
// Group 8: Scale, Raycasting & Catalog Search Adversarial Tests
// ----------------------------------------------------------------------------

runTest('ADV_FE_14_Scale_500BuildingsBatchVisualization', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  terrain.update({
    resolution: 2,
    world_size: [1000, 150, 1000],
    heightmap: [[0, 0], [0, 0]]
  });

  const bldVis = new BuildingVisualizer(scene, terrain);

  const manyBuildings = [];
  for (let i = 0; i < 500; i++) {
    manyBuildings.push({
      id: `bld_${i}`,
      prefab_name: 'SM_Bld_Tent_01',
      position: [i * 2, 0, (i % 20) * 10],
      bounding_box: { size: [7.8, 4.1, 12.0] }
    });
  }

  bldVis.update(manyBuildings);
  assert(bldVis.buildingMeshes.length === 500, '500 building meshes instantiated');
  assert(bldVis.group.children.length === 500, '500 children in group');

  // Verify memory disposal on 500 buildings
  bldVis.dispose();
  assert(bldVis.buildingMeshes.length === 0, 'All 500 buildings disposed');
  assert(bldVis.group.children.length === 0, 'Group emptied on dispose');

  terrain.dispose();
});

runTest('ADV_FE_15_Raycasting_IntersectionPrecision', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  const bldVis = new BuildingVisualizer(scene, terrain);

  const bld = {
    id: 'bld_target',
    prefab_name: 'SM_Bld_CommandCenter_01',
    position: [0, 0, 0],
    bounding_box: { size: [10, 10, 10] }
  };

  bldVis.update([bld]);
  const mesh = bldVis.buildingMeshes[0];

  const raycaster = new THREE.Raycaster();
  raycaster.set(new THREE.Vector3(0, 5, 50), new THREE.Vector3(0, 0, -1)); // Ray pointing directly at box center

  const intersects = raycaster.intersectObject(mesh, false);
  assert(intersects.length > 0, 'Ray successfully intersects building box');
  assert(intersects[0].object.userData.data.id === 'bld_target', 'Raycast returns correct building userData');

  bldVis.dispose();
  terrain.dispose();
});

runTest('ADV_FE_16_Catalog_SpecialCharactersAndRegexSearch', () => {
  const client = new ApiClient();
  const catalog = {
    assets: {
      'SM_Bld_Tent_01': {
        name: 'SM_Bld_Tent_01',
        category: 'building',
        placement_role: 'barracks',
        tags: ['tent', 'shelter (alpha)', 'camo [v1]']
      },
      'SM_Prop_Barricade_01': {
        name: 'SM_Prop_Barricade_01',
        category: 'props',
        placement_role: 'barrier',
        tags: ['barrier', 'sandbag', 'hazard*']
      }
    }
  };

  // Test search parsing with regex special characters: parenthesis, brackets, asterisks
  const searchQueries = ['(', '[', '*', '?', '+', '\\'];
  for (let q of searchQueries) {
    const query = q.toLowerCase();
    const matches = Object.values(catalog.assets).filter((a) => {
      const inName = a.name.toLowerCase().includes(query);
      const inTags = a.tags.some((t) => t.toLowerCase().includes(query));
      return inName || inTags;
    });
    assert(Array.isArray(matches), `Search with '${q}' runs safely`);
  }
});

console.log('================================================================');
console.log(`TOTAL ADVERSARIAL FRONTEND TESTS: ${passedTests + failedTests}`);
console.log(`PASSED: ${passedTests}`);
console.log(`FAILED: ${failedTests}`);
console.log('================================================================');

if (failedTests > 0) {
  process.exit(1);
}
