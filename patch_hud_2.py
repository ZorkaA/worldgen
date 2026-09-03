import re

with open("frontend/src/components/hud.js", "r") as f:
    content = f.read()

replacement = """    btnWireframe?.addEventListener('click', () => {
      if (this.viewer) {
        const isWire = this.viewer.toggleWireframe();
        btnWireframe.classList.toggle('active', isWire);
        this.showToast(isWire ? 'Wireframe Mode: ON' : 'Wireframe Mode: OFF');
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
    });"""

old = """    btnWireframe?.addEventListener('click', () => {
      if (this.viewer) {
        const isWire = this.viewer.toggleWireframe();
        btnWireframe.classList.toggle('active', isWire);
        this.showToast(isWire ? 'Wireframe Mode: ON' : 'Wireframe Mode: OFF');
      }
    });"""

content = content.replace(old, replacement)

with open("frontend/src/components/hud.js", "w") as f:
    f.write(content)
print("hud patched")
