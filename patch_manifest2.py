import re

with open("frontend/src/components/manifest_panel.js", "r") as f:
    content = f.read()

content = content.replace("const jsonStr = JSON.stringify(this.manifest, null, 2);", "const filtered = this.getFilteredManifest();\\n    const jsonStr = JSON.stringify(filtered, null, 2);")

with open("frontend/src/components/manifest_panel.js", "w") as f:
    f.write(content.replace("\\\\n", "\\n"))
print("Patched manifest_panel.js again")
