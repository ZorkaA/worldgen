import * as THREE from 'three';

/**
 * Tactical Zone Boundary & Footprint Visualizer
 * Color-coded by faction (A: Blue/Olive, B: Gold/Crimson, C: Slate/Cyan)
 * with destruction level styling, elevated above terrain to prevent z-fighting.
 */
export class ZoneVisualizer {
  constructor(scene, terrainVisualizer) {
    this.scene = scene;
    this.terrain = terrainVisualizer;
    this.group = new THREE.Group();
    this.group.name = 'ZonesGroup';
    this.scene.add(this.group);
    this.zonesData = [];
    this.beaconMeshes = [];

    // Faction Color Map
    this.factionColors = {
      'A': 0x2563eb, // Military Blue / Olive
      'B': 0xd97706, // Desert Gold / Crimson
      'C': 0x06b6d4, // Urban Slate / Cyan
    };
  }

  update(zones) {
    this.dispose();
    if (!zones || !Array.isArray(zones)) return;

    this.zonesData = zones;

    zones.forEach((zone) => {
      const faction = (zone.faction || 'A').toUpperCase();
      const baseColorHex = this.factionColors[faction] || 0x22c55e;
      const color = new THREE.Color(baseColorHex);
      const destruction = String(zone.destruction || '01');

      const [cx, cy, cz] = zone.center || [0, 0, 0];
      const radius = zone.radius || 60;

      // 1. Build Footprint Boundary Loop conforming to terrain elevation
      const points = [];
      const numSegments = 64;

      if (zone.footprint_points && zone.footprint_points.length >= 3) {
        // Use exact polygon footprint if provided
        for (let pt of zone.footprint_points) {
          const px = pt[0];
          const pz = pt[1];
          const py = this.terrain.getElevationAt(px, pz) + 0.25; // 0.25m offset to eliminate z-fighting
          points.push(new THREE.Vector3(px, py, pz));
        }
        // Close the loop
        points.push(points[0].clone());
      } else {
        // Generate circular ring around center
        for (let i = 0; i <= numSegments; i++) {
          const angle = (i / numSegments) * Math.PI * 2;
          const px = cx + Math.cos(angle) * radius;
          const pz = cz + Math.sin(angle) * radius;
          const py = this.terrain.getElevationAt(px, pz) + 0.25;
          points.push(new THREE.Vector3(px, py, pz));
        }
      }

      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);

      // Line style based on destruction level
      let lineMat;
      if (destruction === '03' || destruction === '04') {
        lineMat = new THREE.LineDashedMaterial({
          color: destruction === '04' ? 0xef4444 : color,
          linewidth: 2,
          scale: 1,
          dashSize: 4,
          gapSize: 2,
        });
      } else {
        lineMat = new THREE.LineBasicMaterial({
          color: color,
          linewidth: 2,
        });
      }

      const boundaryLine = new THREE.Line(lineGeo, lineMat);
      if (destruction === '03' || destruction === '04') {
        boundaryLine.computeLineDistances();
      }
      boundaryLine.userData = { type: 'zone', data: zone };
      this.group.add(boundaryLine);

      // 2. Add Center Tactical Beacon Pin
      const terrainCenterY = this.terrain.getElevationAt(cx, cz);
      const beaconHeight = 24.0;

      // Vertical beam
      const beamGeo = new THREE.CylinderGeometry(0.4, 0.4, beaconHeight, 8);
      const beamMat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.55
      });
      const beamMesh = new THREE.Mesh(beamGeo, beamMat);
      beamMesh.position.set(cx, terrainCenterY + beaconHeight / 2, cz);
      beamMesh.userData = { type: 'zone', data: zone };
      this.group.add(beamMesh);

      // Beacon tip sphere
      const sphereGeo = new THREE.SphereGeometry(1.5, 12, 12);
      const sphereMat = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.8,
        roughness: 0.2,
      });
      const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
      sphereMesh.position.set(cx, terrainCenterY + beaconHeight, cz);
      sphereMesh.userData = { type: 'zone', data: zone };
      this.group.add(sphereMesh);
      this.beaconMeshes.push(sphereMesh);

      // Base footprint disc with subtle glow
      const discGeo = new THREE.RingGeometry(radius * 0.95, radius * 1.0, 48);
      discGeo.rotateX(-Math.PI / 2);
      const discMat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.25,
        side: THREE.DoubleSide
      });
      const discMesh = new THREE.Mesh(discGeo, discMat);
      discMesh.position.set(cx, terrainCenterY + 0.15, cz);
      discMesh.userData = { type: 'zone', data: zone };
      this.group.add(discMesh);
    });
  }

  animate(time) {
    // Subtle pulse on beacon spheres
    const pulse = 1.0 + Math.sin(time * 3.0) * 0.15;
    for (let beacon of this.beaconMeshes) {
      beacon.scale.set(pulse, pulse, pulse);
    }
  }

  dispose() {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      this.group.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
    }
    this.beaconMeshes = [];
    this.zonesData = [];
  }
}
