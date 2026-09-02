/**
 * Terrain Configuration Panel Component
 * Renders modern accessible form controls with synchronized <output> elements,
 * container queries, stable scrollbars, and utilitarian military engineering controls:
 * - Map Dimensions (km, 0.5 - 4.0 km)
 * - Grid Resolution (snap points: 65, 129, 257, 513, 1025)
 * - Platform Deformation Strength (0.0 - 1.0)
 * - Boundary Edge Margin Offset (25 - 400m)
 * - Max Road Incline Grade (5% - 45%)
 * - Multifractal Perlin & Hydraulic Erosion Parameters
 */
export class TerrainPanel {
  constructor(containerElement, onGenerateCallback) {
    this.container = containerElement;
    this.onGenerate = onGenerateCallback;

    // Current V2 State
    this.config = {
      seed: 42,
      map_width_km: 1.0,
      map_length_km: 1.0,
      resolution: 129,
      deformation_strength: 0.85,
      edge_margin: 150.0,
      max_road_slope: 0.25,
      height_scale: 120.0,
      scale: 256.0,
      octaves: 6,
      persistence: 0.5,
      lacunarity: 2.0,
      domain_warp_strength: 35.0,
      erosion_droplets: 50000,
    };

    this.render();
  }

  render() {
    this.container.innerHTML = `
      <!-- Quick Biome Presets -->
      <div class="config-section">
        <div class="section-title">
          <span>Terrain Presets</span>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3 7h7l-5.5 4.5 2 7.5-6.5-5-6.5 5 2-7.5L1 9h7z"/></svg>
        </div>
        <div class="preset-grid">
          <button type="button" class="btn-preset active" data-preset="balanced">Highlands</button>
          <button type="button" class="btn-preset" data-preset="mountains">Alpine Ridge</button>
          <button type="button" class="btn-preset" data-preset="plains">Plains Sector</button>
          <button type="button" class="btn-preset" data-preset="canyons">Desert Plateau</button>
        </div>
      </div>

      <!-- Global Map Dimension & Resolution Parameters (R1) -->
      <div class="config-section">
        <div class="section-title">
          <span>Global Map Dimensions</span>
        </div>

        <!-- Map Width (km) -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-width-km">Map Width (km)</label>
            <output id="out-width-km">${this.config.map_width_km.toFixed(2)} km</output>
          </div>
          <input type="range" id="terrain-width-km" class="input-range" min="0.5" max="4.0" step="0.25" value="${this.config.map_width_km}" />
        </div>

        <!-- Map Length (km) -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-length-km">Map Length (km)</label>
            <output id="out-length-km">${this.config.map_length_km.toFixed(2)} km</output>
          </div>
          <input type="range" id="terrain-length-km" class="input-range" min="0.5" max="4.0" step="0.25" value="${this.config.map_length_km}" />
        </div>

        <!-- Resolution Snap Points -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-resolution">Grid Granularity / Resolution</label>
          </div>
          <select id="terrain-resolution" class="input-select">
            <option value="65">65 x 65 (Draft / Realtime)</option>
            <option value="129" selected>129 x 129 (Standard / Fast)</option>
            <option value="257">257 x 257 (Balanced Detail)</option>
            <option value="513">513 x 513 (High Fidelity)</option>
            <option value="1025">1025 x 1025 (Ultra Precision)</option>
          </select>
        </div>

        <!-- Terrain Deformation Strength -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-deformation">Deformation Strength</label>
            <output id="out-deformation">${Math.round(this.config.deformation_strength * 100)}%</output>
          </div>
          <input type="range" id="terrain-deformation" class="input-range" min="0.0" max="1.0" step="0.05" value="${this.config.deformation_strength}" />
        </div>

        <!-- Edge Margin Offset -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-edge-margin">Edge Margin Offset</label>
            <output id="out-edge-margin">${this.config.edge_margin}m</output>
          </div>
          <input type="range" id="terrain-edge-margin" class="input-range" min="25" max="400" step="25" value="${this.config.edge_margin}" />
        </div>

        <!-- Max Road Incline Grade -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-road-slope">Max Road Incline Grade</label>
            <output id="out-road-slope">${Math.round(this.config.max_road_slope * 100)}%</output>
          </div>
          <input type="range" id="terrain-road-slope" class="input-range" min="0.05" max="0.45" step="0.05" value="${this.config.max_road_slope}" />
        </div>
      </div>

      <!-- Procedural Heightmap Parameters -->
      <div class="config-section">
        <div class="section-title">
          <span>Terrain Parameters</span>
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

        <!-- Height Scale -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-height-scale">Height Scale (m)</label>
            <output id="out-height-scale">${this.config.height_scale}m</output>
          </div>
          <input type="range" id="terrain-height-scale" class="input-range" min="30" max="250" step="5" value="${this.config.height_scale}" />
        </div>

        <!-- Perlin Noise Scale -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-scale">Perlin Noise Scale</label>
            <output id="out-scale">${this.config.scale}</output>
          </div>
          <input type="range" id="terrain-scale" class="input-range" min="64" max="600" step="8" value="${this.config.scale}" />
        </div>

        <!-- Fractal Octaves -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-octaves">Fractal Octaves</label>
            <output id="out-octaves">${this.config.octaves}</output>
          </div>
          <input type="range" id="terrain-octaves" class="input-range" min="1" max="10" step="1" value="${this.config.octaves}" />
        </div>

        <!-- Fractal Persistence -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-persistence">Fractal Persistence</label>
            <output id="out-persistence">${this.config.persistence.toFixed(2)}</output>
          </div>
          <input type="range" id="terrain-persistence" class="input-range" min="0.1" max="0.9" step="0.05" value="${this.config.persistence}" />
        </div>

        <!-- Fractal Lacunarity -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-lacunarity">Fractal Lacunarity</label>
            <output id="out-lacunarity">${this.config.lacunarity.toFixed(1)}</output>
          </div>
          <input type="range" id="terrain-lacunarity" class="input-range" min="1.2" max="3.5" step="0.1" value="${this.config.lacunarity}" />
        </div>

        <!-- Domain Warp Perturbation -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-warp">Domain Warp Perturbation</label>
            <output id="out-warp">${this.config.domain_warp_strength}</output>
          </div>
          <input type="range" id="terrain-warp" class="input-range" min="0" max="120" step="5" value="${this.config.domain_warp_strength}" />
        </div>

        <!-- Erosion Particle Count -->
        <div class="form-group">
          <div class="label-row">
            <label for="terrain-erosion">Erosion Particle Count</label>
            <output id="out-erosion">${(this.config.erosion_droplets / 1000).toFixed(0)}k</output>
          </div>
          <input type="range" id="terrain-erosion" class="input-range" min="0" max="150000" step="5000" value="${this.config.erosion_droplets}" />
        </div>
      </div>

      <!-- Action Button -->
      <div style="margin-top: 4px;">
        <button type="button" class="btn-primary" id="btn-panel-generate" style="width: 100%; justify-content: center;">
          <svg class="spin-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/></svg>
          <span id="btn-panel-generate-label">Generate Terrain</span>
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
      if (!slider || !out) return;
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        this.config[key] = val;
        out.value = formatter(val);
      });
    };

    // V2 Global Parameters
    bindSlider('#terrain-width-km', '#out-width-km', 'map_width_km', (v) => `${v.toFixed(2)} km`);
    bindSlider('#terrain-length-km', '#out-length-km', 'map_length_km', (v) => `${v.toFixed(2)} km`);
    bindSlider('#terrain-deformation', '#out-deformation', 'deformation_strength', (v) => `${Math.round(v * 100)}%`);
    bindSlider('#terrain-edge-margin', '#out-edge-margin', 'edge_margin', (v) => `${v}m`);
    bindSlider('#terrain-road-slope', '#out-road-slope', 'max_road_slope', (v) => `${Math.round(v * 100)}%`);

    // Standard Parameters
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
      this.config.deformation_strength = 0.85;
    } else if (presetName === 'mountains') {
      this.config.scale = 220;
      this.config.octaves = 7;
      this.config.persistence = 0.55;
      this.config.lacunarity = 2.2;
      this.config.domain_warp_strength = 65;
      this.config.erosion_droplets = 80000;
      this.config.height_scale = 180;
      this.config.deformation_strength = 0.90;
    } else if (presetName === 'plains') {
      this.config.scale = 400;
      this.config.octaves = 4;
      this.config.persistence = 0.35;
      this.config.lacunarity = 1.8;
      this.config.domain_warp_strength = 15;
      this.config.erosion_droplets = 20000;
      this.config.height_scale = 65;
      this.config.deformation_strength = 0.70;
    } else if (presetName === 'canyons') {
      this.config.scale = 180;
      this.config.octaves = 6;
      this.config.persistence = 0.6;
      this.config.lacunarity = 2.6;
      this.config.domain_warp_strength = 80;
      this.config.erosion_droplets = 60000;
      this.config.height_scale = 150;
      this.config.deformation_strength = 0.95;
    }

    // Refresh UI inputs
    const setElem = (id, outId, val, fmt = (v) => v) => {
      const el = this.container.querySelector(id);
      const out = this.container.querySelector(outId);
      if (el) el.value = val;
      if (out) out.value = fmt(val);
    };

    setElem('#terrain-scale', '#out-scale', this.config.scale);
    setElem('#terrain-octaves', '#out-octaves', this.config.octaves);
    setElem('#terrain-persistence', '#out-persistence', this.config.persistence, (v) => v.toFixed(2));
    setElem('#terrain-lacunarity', '#out-lacunarity', this.config.lacunarity, (v) => v.toFixed(1));
    setElem('#terrain-warp', '#out-warp', this.config.domain_warp_strength);
    setElem('#terrain-erosion', '#out-erosion', this.config.erosion_droplets, (v) => `${(v / 1000).toFixed(0)}k`);
    setElem('#terrain-height-scale', '#out-height-scale', this.config.height_scale, (v) => `${v}m`);
    setElem('#terrain-deformation', '#out-deformation', this.config.deformation_strength, (v) => `${Math.round(v * 100)}%`);
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
        label.textContent = 'Generate Terrain';
      }
    }
  }

  getConfig() {
    return {
      ...this.config,
      world_size: [
        this.config.map_width_km * 1000.0,
        this.config.height_scale,
        this.config.map_length_km * 1000.0
      ]
    };
  }
}

