/**
 * Zone Configuration Panel Component
 * Controls Poisson-disc distribution, military faction themes (A/B/C),
 * destruction levels (01-04), density selectors, and interactive zone list with camera focus.
 */
export class ZonePanel {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.onGenerate = options.onGenerate || null;
    this.onFocusZone = options.onFocusZone || null;

    this.config = {
      zone_count_target: 5,
      min_zone_distance: 120.0,
      default_factions: ['A', 'B', 'C'],
      max_destruction: 4,
      min_radius: 40.0,
      max_radius: 80.0,
      density: 'medium',
    };

    this.activeZones = [];

    this.render();
  }

  render() {
    this.container.innerHTML = `
      <!-- Zone Generation Config -->
      <div class="config-section">
        <div class="section-title">
          <span>Poisson-Disc Zone Layout</span>
        </div>

        <!-- Zone Count -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-count">Target Zone Count</label>
            <output id="out-zone-count">${this.config.zone_count_target}</output>
          </div>
          <input type="range" id="zone-count" class="input-range" min="2" max="15" step="1" value="${this.config.zone_count_target}" />
        </div>

        <!-- Min Distance -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-min-dist">Min Zone Spacing</label>
            <output id="out-zone-min-dist">${this.config.min_zone_distance}m</output>
          </div>
          <input type="range" id="zone-min-dist" class="input-range" min="50" max="300" step="10" value="${this.config.min_zone_distance}" />
        </div>

        <!-- Factions Assignment -->
        <div class="form-group">
          <div class="label-row">
            <label>Active Factions</label>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 4px;">
            <label class="filter-chip active" style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
              <input type="checkbox" id="chk-faction-a" value="A" checked style="accent-color: var(--faction-a);" />
              <span>Faction A (Blue/Olive)</span>
            </label>
            <label class="filter-chip active" style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
              <input type="checkbox" id="chk-faction-b" value="B" checked style="accent-color: var(--faction-b);" />
              <span>Faction B (Gold/Red)</span>
            </label>
            <label class="filter-chip active" style="display: flex; align-items: center; gap: 4px; cursor: pointer;">
              <input type="checkbox" id="chk-faction-c" value="C" checked style="accent-color: var(--faction-c);" />
              <span>Faction C (Slate/Cyan)</span>
            </label>
          </div>
        </div>

        <!-- Destruction Range -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-max-damage">Max Destruction Level</label>
            <output id="out-zone-max-damage">Level 04 (Scorched)</output>
          </div>
          <select id="zone-max-damage" class="input-select">
            <option value="1">01 — Pristine Condition</option>
            <option value="2">02 — Light Battle Damage</option>
            <option value="3">03 — Heavy Structural Damage</option>
            <option value="4" selected>04 — Scorched & Ruined</option>
          </select>
        </div>

        <!-- Building Density -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-density">Building Density</label>
          </div>
          <select id="zone-density" class="input-select">
            <option value="low">Low (Sparse Outposts)</option>
            <option value="medium" selected>Medium (Standard Base)</option>
            <option value="high">High (Fortified Complex)</option>
          </select>
        </div>
      </div>

      <!-- Active Zones Inspector List -->
      <div class="config-section">
        <div class="section-title">
          <span>Active Military Zones</span>
          <span id="zone-count-badge" style="font-size: 10px; color: var(--text-muted);">0 Zones</span>
        </div>
        <div id="active-zones-list" style="display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; scrollbar-gutter: stable; overscroll-behavior: contain;">
          <p style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 12px 0;">No active zones loaded.</p>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  attachEventListeners() {
    // Range Sliders
    const sliderCount = this.container.querySelector('#zone-count');
    const outCount = this.container.querySelector('#out-zone-count');
    sliderCount.addEventListener('input', (e) => {
      this.config.zone_count_target = parseInt(e.target.value, 10);
      outCount.value = this.config.zone_count_target;
    });

    const sliderMinDist = this.container.querySelector('#zone-min-dist');
    const outMinDist = this.container.querySelector('#out-zone-min-dist');
    sliderMinDist.addEventListener('input', (e) => {
      this.config.min_zone_distance = parseFloat(e.target.value);
      outMinDist.value = `${this.config.min_zone_distance}m`;
    });

    // Faction checkboxes
    const chkA = this.container.querySelector('#chk-faction-a');
    const chkB = this.container.querySelector('#chk-faction-b');
    const chkC = this.container.querySelector('#chk-faction-c');

    const updateFactions = () => {
      const active = [];
      if (chkA.checked) active.push('A');
      if (chkB.checked) active.push('B');
      if (chkC.checked) active.push('C');
      this.config.default_factions = active.length > 0 ? active : ['A'];
    };

    chkA.addEventListener('change', updateFactions);
    chkB.addEventListener('change', updateFactions);
    chkC.addEventListener('change', updateFactions);

    // Destruction
    const selectDamage = this.container.querySelector('#zone-max-damage');
    selectDamage.addEventListener('change', (e) => {
      this.config.max_destruction = parseInt(e.target.value, 10);
    });

    // Density
    const selectDensity = this.container.querySelector('#zone-density');
    selectDensity.addEventListener('change', (e) => {
      this.config.density = e.target.value;
    });
  }

  /**
   * Update active zone list display when a manifest is loaded
   */
  updateZonesList(zones, buildings = []) {
    this.activeZones = zones || [];
    const listContainer = this.container.querySelector('#active-zones-list');
    const countBadge = this.container.querySelector('#zone-count-badge');

    if (!listContainer) return;

    countBadge.textContent = `${this.activeZones.length} Zones`;

    if (this.activeZones.length === 0) {
      listContainer.innerHTML = `<p style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 12px 0;">No active zones loaded.</p>`;
      return;
    }

    // Count buildings per zone
    const bldCountMap = {};
    for (let b of buildings) {
      bldCountMap[b.zone_id] = (bldCountMap[b.zone_id] || 0) + 1;
    }

    listContainer.innerHTML = this.activeZones.map((z, idx) => {
      const faction = (z.faction || 'A').toUpperCase();
      const factionClass = `faction-${faction.toLowerCase()}`;
      const destruction = String(z.destruction || '01');
      const bldCount = bldCountMap[z.id] || (z.building_ids ? z.building_ids.length : 0);

      return `
        <div class="zone-card" data-zone-id="${z.id}" data-zone-index="${idx}">
          <div class="zone-card-header">
            <span class="zone-name">${z.name || `Zone ${idx + 1}`}</span>
            <span class="zone-faction-badge ${factionClass}">Faction ${faction}</span>
          </div>
          <div class="zone-card-meta">
            <span>Damage: <strong>${destruction}</strong> | Radius: <strong>${z.radius || 60}m</strong></span>
            <span><strong>${bldCount}</strong> Buildings</span>
          </div>
          <div style="display: flex; justify-content: flex-end; margin-top: 2px;">
            <button type="button" class="btn-small btn-focus-zone" data-zone-index="${idx}">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><line x1="12" y1="1" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="1" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="23" y2="12"/></svg>
              <span>Focus 3D View</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Attach Focus Button Listeners
    const focusButtons = listContainer.querySelectorAll('.btn-focus-zone');
    focusButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(btn.dataset.zoneIndex, 10);
        const targetZone = this.activeZones[idx];
        if (targetZone && this.onFocusZone) {
          this.onFocusZone(targetZone);
        }
      });
    });
  }

  getConfig() {
    return { ...this.config };
  }
}
