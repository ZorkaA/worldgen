with open("frontend/src/components/terrain_panel.js", "r") as f:
    content = f.read()

old_bind = """    const bindSlider = (id, outId, key, formatter = (v) => v) => {
      const slider = this.container.querySelector(id);
      const out = this.container.querySelector(outId);
      if (!slider || !out) return;
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        this.config[key] = val;
        out.value = formatter(val);
      });
    };"""

new_bind = """    const bindSlider = (id, outId, key, formatter = (v) => v, parser = (v) => parseFloat(v)) => {
      const slider = this.container.querySelector(id);
      const out = this.container.querySelector(outId);
      if (!slider || !out) return;
      
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        this.config[key] = val;
        out.value = formatter(val);
      });
      
      out.addEventListener('change', (e) => {
        let textVal = e.target.value.replace(/[^0-9.-]/g, '');
        if (!textVal) return;
        const val = parser(textVal);
        this.config[key] = val;
        slider.value = val;
        out.value = formatter(val);
      });
    };"""

content = content.replace(old_bind, new_bind)
with open("frontend/src/components/terrain_panel.js", "w") as f:
    f.write(content)
print("bindSlider patched")
