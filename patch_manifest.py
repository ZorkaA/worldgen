import re

with open("frontend/src/components/manifest_panel.js", "r") as f:
    content = f.read()

html_insert = """
      <!-- Export Options Hierarchy -->
      <div class="config-section">
        <div class="section-title">
          <span>Export Options</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 4px; background: rgba(255,255,255,0.02); border-radius: 4px;">
            <span>Terrain Heightmap</span>
            <input type="checkbox" id="export-inc-terrain" checked class="modern-checkbox">
          </label>
          <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 4px; background: rgba(255,255,255,0.02); border-radius: 4px;">
            <span>Zone Footprints</span>
            <input type="checkbox" id="export-inc-zones" checked class="modern-checkbox">
          </label>
          <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 4px; background: rgba(255,255,255,0.02); border-radius: 4px;">
            <span>Building Assets</span>
            <input type="checkbox" id="export-inc-buildings" checked class="modern-checkbox">
          </label>
          <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 4px; background: rgba(255,255,255,0.02); border-radius: 4px;">
            <span>Road Network</span>
            <input type="checkbox" id="export-inc-roads" checked class="modern-checkbox">
          </label>
        </div>
      </div>
"""

content = content.replace("<!-- Export Actions -->", html_insert + "\n      <!-- Export Actions -->")

# Update getFilteredManifest method to use these toggles
js_insert = """
  getFilteredManifest() {
    if (!this.manifest) return null;
    
    const incTerrain = this.container.querySelector('#export-inc-terrain')?.checked ?? true;
    const incZones = this.container.querySelector('#export-inc-zones')?.checked ?? true;
    const incBld = this.container.querySelector('#export-inc-buildings')?.checked ?? true;
    const incRoads = this.container.querySelector('#export-inc-roads')?.checked ?? true;
    
    // Deep clone basic structure
    const out = {
      $schema: this.manifest.$schema,
      metadata: { ...this.manifest.metadata }
    };
    
    if (incTerrain) {
      out.terrain = this.manifest.terrain;
    }
    if (incZones) {
      out.zones = this.manifest.zones;
    }
    if (incBld) {
      out.buildings = this.manifest.buildings;
    }
    if (incRoads) {
      out.roads = this.manifest.roads;
    }
    return out;
  }
"""

content = content.replace("downloadManifestFile() {", js_insert + "\n  downloadManifestFile() {")
content = content.replace("const jsonStr = JSON.stringify(this.manifest, null, 2);", "const filtered = this.getFilteredManifest();\n    const jsonStr = JSON.stringify(filtered, null, 2);")

with open("frontend/src/components/manifest_panel.js", "w") as f:
    f.write(content)
print("Patched manifest_panel.js")
