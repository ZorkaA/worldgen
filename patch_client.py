with open("frontend/src/api/client.js", "r") as f:
    content = f.read()
content = content.replace("manifest: this.activeManifest", "zones: this.activeManifest ? this.activeManifest.zones : []")
with open("frontend/src/api/client.js", "w") as f:
    f.write(content)
