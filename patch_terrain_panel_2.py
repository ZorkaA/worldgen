import re

with open("frontend/src/components/terrain_panel.js", "r") as f:
    content = f.read()

# Let's insert the toggle before max_road_slope input.
html_insert = """
        <!-- Generate Road Network -->
        <div class="form-group">
          <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
            <span>Generate Road Network</span>
            <input type="checkbox" id="terrain-generate-roads" checked class="modern-checkbox">
          </label>
        </div>
"""

# Let's find a good place to insert it. "Max Road Incline" or "Map Dimensions"
# I'll just search for `id="terrain-road-slope"` and insert it before the div.
pattern = re.compile(r'(<div class="form-group">\s*<div class="label-row">\s*<label for="terrain-road-slope">)')
if pattern.search(content):
    content = pattern.sub(html_insert + r'\1', content)

# Now add the listener
js_insert = """
    // Road Toggle
    const chkRoads = this.container.querySelector('#terrain-generate-roads');
    if (chkRoads) {
      chkRoads.addEventListener('change', (e) => {
        this.config.generate_roads = e.target.checked;
      });
    }
"""
content = content.replace("bindSlider('#terrain-road-slope', '#out-road-slope', 'max_road_slope', (v) => `${Math.round(v * 100)}%`);", "bindSlider('#terrain-road-slope', '#out-road-slope', 'max_road_slope', (v) => `${Math.round(v * 100)}%`);\n" + js_insert)

with open("frontend/src/components/terrain_panel.js", "w") as f:
    f.write(content)
