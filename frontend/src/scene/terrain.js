import * as THREE from 'three';

/**
 * Procedural & Adaptive Terrain Mesh Manager
 * Supports:
 * 1. Adaptive Decimated Indexed Meshes (terrain.mesh with variable-density triangles).
 * 2. Regular Grid Heightmaps (PlaneGeometry with dynamic vertex elevation displacement).
 * Computes slope and elevation-aware vertex coloring, normal computation,
 * toggleable wireframe inspection mode, and spatial elevation queries.
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
    this.meshType = 'grid'; // 'grid' | 'decimated'
    this.decimatedStats = null;
  }

  /**
   * Build or update the terrain mesh from manifest terrain data
   */
  update(terrainData) {
    // Clean up existing meshes
    this.dispose();

    if (!terrainData) {
      console.warn('Invalid terrain data for TerrainVisualizer: terrainData is null or undefined');
      return;
    }

    this.worldSize = terrainData.world_size || [1000, 150, 1000];
    if (terrainData.heightmap && Array.isArray(terrainData.heightmap) && terrainData.heightmap.length > 0) {
      this.heightmap2D = terrainData.heightmap;
    }

    const meshData = terrainData.mesh || (terrainData.vertices && terrainData.indices ? terrainData : null);

    // Check if adaptive decimated mesh data is provided
    if (meshData && meshData.vertices && meshData.indices && meshData.vertices.length > 0) {
      this.buildDecimatedMesh(meshData, terrainData);
    } else if (terrainData.heightmap && Array.isArray(terrainData.heightmap) && terrainData.heightmap.length > 0) {
      this.buildGridMesh(terrainData);
    } else {
      console.warn('Invalid terrain data for TerrainVisualizer: missing mesh and heightmap');
    }
  }

  /**
   * Build adaptive decimated mesh from indexed vertex buffers
   */
  buildDecimatedMesh(meshData, terrainData) {
    this.meshType = 'decimated';
    const [width, heightScale, length] = this.worldSize;

    // 1. Normalize vertices (flat Float32Array or array of [x, y, z])
    let positions;
    if (meshData.vertices instanceof Float32Array) {
      positions = meshData.vertices;
    } else if (Array.isArray(meshData.vertices)) {
      if (typeof meshData.vertices[0] === 'number') {
        positions = new Float32Array(meshData.vertices);
      } else if (Array.isArray(meshData.vertices[0])) {
        // Flatten nested array [[x, y, z], ...]
        positions = new Float32Array(meshData.vertices.length * 3);
        for (let i = 0; i < meshData.vertices.length; i++) {
          positions[i * 3] = meshData.vertices[i][0];
          positions[i * 3 + 1] = meshData.vertices[i][1];
          positions[i * 3 + 2] = meshData.vertices[i][2];
        }
      }
    }

    if (!positions || positions.length === 0) {
      console.warn('Decimated mesh has empty positions buffer');
      return;
    }

    // 2. Normalize indices (Uint32Array or array of ints/triangles)
    let indices;
    if (meshData.indices instanceof Uint32Array || meshData.indices instanceof Uint16Array) {
      indices = meshData.indices;
    } else if (Array.isArray(meshData.indices)) {
      if (typeof meshData.indices[0] === 'number') {
        indices = new Uint32Array(meshData.indices);
      } else if (Array.isArray(meshData.indices[0])) {
        // Flatten nested array [[i0, i1, i2], ...]
        indices = new Uint32Array(meshData.indices.length * 3);
        for (let i = 0; i < meshData.indices.length; i++) {
          indices[i * 3] = meshData.indices[i][0];
          indices[i * 3 + 1] = meshData.indices[i][1];
          indices[i * 3 + 2] = meshData.indices[i][2];
        }
      }
    }

    if (!indices || indices.length === 0) {
      console.warn('Decimated mesh has empty indices buffer');
      return;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));

    // 3. Normals (use provided or compute)
    if (meshData.normals && meshData.normals.length > 0) {
      let normals;
      if (meshData.normals instanceof Float32Array) {
        normals = meshData.normals;
      } else if (typeof meshData.normals[0] === 'number') {
        normals = new Float32Array(meshData.normals);
      } else if (Array.isArray(meshData.normals[0])) {
        normals = new Float32Array(meshData.normals.length * 3);
        for (let i = 0; i < meshData.normals.length; i++) {
          normals[i * 3] = meshData.normals[i][0];
          normals[i * 3 + 1] = meshData.normals[i][1];
          normals[i * 3 + 2] = meshData.normals[i][2];
        }
      }
      if (normals && normals.length === positions.length) {
        geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
      } else {
        geometry.computeVertexNormals();
      }
    } else {
      geometry.computeVertexNormals();
    }

    // 4. UVs (optional)
    if (meshData.uvs && meshData.uvs.length > 0) {
      let uvs;
      if (meshData.uvs instanceof Float32Array) {
        uvs = meshData.uvs;
      } else if (typeof meshData.uvs[0] === 'number') {
        uvs = new Float32Array(meshData.uvs);
      } else if (Array.isArray(meshData.uvs[0])) {
        uvs = new Float32Array(meshData.uvs.length * 2);
        for (let i = 0; i < meshData.uvs.length; i++) {
          uvs[i * 2] = meshData.uvs[i][0];
          uvs[i * 2 + 1] = meshData.uvs[i][1];
        }
      }
      if (uvs && uvs.length === (positions.length / 3) * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
      }
    }

    // 5. Compute slope & elevation-aware vertex colors
    this.applyTacticalVertexColors(geometry, positions);

    // 6. Create Shaded Material with Vertex Colors
    this.material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.85,
      metalness: 0.1,
      flatShading: false,
      side: THREE.DoubleSide
    });

    this.geometry = geometry;
    this.mesh = new THREE.Mesh(this.geometry, this.material);
    this.mesh.name = 'AdaptiveTerrainMesh';
    this.mesh.receiveShadow = true;
    this.mesh.castShadow = false;
    this.scene.add(this.mesh);

    // 7. Create Wireframe Overlay Mesh with matching topology
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x22c55e,
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    this.wireframeMesh = new THREE.Mesh(this.geometry, wireMat);
    this.wireframeMesh.name = 'TerrainWireframe';
    this.wireframeMesh.position.y += 0.08; // slightly elevated to avoid z-fighting
    this.wireframeMesh.visible = this.isWireframeVisible;
    this.scene.add(this.wireframeMesh);

    this.decimatedStats = {
      vertexCount: positions.length / 3,
      triangleCount: indices.length / 3,
      decimationRatio: meshData.decimation_ratio || (indices.length / 3) / ((129 - 1) * (129 - 1) * 2)
    };
  }

  /**
   * Build regular grid mesh from 2D heightmap array (backwards compatible)
   */
  buildGridMesh(terrainData) {
    this.meshType = 'grid';
    const rawHeightmap = terrainData.heightmap;
    this.heightmap2D = rawHeightmap;
    const res = Array.isArray(terrainData.resolution) ? terrainData.resolution[0] : (terrainData.resolution || rawHeightmap.length);
    this.resolution = res;

    const [width, heightScale, length] = this.worldSize;
    const resX = rawHeightmap[0].length;
    const resZ = rawHeightmap.length;

    // 1. Create base PlaneGeometry (resX-1) x (resZ-1) segments -> resX x resZ vertices
    const geometry = new THREE.PlaneGeometry(width, length, resX - 1, resZ - 1);

    // 2. Rotate to horizontal XZ plane and translate to positive quadrant [0..width, 0, 0..length]
    geometry.rotateX(-Math.PI / 2);
    geometry.translate(width / 2, 0, length / 2);

    const positions = geometry.attributes.position.array;
    const vertexCount = positions.length / 3;

    // 3. Inject elevations into Y coordinates
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
    this.applyTacticalVertexColors(geometry, positions);

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
    this.wireframeMesh.position.y += 0.05;
    this.wireframeMesh.visible = this.isWireframeVisible;
    this.scene.add(this.wireframeMesh);
  }

  /**
   * Calculate and apply military tactical slope/height vertex colors to geometry
   */
  applyTacticalVertexColors(geometry, positions) {
    const vertexCount = positions.length / 3;
    const normals = geometry.attributes.normal.array;
    const colors = new Float32Array(vertexCount * 3);

    // Find min and max height
    let minH = Infinity;
    let maxH = -Infinity;
    for (let i = 0; i < vertexCount; i++) {
      const y = positions[i * 3 + 1];
      if (y < minH) minH = y;
      if (y > maxH) maxH = y;
    }
    const hRange = Math.max(0.001, maxH - minH);

    // Tactical Color Palettes:
    const cGrass = new THREE.Color(0x4a7c59);
    const cSand = new THREE.Color(0xc2b280);
    const cDirt = new THREE.Color(0x7d6b53);
    const cRock = new THREE.Color(0x404347);
    const cPeak = new THREE.Color(0xd1d5db);

    const tmpColor = new THREE.Color();

    for (let i = 0; i < vertexCount; i++) {
      const y = positions[i * 3 + 1];
      const ny = normals[i * 3 + 1]; // Upward normal component (1.0 = flat, 0.0 = cliff)
      const normY = (y - minH) / hRange;

      if (normY < 0.08) {
        // Shoreline / Lowland
        tmpColor.copy(cSand).lerp(cGrass, normY / 0.08);
      } else if (normY > 0.82 && ny > 0.6) {
        // High mountain peaks
        tmpColor.copy(cRock).lerp(cPeak, (normY - 0.82) / 0.18);
      } else {
        // Slope-dependent coloring
        if (ny > 0.85) {
          // Flat plains / gentle hills
          tmpColor.copy(cGrass);
        } else if (ny > 0.65) {
          // Moderate slope -> scree / dirt
          const t = (ny - 0.65) / 0.20;
          tmpColor.copy(cDirt).lerp(cGrass, t);
        } else {
          // Steep cliffs / rock face
          const t = Math.max(0, ny / 0.65);
          tmpColor.copy(cRock).lerp(cDirt, t);
        }
      }

      colors[i * 3] = tmpColor.r;
      colors[i * 3 + 1] = tmpColor.g;
      colors[i * 3 + 2] = tmpColor.b;
    }

    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
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
   * Sample elevation at world coordinates (wx, wz)
   */
  getElevationAt(wx, wz) {
    const [width, , length] = this.worldSize;

    if (this.heightmap2D && this.heightmap2D.length > 0) {
      const resZ = this.heightmap2D.length;
      const resX = this.heightmap2D[0].length;

      const clampedWx = Math.max(0, Math.min(width, wx));
      const clampedWz = Math.max(0, Math.min(length, wz));

      const gx = (clampedWx / width) * (resX - 1);
      const gz = (clampedWz / length) * (resZ - 1);

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

    // If only decimated mesh is present without 2D heightmap grid,
    // do a fast nearest-vertex elevation fallback
    if (this.geometry && this.geometry.attributes.position) {
      const positions = this.geometry.attributes.position.array;
      const count = positions.length / 3;
      let closestDistSq = Infinity;
      let closestY = 0;
      for (let i = 0; i < count; i++) {
        const vx = positions[i * 3];
        const vy = positions[i * 3 + 1];
        const vz = positions[i * 3 + 2];
        const dSq = (vx - wx) * (vx - wx) + (vz - wz) * (vz - wz);
        if (dSq < closestDistSq) {
          closestDistSq = dSq;
          closestY = vy;
          if (dSq < 1.0) break;
        }
      }
      return closestY;
    }

    return 0;
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

