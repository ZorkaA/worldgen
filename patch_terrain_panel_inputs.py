import re

with open("frontend/src/components/terrain_panel.js", "r") as f:
    content = f.read()

# 1. Change <output> to <input type="number" class="input-text" style="width: 60px; text-align: right; padding: 2px;">
content = re.sub(
    r'<output id="([^"]+)">([^<]*)</output>',
    r'<input type="text" id="\1" class="input-text" value="\2" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />',
    content
)

# 2. In attachEventListeners, bindSlider needs to bind BOTH ways.
new_bind = """
    // Sliders with synchronized inputs
    const bindSlider = (id, outId, key, formatter = (v) => v, parser = (v) => parseFloat(v)) => {
      const slider = this.container.querySelector(id);
      const out = this.container.querySelector(outId);
      if (!slider || !out) return;
      
      // Update config and text input when slider moves
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        this.config[key] = val;
        out.value = formatter(val);
      });
      
      // Update config and slider when text input changes
      out.addEventListener('change', (e) => {
        let textVal = e.target.value.replace(/[^0-9.-]/g, ''); // strip non-numeric
        if (!textVal) return;
        const val = parser(textVal);
        this.config[key] = val;
        // Optionally update slider (it will clamp visually to its limits, which is fine)
        slider.value = val;
        out.value = formatter(val);
      });
    };
"""

content = re.sub(
    r'    // Sliders with synchronized outputs\s+const bindSlider = [^}]+};\s*};',
    new_bind.strip(),
    content,
    flags=re.MULTILINE
)

# Also disable roads by default
content = content.replace("generate_roads: true,", "generate_roads: false,")
content = content.replace('<input type="checkbox" id="terrain-generate-roads" checked class="modern-checkbox">', '<input type="checkbox" id="terrain-generate-roads" class="modern-checkbox">')

with open("frontend/src/components/terrain_panel.js", "w") as f:
    f.write(content)
print("Patched terrain_panel.js")
