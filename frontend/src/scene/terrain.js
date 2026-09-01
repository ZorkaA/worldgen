import * as THREE from 'three';

/**
 * Procedural Terrain Mesh Manager
 * Manages PlaneGeometry displacement, dynamic normal computation,
 * slope/elevation vertex coloring, wireframe overlays, and elevation queries.
 */
export class TerrainVisualizer {
  constructor(scene) {
    this.scene = scene;
    this.mesh = null;
    this.wireframeMesh = null;
    this.geometry = null;
    this.material = null;
    this.heightmap2D = null;
    this.resolution = 129;
    this.worldSize = [1000, 150, 1000];
    this.isWireframeVisible = false;
  }

  /**
   * Build or update the terrain mesh from manifest terrain data
   */
  update(terrainData) {
    // Clean up existing meshes
    this.dispose();

    if (!terrainData || !terrainData.heightmap) {
      console.warn('Invalid terrain data for TerrainVisualizer');
      return;
    }

    const rawHeightmap = terrainData.heightmap;
    this.heightmap2D = rawHeightmap;
    const res = Array.isArray(terrainData.resolution) ? terrainData.resolution[0] : (terrainData.resolution || rawHeightmap.length);
    this.resolution = res;
    this.worldSize = terrainData.world_size || [1000, 150, 1000];

    const [width, heightScale, length] = this.worldSize;
    const resX = rawHeightmap[0].length;
    const resZ = rawHeightmap.length;

    // 1. Create base PlaneGeometry
    // PlaneGeometry creates (resX-1) x (resZ-1) segments -> resX x resZ vertices
    const geometry = new THREE.PlaneGeometry(width, length, resX - 1, resZ - 1);

    // 2. Rotate to horizontal XZ plane and translate to positive quadrant [0..width, 0, 0..length]
    geometry.rotateX(-Math.PI / 2);
    geometry.translate(width / 2, 0, length / 2);

    const positions = geometry.attributes.position.array;
    const vertexCount = positions.length / 3;

    // Find min and max height for normalization
    let minH = Infinity;
    let maxH = -Infinity;

    for (let z = 0; z < resZ; z++) {
      for (let x = 0; x < resX; x++) {
        const val = rawHeightmap[z][x];
        if (val < minH) minH = val;
        if (val > maxH) maxH = val;
      }
    }
    const hRange = Math.max(0.001, maxH - minH);

    // 3. Inject elevations into Y coordinates
    // In Three.js PlaneGeometry(w, l, segX, segZ) rotated -PI/2:
    // Vertices order: row by row along Z, then X
    for (let i = 0; i < vertexCount; i++) {
      const xIdx = i % resX;
      const zIdx = Math.floor(i / resX);
      const safeZ = Math.min(resZ - 1, zIdx);
      const safeX = Math.min(resX - 1, xIdx);
      const elevation = rawHeightmap[safeZ][safeX];
      positions[i * 3 + 1] = elevation;
    }

    geometry.attributes.position.needsUpdate = true;
    geometry.computeVertexNormals();

    // 4. Compute slope & elevation-aware vertex colors
    const normals = geometry.attributes.normal.array;
    const colors = new Float32Array(vertexCount * 3);

    // Tactical Color Palettes:
    // Grass/Plains: #3d633b / #4a7c59
    const cGrass = new THREE.Color(0x4a7c59);
    // Sand/Shoreline: #c2b280
    const cSand = new THREE.Color(0xc2b280);
    // Scree/Dirt brown: #7d6b53
    const cDirt = new THREE.Color(0x7d6b53);
    // Slate rock/Cliff: #404347
    const cRock = new THREE.Color(0x404347);
    // Mountain Snow/Peak: #d1d5db
    const cPeak = new THREE.Color(0xd1d5db);

    const tmpColor = new THREE.Color();

    for (let i = 0; i < vertexCount; i++) {
      const y = positions[i * 3 + 1];
      const ny = normals[i * 3 + 1]; // Upward normal component (1.0 = perfectly flat, 0.0 = vertical cliff)
      const normY = (y - minH) / hRange;

      if (normY < 0.08) {
        // Lowland shoreline/sand
        tmpColor.copy(cSand).lerp(cGrass, normY / 0.08);
      } else if (normY > 0.82 && ny > 0.6) {
        // High mountain peaks / caps
        tmpColor.copy(cRock).lerp(cPeak, (normY - 0.82) / 0.18);
      } else {
        // Shading based on slope normal Ny
        if (ny > 0.85) {
          // Flat / Gentle slopes -> Grass
          tmpColor.copy(cGrass);
        } else if (ny > 0.65) {
          // Moderate slope -> Dirt / Scree
          const t = (ny - 0.65) / 0.20;
          tmpColor.copy(cDirt).lerp(cGrass, t);
        } else {
          // Steep cliff -> Slate rock
          const t = Math.max(0, ny / 0.65);
          tmpColor.copy(cRock).lerp(cDirt, t);
        }
      }

      colors[i * 3] = tmpColor.r;
      colors[i * 3 + 1] = tmpColor.g;
      colors[i * 3 + 2] = tmpColor.b;
    }

    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // 5. Create Shaded Material with Vertex Colors
    this.material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.85,
      metalness: 0.1,
      flatShading: false,
      side: THREE.DoubleSide
    });

    this.geometry = geometry;
    this.mesh = new THREE.Mesh(this.geometry, this.material);
    this.mesh.name = 'TerrainMesh';
    this.mesh.receiveShadow = true;
    this.mesh.castShadow = false;
    this.scene.add(this.mesh);

    // 6. Create Wireframe Overlay Mesh
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x22c55e,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    this.wireframeMesh = new THREE.Mesh(this.geometry, wireMat);
    this.wireframeMesh.name = 'TerrainWireframe';
    this.wireframeMesh.position.y += 0.05; // avoid z-fighting
    this.wireframeMesh.visible = this.isWireframeVisible;
    this.scene.add(this.wireframeMesh);
  }

  /**
   * Toggle wireframe mode
   */
  setWireframe(enabled) {
    this.isWireframeVisible = enabled;
    if (this.wireframeMesh) {
      this.wireframeMesh.visible = enabled;
    }
  }

  /**
   * Sample elevation at world coordinates (wx, wz) with bilinear interpolation
   */
  getElevationAt(wx, wz) {
    if (!this.heightmap2D) return 0;
    const [width, , length] = this.worldSize;
    const resZ = this.heightmap2D.length;
    const resX = this.heightmap2D[0].length;

    const gx = (wx / width) * (resX - 1);
    const gz = (wz / length) * (resZ - 1);

    const x0 = Math.max(0, Math.min(resX - 1, Math.floor(gx)));
    const x1 = Math.max(0, Math.min(resX - 1, Math.ceil(gx)));
    const z0 = Math.max(0, Math.min(resZ - 1, Math.floor(gz)));
    const z1 = Math.max(0, Math.min(resZ - 1, Math.ceil(gz)));

    const tx = gx - x0;
    const tz = gz - z0;

    const h00 = this.heightmap2D[z0][x0];
    const h10 = this.heightmap2D[z0][x1];
    const h01 = this.heightmap2D[z1][x0];
    const h11 = this.heightmap2D[z1][x1];

    const hTop = h00 * (1 - tx) + h10 * tx;
    const hBot = h01 * (1 - tx) + h11 * tx;

    return hTop * (1 - tz) + hBot * tz;
  }

  dispose() {
    if (this.mesh) {
      this.scene.remove(this.mesh);
      if (this.geometry) this.geometry.dispose();
      if (this.material) this.material.dispose();
      this.mesh = null;
    }
    if (this.wireframeMesh) {
      this.scene.remove(this.wireframeMesh);
      this.wireframeMesh = null;
    }
  }
}
