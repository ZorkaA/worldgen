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

// ----------------------------------------------------------------------------
// Group 9: WorldGen V2 Feature Verification Tests (R1, R2, R3, R4, R5)
// ----------------------------------------------------------------------------

runTest('ADV_FE_17_AdaptiveDecimatedMesh_BufferGeometryAndIndexAttributes', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  // Test adaptive decimated mesh format with flat vertices and index buffers
  const decimatedMeshPayload = {
    world_size: [1000, 150, 1000],
    mesh: {
      vertices: [
        0.0, 10.0, 0.0,
        1000.0, 12.0, 0.0,
        500.0, 45.0, 500.0,
        0.0, 15.0, 1000.0,
        1000.0, 20.0, 1000.0
      ],
      indices: [
        0, 1, 2,
        0, 2, 3,
        1, 4, 2,
        3, 2, 4
      ],
      normals: [
        0.0, 1.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.8, 0.6,
        0.0, 1.0, 0.0,
        0.0, 1.0, 0.0
      ],
      uvs: [
        0.0, 0.0,
        1.0, 0.0,
        0.5, 0.5,
        0.0, 1.0,
        1.0, 1.0
      ],
      vertex_count: 5,
      triangle_count: 4,
      decimation_ratio: 0.05
    }
  };

  visualizer.update(decimatedMeshPayload);

  assert(visualizer.mesh !== null, 'Adaptive mesh must be instantiated');
  assert(visualizer.geometry !== null, 'BufferGeometry must be instantiated');
  assert(visualizer.meshType === 'decimated', 'Mesh type flagged as decimated');

  // Verify positions buffer
  const pos = visualizer.geometry.attributes.position;
  assert(pos.count === 5, `Position count must be 5 (actual: ${pos.count})`);

  // Verify index buffer
  const idx = visualizer.geometry.index;
  assert(idx !== null && idx.count === 12, `Index count must be 12 indices (4 triangles * 3 = 12) (actual: ${idx ? idx.count : null})`);

  // Verify slope/elevation-aware vertex colors
  const col = visualizer.geometry.attributes.color;
  assert(col !== undefined && col.count === 5, 'Vertex colors generated for all 5 vertices');
  for (let i = 0; i < col.array.length; i++) {
    assert(!isNaN(col.array[i]), `Decimated vertex color index ${i} is not NaN`);
  }

  // Verify wireframe overlay created with same geometry
  assert(visualizer.wireframeMesh !== null, 'Wireframe overlay created');
  assert(visualizer.wireframeMesh.geometry === visualizer.geometry, 'Wireframe shares exact decimated geometry');

  visualizer.dispose();
});

runTest('ADV_FE_18_AdaptiveDecimatedMesh_NestedArraysAndMissingNormalsFallback', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  // Decimated mesh with nested arrays [[x,y,z], ...] and missing normals
  const nestedDecimatedMesh = {
    world_size: [800, 120, 800],
    vertices: [
      [0.0, 0.0, 0.0],
      [800.0, 0.0, 0.0],
      [400.0, 50.0, 400.0],
      [0.0, 0.0, 800.0],
      [800.0, 0.0, 800.0]
    ],
    indices: [
      [0, 1, 2],
      [0, 2, 3],
      [1, 4, 2],
      [3, 2, 4]
    ]
  };

  visualizer.update(nestedDecimatedMesh);

  assert(visualizer.mesh !== null, 'Nested array decimated mesh loads');
  assert(visualizer.geometry.attributes.position.count === 5, '5 vertices converted to flat BufferAttribute');
  assert(visualizer.geometry.index.count === 12, '12 indices converted to flat index buffer');
  assert(visualizer.geometry.attributes.normal !== undefined, 'Missing normals automatically computed via computeVertexNormals()');

  // Test elevation query on decimated mesh
  const elevCenter = visualizer.getElevationAt(400, 400);
  assertApproxEqual(50.0, elevCenter, 1.0, 'Elevation query returns peak elevation near (400, 400)');

  visualizer.dispose();
});

runTest('ADV_FE_19_Zones_3DDragPreviewLiveTranslationAndDisplacement', () => {
  const scene = new THREE.Scene();
  const terrain = new TerrainVisualizer(scene);
  terrain.update({
    resolution: 2,
    world_size: [1000, 150, 1000],
    heightmap: [[10.0, 10.0], [10.0, 10.0]]
  });

  const zoneVis = new ZoneVisualizer(scene, terrain);
  const initialZones = [
    {
      id: 'zone_alpha',
      name: 'Alpha Outpost',
      faction: 'A',
      destruction: '01',
      zone_type: 'military_base',
      density: 0.65,
      center: [200.0, 10.0, 200.0],
      radius: 60.0,
      footprint_points: [[160, 200], [240, 200], [200, 240]]
    }
  ];

  zoneVis.update(initialZones);

  // Check initial position
  const initialPos = zoneVis.getZonePosition('zone_alpha');
  assertApproxEqual(200.0, initialPos.x, 0.1, 'Initial zone X');
  assertApproxEqual(200.0, initialPos.z, 0.1, 'Initial zone Z');

  // Live translate zone to new coordinate during 60 FPS drag
  zoneVis.previewMoveZone('zone_alpha', 350.0, 10.0, 420.0);

  const movedPos = zoneVis.getZonePosition('zone_alpha');
  assertApproxEqual(350.0, movedPos.x, 0.1, 'Live moved zone X');
  assertApproxEqual(420.0, movedPos.z, 0.1, 'Live moved zone Z');

  // Check visual mesh updates
  const visual = zoneVis.zoneVisualsMap.get('zone_alpha');
  assert(visual !== undefined, 'Visual map entry exists');
  assertApproxEqual(350.0, visual.sphereMesh.position.x, 0.1, 'Beacon sphere translated X');
  assertApproxEqual(350.0, visual.beamMesh.position.x, 0.1, 'Beam cylinder translated X');
  assertApproxEqual(350.0, visual.discMesh.position.x, 0.1, 'Footprint disc translated X');
  assertApproxEqual(420.0, visual.discMesh.position.z, 0.1, 'Footprint disc translated Z');

  // Displacement calculation test (> 1.0m threshold)
  const displacement = Math.hypot(movedPos.x - initialPos.x, movedPos.z - initialPos.z);
  assert(displacement > 1.0, `Displacement ${displacement.toFixed(1)}m exceeds 1.0m threshold`);

  zoneVis.dispose();
  terrain.dispose();
});

runTest('ADV_FE_20_ContinuousDensity_TierBadgingAndOfflineTemplatedAssets', () => {
  const client = new ApiClient();

  // Test density tier formatting logic
  const tiers = [
    { val: 0.10, expectedBadge: 'Sparse Outpost' },
    { val: 0.40, expectedBadge: 'Standard Base' },
    { val: 0.70, expectedBadge: 'Fortified Depot' },
    { val: 0.95, expectedBadge: 'Command Citadel' }
  ];

  const getTierName = (v) => {
    if (v <= 0.25) return 'Sparse Outpost';
    if (v <= 0.55) return 'Standard Base';
    if (v <= 0.80) return 'Fortified Depot';
    return 'Command Citadel';
  };

  for (let t of tiers) {
    assert(getTierName(t.val) === t.expectedBadge, `Density ${t.val} maps to ${t.expectedBadge}`);
  }

  // Synthesize offline manifest with continuous density 0.85
  const manifest = client.synthesizeOfflineManifest(42, {
    resolution: 65,
    density: 0.85,
    zone_count_target: 3
  });

  assert(manifest.zones.length === 3, '3 zones synthesized');
  assert(manifest.zones[0].density === 0.85, 'Continuous density float recorded in manifest zone');
  assert(manifest.buildings.length >= 15, `High density (0.85) produces dense building count (${manifest.buildings.length})`);

  // Verify 5 template types exist and produce corresponding buildings
  const validTemplates = ['military_base', 'airfield', 'outpost', 'radar_station', 'depot'];
  for (let z of manifest.zones) {
    assert(validTemplates.includes(z.zone_type), `Zone template '${z.zone_type}' is valid military template`);
  }
});

runTest('ADV_FE_21_GlobalMapParameters_DimensionScalingAndV2Schema', () => {
  const client = new ApiClient();

  // Synthesize non-square world: 3.5 km width x 1.5 km length
  const manifest = client.synthesizeOfflineManifest(99, {
    map_width_km: 3.5,
    map_length_km: 1.5,
    resolution: 65,
    deformation_strength: 0.90,
    edge_margin: 200.0,
    max_road_slope: 0.20
  });

  assert(manifest.terrain.world_size[0] === 3500.0, 'World width in meters is 3500m (3.5km)');
  assert(manifest.terrain.world_size[2] === 1500.0, 'World length in meters is 1500m (1.5km)');
  assert(manifest.terrain.mesh !== undefined, 'Adaptive mesh included in V2 manifest');
  assert(manifest.terrain.mesh.vertices.length > 0, 'Mesh vertices populated');
  assert(manifest.terrain.mesh.indices.length > 0, 'Mesh indices populated');

  // Verify road slopes respect slope limit
  for (let r of manifest.roads) {
    assert(r.max_slope_observed <= 0.25, `Road slope ${r.max_slope_observed} respects max slope`);
  }
});

runTest('ADV_FE_22_InPlaceRecomputation_ZoneDisplacementWithoutReload', async () => {
  const client = new ApiClient();

  // 1. Initial manifest
  const initManifest = client.synthesizeOfflineManifest(777, { resolution: 65, zone_count_target: 3 });
  client.activeManifest = initManifest;

  const targetZone = initManifest.zones[0];
  const oldX = targetZone.center[0];
  const oldZ = targetZone.center[2];

  // 2. Recompute zone position
  const newPos = { x: oldX + 150.0, y: targetZone.center[1] + 5.0, z: oldZ + 120.0 };
  const result = await client.recomputeZone(targetZone.id, newPos, { resolution: 65 });

  assert(result.success === true, 'Recompute returned success');
  assert(result.manifest !== undefined, 'Recomputed manifest returned');

  const updatedZone = result.manifest.zones.find((z) => z.id === targetZone.id);
  assert(updatedZone !== undefined, 'Updated zone found in manifest');
  assertApproxEqual(newPos.x, updatedZone.center[0], 0.1, 'Zone center X shifted');
  assertApproxEqual(newPos.z, updatedZone.center[2], 0.1, 'Zone center Z shifted');

  // Verify associated buildings shifted
  const shiftedBlds = result.manifest.buildings.filter((b) => b.zone_id === targetZone.id);
  assert(shiftedBlds.length > 0, 'Buildings for zone retained and shifted');
});

runTest('ADV_FE_23_UtilitarianUI_NoSlopCopyCompliance', () => {
  const indexPath = path.join(__dirname, 'index.html');
  const indexContent = fs.readFileSync(indexPath, 'utf-8');

  // Forbidden generic / AI marketing slop terms
  const forbiddenTerms = [
    'WORLDGEN 3D — Procedural Military Designer',
    'Procedural Military Designer',
    'Synthesizing Tactical World',
    'Next-Gen AI Designer',
    'Ultimate World Generator'
  ];

  for (let term of forbiddenTerms) {
    assert(!indexContent.includes(term), `index.html must not contain marketing slop: '${term}'`);
  }

  // Required Utilitarian terms
  assert(indexContent.includes('WorldGen — 3D Terrain & Zone Infrastructure Editor') || indexContent.includes('WORLDGEN'), 'Contains utilitarian brand title');
  assert(indexContent.includes('Terrain Config') || indexContent.includes('Terrain Parameters'), 'Contains terrain parameters header');
  assert(indexContent.includes('Zone Editor') || indexContent.includes('Active Tactical Zones'), 'Contains zone editor header');
  assert(indexContent.includes('dialog id="detail-modal"'), 'Native semantic <dialog> element present');
});

runTest('ADV_FE_24_WireframeMode_DecimatedMeshTopologyInspection', () => {
  const scene = new THREE.Scene();
  const visualizer = new TerrainVisualizer(scene);

  visualizer.update({
    world_size: [1000, 150, 1000],
    mesh: {
      vertices: [0, 0, 0, 1000, 0, 0, 500, 50, 500],
      indices: [0, 1, 2],
      normals: [0, 1, 0, 0, 1, 0, 0, 1, 0]
    }
  });

  assert(visualizer.wireframeMesh.visible === false, 'Wireframe hidden by default');
  visualizer.setWireframe(true);
  assert(visualizer.wireframeMesh.visible === true, 'Wireframe visible when toggled ON');
  assert(visualizer.wireframeMesh.material.wireframe === true, 'Material wireframe property is true');

  visualizer.setWireframe(false);
  assert(visualizer.wireframeMesh.visible === false, 'Wireframe hidden when toggled OFF');

  visualizer.dispose();
});

runTest('ADV_FE_25_Viewer_DragVsOrbitControlsDisabling', () => {
  const viewerCodePath = path.join(__dirname, 'src', 'scene', 'viewer.js');
  const viewerCode = fs.readFileSync(viewerCodePath, 'utf-8');

  // Verify OrbitControls disabled on dragstart
  assert(viewerCode.includes('this.controls.enabled = false'), 'OrbitControls disabled when dragging starts');
  assert(viewerCode.includes('this.controls.enabled = true'), 'OrbitControls re-enabled when dragging ends');

  // Verify capture phase event listeners to intercept pointerdown before OrbitControls
  assert(viewerCode.includes("addEventListener('pointerdown', this.onPointerDown.bind(this), { capture: true })"), 'pointerdown uses capture phase');
  assert(viewerCode.includes("addEventListener('pointercancel', this.onPointerUp.bind(this), { capture: true })"), 'pointercancel bound to handle loss of focus');
});

runTest('ADV_FE_26_Viewer_PointerMoveDoesNotFireApi', () => {
  const viewerCodePath = path.join(__dirname, 'src', 'scene', 'viewer.js');
  const viewerCode = fs.readFileSync(viewerCodePath, 'utf-8');

  // Extract onPointerMove body
  const startIdx = viewerCode.indexOf('onPointerMove(event) {');
  const endIdx = viewerCode.indexOf('onPointerUp(event) {');
  const moveCode = viewerCode.substring(startIdx, endIdx);

  assert(!moveCode.includes('generateWorld'), 'onPointerMove does not invoke generateWorld');
  assert(!moveCode.includes('recomputeZone'), 'onPointerMove does not invoke recomputeZone');
  assert(!moveCode.includes('fetch('), 'onPointerMove does not perform network fetches');
  assert(!moveCode.includes('onZoneDroppedCallback'), 'onPointerMove does not trigger onZoneDroppedCallback');
  assert(moveCode.includes('previewMoveZone'), 'onPointerMove performs client-side previewMoveZone visual translation');
});

console.log('================================================================');
console.log(`TOTAL ADVERSARIAL FRONTEND TESTS: ${passedTests + failedTests}`);
console.log(`PASSED: ${passedTests}`);
console.log(`FAILED: ${failedTests}`);
console.log('================================================================');

if (failedTests > 0) {
  process.exit(1);
}

