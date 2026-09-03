import re

with open("frontend/src/api/client.js", "r") as f:
    content = f.read()

replacement = """          body: JSON.stringify({
            zone_id: zoneId,
            new_position: [newPos.x, newPos.y, newPos.z],
            ...currentConfig,
            zones: this.activeManifest ? this.activeManifest.zones : []
          }),"""

content = content.replace("""          body: JSON.stringify({
            zone_id: zoneId,
            new_position: [newPos.x, newPos.y, newPos.z],
            config: currentConfig,
            zones: this.activeManifest ? this.activeManifest.zones : []
          }),""", replacement)

with open("frontend/src/api/client.js", "w") as f:
    f.write(content)
print("Patched client.js")
