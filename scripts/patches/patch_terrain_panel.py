import re

with open("frontend/src/components/terrain_panel.js", "r") as f:
    content = f.read()

content = content.replace("max_road_slope: 0.25,", "max_road_slope: 0.25,\n      generate_roads: true,")

html_insert = """
      <!-- Generate Roads Toggle -->
      <div class="form-group">
        <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
          <span>Generate Road Network</span>
          <input type="checkbox" id="t-gen-roads" checked class="modern-checkbox">
        </label>
      </div>

      <!-- Max Road Incline -->"""
content = content.replace("<!-- Max Road Incline -->", html_insert)

content = content.replace("max_road_slope: parseFloat(document.getElementById('t-slope').value),", "max_road_slope: parseFloat(document.getElementById('t-slope').value),\n      generate_roads: document.getElementById('t-gen-roads').checked,")

with open("frontend/src/components/terrain_panel.js", "w") as f:
    f.write(content)
