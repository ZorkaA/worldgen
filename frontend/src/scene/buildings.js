import * as THREE from 'three';

/**
 * 3D Building Footprint & Bounding Box Visualizer
 * Renders CAD tactical wireframe outlines and semi-transparent solid proxies
 * positioned, rotated, and elevated to exact world coordinates.
 */
export class BuildingVisualizer {
  constructor(scene, terrainVisualizer) {
    this.scene = scene;
    this.terrain = terrainVisualizer;
    this.group = new THREE.Group();
    this.group.name = 'BuildingsGroup';
    this.scene.add(this.group);

    this.buildingMeshes = [];
    this.highlightBox = null;
    this.selectedBuilding = null;

    this.factionColors = {
      'A': 0x3b82f6, // Faction A Blue
      'B': 0xf59e0b, // Faction B Gold/Orange
      'C': 0x06b6d4, // Faction C Cyan
    };

    this.setupHighlightHelper();
  }

  setupHighlightHelper() {
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const edges = new THREE.EdgesGeometry(geo);
    const mat = new THREE.LineBasicMaterial({
      color: 0x4ade80,
      linewidth: 3,
      depthTest: false,
      transparent: true,
      opacity: 0.9,
    });
    this.highlightBox = new THREE.LineSegments(edges, mat);
    this.highlightBox.visible = false;
    this.highlightBox.renderOrder = 999;
    this.scene.add(this.highlightBox);
  }

  update(buildings) {
    this.dispose();
    if (!buildings || !Array.isArray(buildings)) return;

    buildings.forEach((bld) => {
      // 1. Extract Bounding Box Dimensions
      const bbox = bld.bounding_box || bld.bbox || {};
      const size = bbox.size || [6.0, 4.0, 8.0];
      const sx = Math.max(0.5, size[0]);
      const sy = Math.max(0.5, size[1]);
      const sz = Math.max(0.5, size[2]);

      const [px, py, pz] = bld.position || [0, 0, 0];
      const faction = (bld.faction || 'A').toUpperCase();
      const baseColor = this.factionColors[faction] || 0x38bdf8;
      const color = new THREE.Color(baseColor);

      // Adjust height: align base to terrain if needed
      const terrainY = this.terrain.getElevationAt(px, pz);
      const finalY = Math.max(terrainY, py);

      // 2. Create Box Geometry
      const boxGeo = new THREE.BoxGeometry(sx, sy, sz);

      // 3. Semi-transparent Solid Mesh
      const solidMat = new THREE.MeshStandardMaterial({
        color: color,
        transparent: true,
        opacity: 0.55,
        roughness: 0.4,
        metalness: 0.2,
      });
      const solidMesh = new THREE.Mesh(boxGeo, solidMat);
      solidMesh.castShadow = true;
      solidMesh.receiveShadow = true;

      // 4. Crisp CAD Tactical Wireframe Edges
      const edgesGeo = new THREE.EdgesGeometry(boxGeo);
      const edgeMat = new THREE.LineBasicMaterial({
        color: 0xffffff,
        linewidth: 1.5,
        transparent: true,
        opacity: 0.85,
      });
      const edgeLines = new THREE.LineSegments(edgesGeo, edgeMat);
      solidMesh.add(edgeLines);

      // 5. Position & Orientation
      // Center of box should sit on ground: offset Y by sy / 2
      solidMesh.position.set(px, finalY + sy / 2.0, pz);

      // Rotation handling (Euler array [rx, ry, rz] in degrees or radians, or quaternion)
      if (bld.rotation) {
        if (bld.rotation.length === 4) {
          // Quaternion [x, y, z, w]
          solidMesh.quaternion.set(
            bld.rotation[0],
            bld.rotation[1],
            bld.rotation[2],
            bld.rotation[3]
          );
        } else if (bld.rotation.length === 3) {
          // Euler angles [rx, ry, rz]
          // Usually yaw is rotation[1]
          const rx = THREE.MathUtils.degToRad(bld.rotation[0]);
          const ry = THREE.MathUtils.degToRad(bld.rotation[1]);
          const rz = THREE.MathUtils.degToRad(bld.rotation[2]);
          solidMesh.rotation.set(rx, ry, rz);
        }
      }

      if (bld.scale && bld.scale.length === 3) {
        solidMesh.scale.set(bld.scale[0], bld.scale[1], bld.scale[2]);
      }

      solidMesh.userData = {
        type: 'building',
        data: bld,
        dimensions: [sx, sy, sz]
      };

      this.group.add(solidMesh);
      this.buildingMeshes.push(solidMesh);
    });
  }

  /**
   * Highlight a specific building mesh (on hover or selection)
   */
  setHighlight(mesh) {
    if (!mesh) {
      if (this.highlightBox) this.highlightBox.visible = false;
      return;
    }

    const { dimensions } = mesh.userData;
    if (this.highlightBox && dimensions) {
      this.highlightBox.scale.set(dimensions[0] * 1.05, dimensions[1] * 1.05, dimensions[2] * 1.05);
      this.highlightBox.position.copy(mesh.position);
      this.highlightBox.rotation.copy(mesh.rotation);
      this.highlightBox.quaternion.copy(mesh.quaternion);
      this.highlightBox.visible = true;
    }
  }

  dispose() {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      this.group.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
      // Dispose edge children
      child.traverse((nested) => {
        if (nested !== child) {
          if (nested.geometry) nested.geometry.dispose();
          if (nested.material) nested.material.dispose();
        }
      });
    }
    this.buildingMeshes = [];
    if (this.highlightBox) this.highlightBox.visible = false;
  }
}
