import re

with open("frontend/src/scene/viewer.js", "r") as f:
    content = f.read()

content = content.replace("new THREE.FogExp2(0x0a0f1d, 0.0004)", "new THREE.FogExp2(0x1a2133, 0.00015)")
content = content.replace("this.sunLight.shadow.camera.far = 3500;", "this.sunLight.shadow.camera.far = 6500;")
content = content.replace("this.sunLight.shadow.camera.left = -750;", "this.sunLight.shadow.camera.left = -2000;")
content = content.replace("this.sunLight.shadow.camera.right = 750;", "this.sunLight.shadow.camera.right = 2000;")
content = content.replace("this.sunLight.shadow.camera.top = 750;", "this.sunLight.shadow.camera.top = 2000;")
content = content.replace("this.sunLight.shadow.camera.bottom = -750;", "this.sunLight.shadow.camera.bottom = -2000;")
content = content.replace("this.camera = new THREE.PerspectiveCamera(55, aspect, 0.5, 6000);", "this.camera = new THREE.PerspectiveCamera(55, aspect, 0.5, 12000);")

with open("frontend/src/scene/viewer.js", "w") as f:
    f.write(content)
print("Patched viewer.js")
