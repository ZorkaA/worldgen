import * as THREE from 'three';

/**
 * 3D Road Spline Ribbon Visualizer
 * Smoothly interpolates waypoints using CatmullRomCurve3 and constructs
 * continuous quad ribbon meshes conforming to terrain elevation with zero z-fighting.
 */
export class RoadVisualizer {
  constructor(scene, terrainVisualizer) {
    this.scene = scene;
    this.terrain = terrainVisualizer;
    this.group = new THREE.Group();
    this.group.name = 'RoadsGroup';
    this.scene.add(this.group);
  }

  update(roads) {
    this.dispose();
    if (!roads || !Array.isArray(roads)) return;

    roads.forEach((road) => {
      const waypoints = road.waypoints;
      if (!waypoints || waypoints.length < 2) return;

      const roadWidth = road.width || 6.0;
      const halfWidth = roadWidth / 2.0;

      // 1. Convert waypoints to Vector3 and adjust to terrain elevation
      const rawPoints = [];
      for (let i = 0; i < waypoints.length; i++) {
        const [wx, wy, wz] = waypoints[i];
        // Filter out identical adjacent points to prevent CatmullRom NaN errors
        if (rawPoints.length > 0) {
          const last = rawPoints[rawPoints.length - 1];
          const dist = Math.hypot(wx - last.x, wz - last.z);
          if (dist < 0.5) continue;
        }
        const terrainY = this.terrain.getElevationAt(wx, wz);
        const finalY = (wy !== undefined && wy > 0) ? Math.max(terrainY, wy) : terrainY;
        rawPoints.push(new THREE.Vector3(wx, finalY + 0.15, wz)); // +0.15m vertical offset to avoid z-fighting
      }

      if (rawPoints.length < 2) return;

      // 2. Interpolate smooth curve
      const curve = new THREE.CatmullRomCurve3(rawPoints, false, 'centripetal', 0.5);
      const numSamples = Math.max(30, rawPoints.length * 15);
      const sampledPoints = curve.getPoints(numSamples);

      // Re-snap sampled curve points to terrain surface
      for (let pt of sampledPoints) {
        pt.y = this.terrain.getElevationAt(pt.x, pt.z) + 0.18;
      }

      // 3. Construct Quad Ribbon Mesh Geometry
      const vertices = [];
      const normals = [];
      const uvs = [];
      const indices = [];

      const up = new THREE.Vector3(0, 1, 0);

      for (let i = 0; i < sampledPoints.length; i++) {
        const curr = sampledPoints[i];
        const next = (i < sampledPoints.length - 1) ? sampledPoints[i + 1] : curr;
        const prev = (i > 0) ? sampledPoints[i - 1] : curr;

        // Tangent vector
        const tangent = new THREE.Vector3().subVectors(next, prev).normalize();
        if (tangent.lengthSq() < 0.0001) tangent.set(0, 0, 1);

        // Side normal vector = tangent x up
        const side = new THREE.Vector3().crossVectors(tangent, up).normalize();

        // Left and right vertices
        const left = new THREE.Vector3().copy(curr).addScaledVector(side, -halfWidth);
        const right = new THREE.Vector3().copy(curr).addScaledVector(side, halfWidth);

        // Conform side vertices to terrain elevation
        left.y = this.terrain.getElevationAt(left.x, left.z) + 0.18;
        right.y = this.terrain.getElevationAt(right.x, right.z) + 0.18;

        vertices.push(left.x, left.y, left.z);
        vertices.push(right.x, right.y, right.z);

        normals.push(0, 1, 0);
        normals.push(0, 1, 0);

        const vCoord = i / (sampledPoints.length - 1);
        uvs.push(0, vCoord * 10);
        uvs.push(1, vCoord * 10);

        if (i < sampledPoints.length - 1) {
          const base = i * 2;
          // Triangle 1: (base, base+1, base+2)
          indices.push(base, base + 1, base + 2);
          // Triangle 2: (base+1, base+3, base+2)
          indices.push(base + 1, base + 3, base + 2);
        }
      }

      const ribbonGeo = new THREE.BufferGeometry();
      ribbonGeo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      ribbonGeo.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
      ribbonGeo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      ribbonGeo.setIndex(indices);
      ribbonGeo.computeVertexNormals();

      // 4. Tactical Asphalt/Gravel Material
      const roadMat = new THREE.MeshStandardMaterial({
        color: 0x272a30,
        roughness: 0.9,
        metalness: 0.1,
        side: THREE.DoubleSide,
      });

      const roadMesh = new THREE.Mesh(ribbonGeo, roadMat);
      roadMesh.receiveShadow = true;
      roadMesh.userData = { type: 'road', data: road };
      this.group.add(roadMesh);

      // 5. Add Road Centerline Ribbon
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x94a3b8,
        linewidth: 1,
        transparent: true,
        opacity: 0.6
      });
      const centerPoints = sampledPoints.map(p => new THREE.Vector3(p.x, p.y + 0.04, p.z));
      const lineGeo = new THREE.BufferGeometry().setFromPoints(centerPoints);
      const centerLine = new THREE.Line(lineGeo, lineMat);
      this.group.add(centerLine);
    });
  }

  dispose() {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      this.group.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
    }
  }
}
