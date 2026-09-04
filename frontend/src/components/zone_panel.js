/**
 * Zone Configuration & CRUD Panel Component
 * Features:
 * - Full Zone CRUD: + Add Zone creation modal/form, Delete Zone (🗑️) button, Inline Rename text field.
 * - Continuous Density Slider (0.05 - 1.00) with descriptive military tier badges.
 * - Layout Template Selector (military_base, airfield, outpost, radar_station, depot).
 * - Faction (A/B/C) & Destruction (01-04) customization per zone.
 * - Viewport Camera Focus synchronization.
 */
export class ZonePanel {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.onGenerate = options.onGenerate || null;
    this.onFocusZone = options.onFocusZone || null;
    this.onAddZone = options.onAddZone || null;
    this.onDeleteZone = options.onDeleteZone || null;
    this.onUpdateZone = options.onUpdateZone || null;
    this.onZonesChanged = options.onZonesChanged || null;

    this.config = {
      zone_count_target: 5,
      min_zone_distance: 120.0,
      default_factions: ['A', 'B', 'C'],
      max_destruction: 4,
      min_radius: 40.0,
      max_radius: 80.0,
      density: 0.55,
      default_template: 'military_base',
    };

    this.activeZones = [];
    this.activeBuildings = [];
    this.isAddingZone = false;

    // Available Templates
    this.templates = [
      { id: 'military_base', name: 'Fortified Military Base' },
      { id: 'airfield', name: 'Forward Airfield & Logistics' },
      { id: 'outpost', name: 'Tactical Outpost & Tower' },
      { id: 'radar_station', name: 'Radar & Comms Array' },
      { id: 'depot', name: 'Supply Depot & Motor Pool' },
      { id: 'city', name: 'High-Density City' }
    ];

    this.render();
  }

  getDensityBadgeText(val) {
    if (val <= 0.25) return `${val.toFixed(2)} (Sparse Outpost)`;
    if (val <= 0.55) return `${val.toFixed(2)} (Standard Base)`;
    if (val <= 0.80) return `${val.toFixed(2)} (Fortified Depot)`;
    return `${val.toFixed(2)} (Command Citadel)`;
  }

  render() {
    this.container.innerHTML = `
      <!-- Zone Generation Parameters -->
      <div class="config-section">
        <div class="section-title">
          <span>Zone Distribution Parameters</span>
        </div>

        <!-- Zone Count -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-count">Target Zone Count</label>
            <input type="text" id="out-zone-count" class="input-text" value="${this.config.zone_count_target}" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />
          </div>
          <input type="range" id="zone-count" class="input-range" min="1" max="15" step="1" value="${this.config.zone_count_target}" />
        </div>

        <!-- Min Distance -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-min-dist">Min Zone Spacing</label>
            <input type="text" id="out-zone-min-dist" class="input-text" value="${this.config.min_zone_distance}m" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />
          </div>
          <input type="range" id="zone-min-dist" class="input-range" min="50" max="300" step="10" value="${this.config.min_zone_distance}" />
        </div>

        <!-- Continuous Density Slider (R4) -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-density">Global Building Density</label>
            <input type="text" id="out-zone-density" class="input-text" value="${this.getDensityBadgeText(this.config.density)}" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />
          </div>
          <input type="range" id="zone-density" class="input-range" min="0.05" max="1.00" step="0.05" value="${this.config.density}" />
        </div>

        <!-- Default Layout Template -->
        <div class="form-group">
          <div class="label-row">
            <label for="zone-default-template">Default Zone Template</label>
          </div>
          <select id="zone-default-template" class="input-select">
            ${this.templates.map((t) => `<option value="${t.id}" ${t.id === this.config.default_template ? 'selected' : ''}>${t.name}</option>`).join('')}
          </select>
        </div>

        <!-- Factions Assignment -->
        <div class="form-group">
          <div class="label-row">
            <label>Active Factions</label>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap;">
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
            <input type="text" id="out-zone-max-damage" class="input-text" value="Level 04 (Scorched)" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />
          </div>
          <select id="zone-max-damage" class="input-select">
            <option value="1">01 — Pristine Condition</option>
            <option value="2">02 — Light Battle Damage</option>
            <option value="3">03 — Heavy Structural Damage</option>
            <option value="4" selected>04 — Scorched & Ruined</option>
          </select>
        </div>
      </div>

      <!-- Active Zones & Zone CRUD Section (R2) -->
      <div class="config-section">
        <div class="section-title">
          <span>Active Tactical Zones</span>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span id="zone-count-badge" style="font-size: 10px; color: var(--text-muted);">0 Zones</span>
            <button type="button" class="btn-small" id="btn-toggle-add-zone" style="background: var(--color-primary-glow); border-color: var(--color-primary); color: #4ade80; font-weight: 600;">
              + Add Zone
            </button>
          </div>
        </div>

        <!-- Add Zone Form Container (collapsible) -->
        <div id="add-zone-form-panel" style="display: none; background: rgba(15, 23, 42, 0.9); border: 1px solid var(--color-primary); border-radius: var(--radius-sm); padding: 10px; margin-bottom: 8px;">
          <div style="font-size: 11px; font-weight: 700; color: #4ade80; margin-bottom: 8px;">New Tactical Zone</div>
          
          <div class="form-group" style="margin-bottom: 6px;">
            <label for="new-zone-name" style="font-size: 10px; color: var(--text-secondary);">Zone Name</label>
            <input type="text" id="new-zone-name" class="input-text" placeholder="e.g. Forward Operating Base Delta" value="Tactical Outpost Nova" />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 6px;">
            <div class="form-group">
              <label for="new-zone-faction" style="font-size: 10px; color: var(--text-secondary);">Faction</label>
              <select id="new-zone-faction" class="input-select">
                <option value="A" selected>Faction A (Blue)</option>
                <option value="B">Faction B (Gold)</option>
                <option value="C">Faction C (Cyan)</option>
              </select>
            </div>
            <div class="form-group">
              <label for="new-zone-destruction" style="font-size: 10px; color: var(--text-secondary);">Destruction</label>
              <select id="new-zone-destruction" class="input-select">
                <option value="01" selected>01 (Pristine)</option>
                <option value="02">02 (Minor)</option>
                <option value="03">03 (Heavy)</option>
                <option value="04">04 (Ruined)</option>
              </select>
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 6px;">
            <label for="new-zone-template" style="font-size: 10px; color: var(--text-secondary);">Layout Template</label>
            <select id="new-zone-template" class="input-select">
              ${this.templates.map((t) => `<option value="${t.id}">${t.name}</option>`).join('')}
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 6px;">
            <div class="label-row">
              <label for="new-zone-radius" style="font-size: 10px;">Radius</label>
              <input type="text" id="out-new-zone-radius" class="input-text" value="75m" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />
            </div>
            <input type="range" id="new-zone-radius" class="input-range" min="40" max="150" step="5" value="75" />
          </div>

          <div class="form-group" style="margin-bottom: 8px;">
            <div class="label-row">
              <label for="new-zone-density" style="font-size: 10px;">Density</label>
              <input type="text" id="out-new-zone-density" class="input-text" value="0.55 (Standard Base)" style="width: 70px; text-align: right; padding: 2px; font-size: 11px;" />
            </div>
            <input type="range" id="new-zone-density" class="input-range" min="0.05" max="1.00" step="0.05" value="0.55" />
          </div>

          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <button type="button" class="btn-small" id="btn-cancel-add-zone">Cancel</button>
            <button type="button" class="btn-small" id="btn-confirm-add-zone" style="background: var(--color-primary); color: #022c22; font-weight: 700; border-color: #4ade80;">Create Zone</button>
          </div>
        </div>

        <div id="active-zones-list" style="display: flex; flex-direction: column; gap: 8px; max-height: 380px; overflow-y: auto; scrollbar-gutter: stable; overscroll-behavior: contain;">
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

    // Continuous Density Slider
    const sliderDensity = this.container.querySelector('#zone-density');
    const outDensity = this.container.querySelector('#out-zone-density');
    sliderDensity.addEventListener('input', (e) => {
      this.config.density = parseFloat(e.target.value);
      outDensity.value = this.getDensityBadgeText(this.config.density);
    });

    // Default template selector
    const selectTemplate = this.container.querySelector('#zone-default-template');
    selectTemplate.addEventListener('change', (e) => {
      this.config.default_template = e.target.value;
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

    // Add Zone Toggle Button
    const btnToggleAdd = this.container.querySelector('#btn-toggle-add-zone');
    const panelAddZone = this.container.querySelector('#add-zone-form-panel');
    const btnCancelAdd = this.container.querySelector('#btn-cancel-add-zone');
    const btnConfirmAdd = this.container.querySelector('#btn-confirm-add-zone');

    btnToggleAdd.addEventListener('click', () => {
      this.isAddingZone = !this.isAddingZone;
      panelAddZone.style.display = this.isAddingZone ? 'block' : 'none';
    });

    btnCancelAdd.addEventListener('click', () => {
      this.isAddingZone = false;
      panelAddZone.style.display = 'none';
    });

    const newRadiusSlider = this.container.querySelector('#new-zone-radius');
    const outNewRadius = this.container.querySelector('#out-new-zone-radius');
    newRadiusSlider.addEventListener('input', (e) => {
      outNewRadius.value = `${e.target.value}m`;
    });

    const newDensitySlider = this.container.querySelector('#new-zone-density');
    const outNewDensity = this.container.querySelector('#out-new-zone-density');
    newDensitySlider.addEventListener('input', (e) => {
      outNewDensity.value = this.getDensityBadgeText(parseFloat(e.target.value));
    });

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


    btnConfirmAdd.addEventListener('click', () => {
      const name = this.container.querySelector('#new-zone-name').value.trim() || `Tactical Zone ${this.activeZones.length + 1}`;
      const faction = this.container.querySelector('#new-zone-faction').value;
      const destruction = this.container.querySelector('#new-zone-destruction').value;
      const template = this.container.querySelector('#new-zone-template').value;
      const radius = parseFloat(newRadiusSlider.value) || 75.0;
      const density = parseFloat(newDensitySlider.value) || 0.55;

      const newId = `zone_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      const newZone = {
        id: newId,
        name: name,
        faction: faction,
        destruction: destruction,
        zone_type: template,
        density: density,
        radius: radius,
        center: [500.0 + (Math.random() - 0.5) * 300.0, 20.0, 500.0 + (Math.random() - 0.5) * 300.0],
        footprint_points: []
      };

      this.activeZones.push(newZone);
      this.isAddingZone = false;
      panelAddZone.style.display = 'none';
      this.updateZonesList(this.activeZones, this.activeBuildings);

      if (this.onAddZone) {
        this.onAddZone(newZone);
      }
      if (this.onZonesChanged) {
        this.onZonesChanged(this.activeZones);
      }
    });
  }

  /**
   * Update active zone list display when a manifest is loaded
   */
  updateZonesList(zones, buildings = []) {
    this.activeZones = zones || [];
    this.activeBuildings = buildings || [];
    const listContainer = this.container.querySelector('#active-zones-list');
    const countBadge = this.container.querySelector('#zone-count-badge');

    if (!listContainer) return;

    countBadge.textContent = `${this.activeZones.length} Zones`;

    if (this.activeZones.length === 0) {
      listContainer.innerHTML = `<p style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 12px 0;">No active zones loaded. Click "+ Add Zone" to create one.</p>`;
      return;
    }

    // Count buildings per zone
    const bldCountMap = {};
    for (let b of this.activeBuildings) {
      bldCountMap[b.zone_id] = (bldCountMap[b.zone_id] || 0) + 1;
    }

    listContainer.innerHTML = this.activeZones.map((z, idx) => {
      const faction = (z.faction || 'A').toUpperCase();
      const factionClass = `faction-${faction.toLowerCase()}`;
      const destruction = String(z.destruction || '01');
      const bldCount = bldCountMap[z.id] || (z.building_ids ? z.building_ids.length : 0);
      const densityVal = typeof z.density === 'number' ? z.density : 0.55;
      const zoneType = z.zone_type || 'military_base';

      return `
        <div class="zone-card" data-zone-id="${z.id}" data-zone-index="${idx}">
          <div class="zone-card-header">
            <!-- Inline Editable Rename Input (R2) -->
            <input type="text" class="zone-rename-input input-text" data-zone-id="${z.id}" value="${z.name || `Zone ${idx + 1}`}" title="Click to rename zone" />
            <div style="display: flex; align-items: center; gap: 4px;">
              <span class="zone-faction-badge ${factionClass}">Faction ${faction}</span>
              <!-- Delete Zone Button (R2) -->
              <button type="button" class="btn-icon btn-delete-zone" data-zone-id="${z.id}" title="Delete Zone" style="padding: 2px; color: var(--color-danger); background: transparent; border: none; cursor: pointer;">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
              </button>
            </div>
          </div>

          <div class="zone-card-meta">
            <span>Template: <strong>${zoneType}</strong> | Damage: <strong>${destruction}</strong></span>
            <span>Radius: <strong>${z.radius || 60}m</strong> | Buildings: <strong>${bldCount}</strong></span>
          </div>

          <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px; gap: 6px;">
            <span style="font-size: 10px; color: var(--text-muted);">${this.getDensityBadgeText(densityVal)}</span>
            <button type="button" class="btn-small btn-focus-zone" data-zone-index="${idx}">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><line x1="12" y1="1" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="1" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="23" y2="12"/></svg>
              <span>Focus 3D</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Attach Inline Rename Listeners
    const renameInputs = listContainer.querySelectorAll('.zone-rename-input');
    renameInputs.forEach((input) => {
      input.addEventListener('input', (e) => {
        const zoneId = input.dataset.zoneId;
        const newName = input.value.trim();
        const target = this.activeZones.find((z) => z.id === zoneId);
        if (target) {
          target.name = newName;
          if (this.onUpdateZone) {
            this.onUpdateZone(zoneId, { name: newName });
          }
        }
      });
    });

    // Attach Delete Listeners
    const deleteButtons = listContainer.querySelectorAll('.btn-delete-zone');
    deleteButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const zoneId = btn.dataset.zoneId;
        this.activeZones = this.activeZones.filter((z) => z.id !== zoneId);
        this.updateZonesList(this.activeZones, this.activeBuildings);

        if (this.onDeleteZone) {
          this.onDeleteZone(zoneId);
        }
        if (this.onZonesChanged) {
          this.onZonesChanged(this.activeZones);
        }
      });
    });

    // Attach Focus Button Listeners
    
    const editButtons = listContainer.querySelectorAll('.btn-edit-zone');
    editButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const zoneId = btn.getAttribute('data-zone-id');
        const form = listContainer.querySelector(`#edit-form-${zoneId}`);
        if (form.style.display === 'none') {
          form.style.display = 'flex';
        } else {
          form.style.display = 'none';
        }
      });
    });
    
    const saveEditButtons = listContainer.querySelectorAll('.btn-save-zone-edit');
    saveEditButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const zoneId = btn.getAttribute('data-zone-id');
        const form = listContainer.querySelector(`#edit-form-${zoneId}`);
        
        const template = form.querySelector('.edit-zone-template').value;
        const radius = parseFloat(form.querySelector('.edit-zone-radius').value);
        const density = parseFloat(form.querySelector('.edit-zone-density').value);
        const faction = form.querySelector('.edit-zone-faction').value;
        const destruction = form.querySelector('.edit-zone-destruction').value;
        
        const target = this.activeZones.find((z) => z.id === zoneId);
        if (target) {
            target.type = template;
            target.zone_type = template;
            target.radius = radius;
            target.density = density;
            target.faction = faction;
            target.destruction = destruction;
            
            form.style.display = 'none';
            if (this.onUpdateZone) {
                this.onUpdateZone(zoneId, target);
            }
            if (this.onZonesChanged) {
                this.onZonesChanged(this.activeZones);
            }
        }
      });
    });

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

