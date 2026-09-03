import re

with open("frontend/src/components/hud.js", "r") as f:
    content = f.read()

replacement = """
    btnWireframe?.addEventListener('click', () => {
      btnWireframe.classList.toggle('active');
      if (this.viewer && this.viewer.terrain) {
        this.viewer.terrain.toggleWireframe();
      }
    });
    
    const btnZones = document.getElementById('btn-toggle-zones');
    btnZones?.addEventListener('click', () => {
      btnZones.classList.toggle('active');
      const isVisible = btnZones.classList.contains('active');
      if (this.viewer && this.viewer.zones && this.viewer.zones.group) {
        this.viewer.zones.group.visible = isVisible;
      }
    });

    const btnAssets = document.getElementById('btn-toggle-assets');
    btnAssets?.addEventListener('click', () => {
      btnAssets.classList.toggle('active');
      const isVisible = btnAssets.classList.contains('active');
      if (this.viewer && this.viewer.buildings && this.viewer.buildings.group) {
        this.viewer.buildings.group.visible = isVisible;
      }
    });
"""

content = content.replace("""
    btnWireframe?.addEventListener('click', () => {
      btnWireframe.classList.toggle('active');
      if (this.viewer && this.viewer.terrain) {
        this.viewer.terrain.toggleWireframe();
      }
    });""", replacement)

with open("frontend/src/components/hud.js", "w") as f:
    f.write(content)
print("Patched hud.js")
