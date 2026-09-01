import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { TerrainVisualizer } from './terrain.js';
import { ZoneVisualizer } from './zones.js';
import { BuildingVisualizer } from './buildings.js';
import { RoadVisualizer } from './roads.js';

/**
 * Main 3D WebGL World Viewer
 * Orchestrates Three.js Scene, WebGLRenderer, PerspectiveCamera, OrbitControls,
 * Directional & Ambient Lighting, Subsystem Visualizers, Raycasting, and Camera Presets.
 */
export class WorldViewer {
  constructor(canvasElement, options = {}) {
    this.canvas = canvasElement;
    this.options = options;

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.sunLight = null;
    this.hemiLight = null;

    // Subsystems
    this.terrain = null;
    this.zones = null;
    this.buildings = null;
    this.roads = null;

    // State & Animation
    this.animationFrameId = null;
    this.clock = new THREE.Clock();
    this.worldBounds = [1000, 150, 1000];
    this.currentManifest = null;

    // Raycasting & Interaction
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.hoveredObject = null;
    this.onHoverCallback = options.onHover || null;
    this.onClickCallback = options.onClick || null;

    // Camera Animation Transition
    this.targetCamPos = null;
    this.targetCamLookAt = null;
    this.isTransitioningCam = false;

    // Performance Stats
    this.frameCount = 0;
    this.lastFpsTime = performance.now();
    this.fps = 60;
    this.onStatsCallback = options.onStats || null;

    this.init();
  }

  init() {
    // 1. Create Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0f1d);
    this.scene.fog = new THREE.FogExp2(0x0a0f1d, 0.0004);

    // 2. Create Camera
    const aspect = this.canvas.clientWidth / (this.canvas.clientHeight || 1);
    this.camera = new THREE.PerspectiveCamera(55, aspect, 0.5, 5000);
    this.camera.position.set(500, 450, 950);

    // 3. Create WebGLRenderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance',
      stencil: false,
    });
    this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 4. OrbitControls with smooth damping and ground clipping protection
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.maxPolarAngle = Math.PI / 2.05; // Prevents camera dipping under terrain
    this.controls.minDistance = 10;
    this.controls.maxDistance = 3500;
    this.controls.target.set(500, 20, 500);

    // 5. Lighting Setup
    this.setupLighting();

    // 6. Instantiate Subsystems
    this.terrain = new TerrainVisualizer(this.scene);
    this.zones = new ZoneVisualizer(this.scene, this.terrain);
    this.buildings = new BuildingVisualizer(this.scene, this.terrain);
    this.roads = new RoadVisualizer(this.scene, this.terrain);

    // 7. Event Listeners
    window.addEventListener('resize', this.onWindowResize.bind(this));
    this.canvas.addEventListener('pointermove', this.onPointerMove.bind(this));
    this.canvas.addEventListener('click', this.onCanvasClick.bind(this));

    // 8. Start Render Loop
    this.animate();
  }

  setupLighting() {
    // Primary Directional Light (Sun)
    this.sunLight = new THREE.DirectionalLight(0xfffaed, 2.2);
    this.sunLight.position.set(500, 600, 800);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.sunLight.shadow.camera.near = 10;
    this.sunLight.shadow.camera.far = 2500;
    this.sunLight.shadow.camera.left = -700;
    this.sunLight.shadow.camera.right = 700;
    this.sunLight.shadow.camera.top = 700;
    this.sunLight.shadow.camera.bottom = -700;
    this.sunLight.shadow.bias = -0.0003;
    this.scene.add(this.sunLight);

    // Fill Illumination via Hemisphere Light (Sky Blue / Ground Dark Tan)
    this.hemiLight = new THREE.HemisphereLight(0x78a0dc, 0x3d352b, 0.85);
    this.hemiLight.position.set(500, 1000, 500);
    this.scene.add(this.hemiLight);

    // Ambient fill
    const ambientLight = new THREE.AmbientLight(0x202430, 0.4);
    this.scene.add(ambientLight);
  }

  /**
   * Load and render complete World Manifest
   */
  loadManifest(manifest) {
    if (!manifest) return;
    this.currentManifest = manifest;

    if (manifest.terrain) {
      this.worldBounds = manifest.terrain.world_size || [1000, 150, 1000];
      this.terrain.update(manifest.terrain);

      // Adjust sun and camera bounds
      const [w, , l] = this.worldBounds;
      this.sunLight.position.set(w * 0.5, 600, l * 0.8);
      this.controls.target.set(w / 2, 20, l / 2);
    }

    if (manifest.zones) {
      this.zones.update(manifest.zones);
    }

    if (manifest.buildings) {
      this.buildings.update(manifest.buildings);
    }

    if (manifest.roads) {
      this.roads.update(manifest.roads);
    }
  }

  /**
   * Toggle Terrain Wireframe Mode
   */
  toggleWireframe(forceState = null) {
    const nextState = forceState !== null ? forceState : !this.terrain.isWireframeVisible;
    this.terrain.setWireframe(nextState);
    return nextState;
  }

  /**
   * Camera Presets
   */
  setCameraPreset(presetName) {
    const [w, h, l] = this.worldBounds;
    const cx = w / 2;
    const cz = l / 2;

    if (presetName === 'orbit') {
      this.transitionCamera(
        new THREE.Vector3(cx + 350, 380, cz + 450),
        new THREE.Vector3(cx, 25, cz)
      );
    } else if (presetName === 'top') {
      this.transitionCamera(
        new THREE.Vector3(cx, 1350, cz + 0.01),
        new THREE.Vector3(cx, 0, cz)
      );
    } else if (presetName === 'iso') {
      this.transitionCamera(
        new THREE.Vector3(cx + 650, 550, cz + 650),
        new THREE.Vector3(cx, 0, cz)
      );
    }
  }

  /**
   * Smoothly focus camera on specific world target
   */
  focusOn(position, distance = 90) {
    if (!position) return;
    const px = position[0] !== undefined ? position[0] : position.x;
    const py = position[1] !== undefined ? position[1] : position.y;
    const pz = position[2] !== undefined ? position[2] : position.z;

    const targetPos = new THREE.Vector3(px, py, pz);
    const camPos = new THREE.Vector3(px + distance * 0.7, py + distance * 0.6, pz + distance * 0.7);

    this.transitionCamera(camPos, targetPos);
  }

  transitionCamera(newPos, newLookAt) {
    this.targetCamPos = newPos;
    this.targetCamLookAt = newLookAt;
    this.isTransitioningCam = true;
  }

  onWindowResize() {
    if (!this.canvas || !this.camera || !this.renderer) return;
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;

    this.camera.aspect = width / (height || 1);
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  onPointerMove(event) {
    const rect = this.canvas.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    // Raycast building & zone meshes
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const interactiveObjects = [...this.buildings.buildingMeshes, ...this.zones.beaconMeshes];
    const intersects = this.raycaster.intersectObjects(interactiveObjects, false);

    if (intersects.length > 0) {
      const topHit = intersects[0].object;
      this.canvas.style.cursor = 'pointer';
      if (this.hoveredObject !== topHit) {
        this.hoveredObject = topHit;
        if (topHit.userData.type === 'building') {
          this.buildings.setHighlight(topHit);
        }
        if (this.onHoverCallback) {
          this.onHoverCallback(topHit.userData, event.clientX, event.clientY);
        }
      }
    } else {
      this.canvas.style.cursor = 'default';
      if (this.hoveredObject) {
        this.hoveredObject = null;
        this.buildings.setHighlight(null);
        if (this.onHoverCallback) {
          this.onHoverCallback(null);
        }
      }
    }
  }

  onCanvasClick(event) {
    if (this.hoveredObject && this.onClickCallback) {
      this.onClickCallback(this.hoveredObject.userData);
    }
  }

  animate() {
    this.animationFrameId = requestAnimationFrame(this.animate.bind(this));

    const delta = this.clock.getDelta();
    const elapsedTime = this.clock.getElapsedTime();

    // Camera smooth transition interpolation
    if (this.isTransitioningCam && this.targetCamPos && this.targetCamLookAt) {
      this.camera.position.lerp(this.targetCamPos, 0.08);
      this.controls.target.lerp(this.targetCamLookAt, 0.08);

      if (
        this.camera.position.distanceTo(this.targetCamPos) < 1.0 &&
        this.controls.target.distanceTo(this.targetCamLookAt) < 1.0
      ) {
        this.camera.position.copy(this.targetCamPos);
        this.controls.target.copy(this.targetCamLookAt);
        this.isTransitioningCam = false;
      }
    }

    this.controls.update();

    // Animate zones beacon pulse
    if (this.zones) {
      this.zones.animate(elapsedTime);
    }

    this.renderer.render(this.scene, this.camera);

    // Performance Stats & Compass Orientation
    this.frameCount++;
    const now = performance.now();
    if (now - this.lastFpsTime >= 500) {
      this.fps = Math.round((this.frameCount * 1000) / (now - this.lastFpsTime));
      this.frameCount = 0;
      this.lastFpsTime = now;

      // Update orientation angle
      const azimuthAngle = this.controls.getAzimuthalAngle();

      if (this.onStatsCallback) {
        const triCount = this.renderer.info.render.triangles;
        this.onStatsCallback({ fps: this.fps, triangles: triCount, azimuthAngle });
      }
    }
  }

  dispose() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    window.removeEventListener('resize', this.onWindowResize);
    if (this.terrain) this.terrain.dispose();
    if (this.zones) this.zones.dispose();
    if (this.buildings) this.buildings.dispose();
    if (this.roads) this.roads.dispose();
    if (this.renderer) this.renderer.dispose();
  }
}
