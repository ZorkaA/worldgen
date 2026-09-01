/**
 * Terrain Configuration Panel Component
 * Renders modern accessible form controls with synchronized <output> elements
 * and biome presets for multifractal Perlin & hydraulic erosion parameters.
 */
export class TerrainPanel {
  constructor(containerElement, onGenerateCallback) {
    this.container = containerElement;
    this.onGenerate = onGenerateCallback;

    // Current State
    this.config = {
      seed: 42,
      resolution: 129,
      scale: 256.0,
      octaves: 6,
      persistence: 0.5,
      lacunarity: 2.0,
      domain_warp_strength: 35.0,
      erosion_droplets: 50000,
      height_scale: 120.0,
    };

    this.render();
  }

  render() {
    this.container.innerHTML = `
      <!-- Quick Biome Presets -->
      <div class="config-section">
        <div class="section-title">
          <span>Biome Presets</span>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3 7h7l-5.5 4.5 2 7.5-6.5-5-6.5 5 2-7.5L1 9h7z"/></svg>
        </div>
        <div class="preset-grid">
          <button type="button" class="btn-preset active" data-preset="balanced">Highlands</button>
          <button type="button" class="btn-preset" data-preset="mountains">Alpine Ridge</button>
          <button type="button" class="btn-preset" data-preset="plains">Plains Outpost</button>
          <button type="button" class="btn-preset" data-preset="canyons">Desert Mesa</button>
        </div>
      </div>

      <!-- Core Generation Parameters -->
      <div class="config-section">
        <div class="section-title">
          <span>Terrain Synthesis</span>
        </div>

        <!-- Seed -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-seed">Seed</label>
            <output id="out-terrain-seed">${this.config.seed}</output>
          </div>
          <div style="display: flex; gap: 6px;">
            <input type="number" id="terrain-seed" class="input-text" value="${this.config.seed}" min="0" max="99999999" />
            <button type="button" class="btn-small" id="btn-random-seed" title="Randomize Seed">🎲 Random</button>
          </div>
        </div>

        <!-- Resolution -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-resolution">Mesh Resolution</label>
          </div>
          <select id="terrain-resolution" class="input-select">
            <option value="129" selected>129 x 129 (Fast Performance)</option>
            <option value="257">257 x 257 (Balanced Detail)</option>
            <option value="513">513 x 513 (High Fidelity)</option>
          </select>
        </div>

        <!-- Height Scale -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-height-scale">Height Scale (m)</label>
            <output id="out-height-scale">${this.config.height_scale}m</output>
          </div>
          <input type="range" id="terrain-height-scale" class="input-range" min="30" max="250" step="5" value="${this.config.height_scale}" />
        </div>

        <!-- Noise Scale -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-scale">Noise Scale</label>
            <output id="out-scale">${this.config.scale}</output>
          </div>
          <input type="range" id="terrain-scale" class="input-range" min="64" max="600" step="8" value="${this.config.scale}" />
        </div>

        <!-- Octaves -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-octaves">Octaves</label>
            <output id="out-octaves">${this.config.octaves}</output>
          </div>
          <input type="range" id="terrain-octaves" class="input-range" min="1" max="10" step="1" value="${this.config.octaves}" />
        </div>

        <!-- Persistence -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-persistence">Persistence (Roughness)</label>
            <output id="out-persistence">${this.config.persistence.toFixed(2)}</output>
          </div>
          <input type="range" id="terrain-persistence" class="input-range" min="0.1" max="0.9" step="0.05" value="${this.config.persistence}" />
        </div>

        <!-- Lacunarity -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-lacunarity">Lacunarity (Frequency Multiplier)</label>
            <output id="out-lacunarity">${this.config.lacunarity.toFixed(1)}</output>
          </div>
          <input type="range" id="terrain-lacunarity" class="input-range" min="1.2" max="3.5" step="0.1" value="${this.config.lacunarity}" />
        </div>

        <!-- Domain Warp Strength -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-warp">Domain Warp Strength</label>
            <output id="out-warp">${this.config.domain_warp_strength}</output>
          </div>
          <input type="range" id="terrain-warp" class="input-range" min="0" max="120" step="5" value="${this.config.domain_warp_strength}" />
        </div>

        <!-- Hydraulic Erosion Droplets -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-erosion">Hydraulic Erosion Droplets</label>
            <output id="out-erosion">${(this.config.erosion_droplets / 1000).toFixed(0)}k</output>
          </div>
          <input type="range" id="terrain-erosion" class="input-range" min="0" max="150000" step="5000" value="${this.config.erosion_droplets}" />
        </div>
      </div>

      <!-- Action Button -->
      <div style="margin-top: 4px;">
        <button type="button" class="btn-primary" id="btn-panel-generate" style="width: 100%; justify-content: center;">
          <svg class="spin-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/></svg>
          <span id="btn-panel-generate-label">Synthesize Terrain</span>
        </button>
      </div>
    `;

    this.attachEventListeners();
  }

  attachEventListeners() {
    // Seed Controls
    const inputSeed = this.container.querySelector('#terrain-seed');
    const outSeed = this.container.querySelector('#out-terrain-seed');
    const btnRandom = this.container.querySelector('#btn-random-seed');

    inputSeed.addEventListener('input', (e) => {
      this.config.seed = parseInt(e.target.value, 10) || 0;
      outSeed.value = this.config.seed;
    });

    btnRandom.addEventListener('click', () => {
      const randSeed = Math.floor(Math.random() * 900000 + 100000);
      this.config.seed = randSeed;
      inputSeed.value = randSeed;
      outSeed.value = randSeed;
    });

    // Resolution
    const selectRes = this.container.querySelector('#terrain-resolution');
    selectRes.addEventListener('change', (e) => {
      this.config.resolution = parseInt(e.target.value, 10);
    });

    // Sliders with synchronized outputs
    const bindSlider = (id, outId, key, formatter = (v) => v) => {
      const slider = this.container.querySelector(id);
      const out = this.container.querySelector(outId);
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        this.config[key] = val;
        out.value = formatter(val);
      });
    };

    bindSlider('#terrain-height-scale', '#out-height-scale', 'height_scale', (v) => `${v}m`);
    bindSlider('#terrain-scale', '#out-scale', 'scale');
    bindSlider('#terrain-octaves', '#out-octaves', 'octaves');
    bindSlider('#terrain-persistence', '#out-persistence', 'persistence', (v) => v.toFixed(2));
    bindSlider('#terrain-lacunarity', '#out-lacunarity', 'lacunarity', (v) => v.toFixed(1));
    bindSlider('#terrain-warp', '#out-warp', 'domain_warp_strength');
    bindSlider('#terrain-erosion', '#out-erosion', 'erosion_droplets', (v) => `${(v / 1000).toFixed(0)}k`);

    // Presets
    const presetButtons = this.container.querySelectorAll('.btn-preset');
    presetButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        presetButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.applyPreset(btn.dataset.preset);
      });
    });

    // Generate Trigger
    const btnGen = this.container.querySelector('#btn-panel-generate');
    btnGen.addEventListener('click', () => {
      if (this.onGenerate) {
        this.onGenerate(this.getConfig());
      }
    });
  }

  applyPreset(presetName) {
    if (presetName === 'balanced') {
      this.config.scale = 256;
      this.config.octaves = 6;
      this.config.persistence = 0.5;
      this.config.lacunarity = 2.0;
      this.config.domain_warp_strength = 35;
      this.config.erosion_droplets = 50000;
      this.config.height_scale = 120;
    } else if (presetName === 'mountains') {
      this.config.scale = 220;
      this.config.octaves = 7;
      this.config.persistence = 0.55;
      this.config.lacunarity = 2.2;
      this.config.domain_warp_strength = 65;
      this.config.erosion_droplets = 80000;
      this.config.height_scale = 180;
    } else if (presetName === 'plains') {
      this.config.scale = 400;
      this.config.octaves = 4;
      this.config.persistence = 0.35;
      this.config.lacunarity = 1.8;
      this.config.domain_warp_strength = 15;
      this.config.erosion_droplets = 20000;
      this.config.height_scale = 65;
    } else if (presetName === 'canyons') {
      this.config.scale = 180;
      this.config.octaves = 6;
      this.config.persistence = 0.6;
      this.config.lacunarity = 2.6;
      this.config.domain_warp_strength = 80;
      this.config.erosion_droplets = 60000;
      this.config.height_scale = 150;
    }

    // Refresh UI inputs
    this.container.querySelector('#terrain-scale').value = this.config.scale;
    this.container.querySelector('#out-scale').value = this.config.scale;
    this.container.querySelector('#terrain-octaves').value = this.config.octaves;
    this.container.querySelector('#out-octaves').value = this.config.octaves;
    this.container.querySelector('#terrain-persistence').value = this.config.persistence;
    this.container.querySelector('#out-persistence').value = this.config.persistence.toFixed(2);
    this.container.querySelector('#terrain-lacunarity').value = this.config.lacunarity;
    this.container.querySelector('#out-lacunarity').value = this.config.lacunarity.toFixed(1);
    this.container.querySelector('#terrain-warp').value = this.config.domain_warp_strength;
    this.container.querySelector('#out-warp').value = this.config.domain_warp_strength;
    this.container.querySelector('#terrain-erosion').value = this.config.erosion_droplets;
    this.container.querySelector('#out-erosion').value = `${(this.config.erosion_droplets / 1000).toFixed(0)}k`;
    this.container.querySelector('#terrain-height-scale').value = this.config.height_scale;
    this.container.querySelector('#out-height-scale').value = `${this.config.height_scale}m`;
  }

  setLoading(isLoading) {
    const btn = this.container.querySelector('#btn-panel-generate');
    const label = this.container.querySelector('#btn-panel-generate-label');
    if (btn && label) {
      if (isLoading) {
        btn.classList.add('is-loading');
        btn.disabled = true;
        label.textContent = 'Generating...';
      } else {
        btn.classList.remove('is-loading');
        btn.disabled = false;
        label.textContent = 'Synthesize Terrain';
      }
    }
  }

  getConfig() {
    return { ...this.config };
  }
}
