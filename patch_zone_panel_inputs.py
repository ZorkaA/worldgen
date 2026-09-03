import re

with open("frontend/src/components/zone_panel.js", "r") as f:
    content = f.read()

# 1. Change <output> to <input type="text">
content = re.sub(
    r'<output id="([^"]+)">([^<]*)</output>',
    r'<input type="text" id="\1" class="input-text" value="\2" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />',
    content
)

# 2. Add two-way binding manually for each slider in zone_panel.js
# - sliderCount & outCount
# - sliderMinDist & outMinDist
# - sliderDensity & outDensity
# - newRadiusSlider & outNewRadius
# - newDensitySlider & outNewDensity

# We just inject a simple block of code to handle change events on inputs
js_insert = """
    // Bind editable text boxes back to the sliders
    const bindSync = (outElem, sliderElem, updateCb) => {
      if (!outElem || !sliderElem) return;
      outElem.addEventListener('change', (e) => {
        let textVal = e.target.value.replace(/[^0-9.-]/g, '');
        if (!textVal) return;
        const val = parseFloat(textVal);
        sliderElem.value = val;
        updateCb(val, e.target);
      });
    };

    bindSync(outCount, sliderCount, (val, out) => {
      this.config.zone_count_target = val;
      out.value = val;
    });
    bindSync(outMinDist, sliderMinDist, (val, out) => {
      this.config.min_zone_distance = val;
      out.value = `${val}m`;
    });
    bindSync(outDensity, sliderDensity, (val, out) => {
      this.config.density = val;
      out.value = this.getDensityBadgeText(val);
    });
    bindSync(outNewRadius, newRadiusSlider, (val, out) => {
      out.value = `${val}m`;
    });
    bindSync(outNewDensity, newDensitySlider, (val, out) => {
      out.value = this.getDensityBadgeText(val);
    });
"""

# Insert right after: newDensitySlider.addEventListener('input', (e) => { ... });
content = re.sub(
    r'(newDensitySlider\.addEventListener\([^}]+\}\);)',
    r'\1\n' + js_insert,
    content
)

with open("frontend/src/components/zone_panel.js", "w") as f:
    f.write(content)
print("Patched zone_panel.js inputs")
