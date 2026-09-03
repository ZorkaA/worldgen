import re

with open("frontend/src/components/zone_panel.js", "r") as f:
    content = f.read()

# Define the edit form HTML
edit_form_html = """
          <div class="zone-edit-form" id="edit-form-${z.id}" style="display: none; flex-direction: column; gap: 8px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color);">
            <div class="form-group-compact">
              <label>Template</label>
              <select class="edit-zone-template input-select input-compact" data-zone-id="${z.id}">
                ${this.templates.map((t) => `<option value="${t.id}" ${t.id === (z.type || z.zone_type || 'military_base') ? 'selected' : ''}>${t.name}</option>`).join('')}
              </select>
            </div>
            <div class="form-group-compact">
              <label>Radius (${z.radius || 60}m)</label>
              <input type="range" class="edit-zone-radius input-range" data-zone-id="${z.id}" min="20" max="250" step="10" value="${z.radius || 60}" />
            </div>
            <div class="form-group-compact">
              <label>Density (${z.density || 0.6})</label>
              <input type="range" class="edit-zone-density input-range" data-zone-id="${z.id}" min="0.1" max="1.0" step="0.1" value="${z.density || 0.6}" />
            </div>
            <div class="form-group-compact">
              <label>Faction</label>
              <select class="edit-zone-faction input-select input-compact" data-zone-id="${z.id}">
                <option value="A" ${faction === 'A' ? 'selected' : ''}>Faction A</option>
                <option value="B" ${faction === 'B' ? 'selected' : ''}>Faction B</option>
                <option value="C" ${faction === 'C' ? 'selected' : ''}>Faction C</option>
              </select>
            </div>
            <div class="form-group-compact">
              <label>Damage</label>
              <select class="edit-zone-destruction input-select input-compact" data-zone-id="${z.id}">
                <option value="0" ${destruction === '0' ? 'selected' : ''}>Pristine (0)</option>
                <option value="1" ${destruction === '1' ? 'selected' : ''}>Light (1)</option>
                <option value="2" ${destruction === '2' ? 'selected' : ''}>Moderate (2)</option>
                <option value="3" ${destruction === '3' ? 'selected' : ''}>Heavy (3)</option>
                <option value="4" ${destruction === '4' ? 'selected' : ''}>Ruined (4)</option>
              </select>
            </div>
            <button class="btn-primary btn-save-zone-edit" data-zone-id="${z.id}">Apply Changes</button>
          </div>
"""

# Replace the HTML block inside the map
replacement_card = f"""
            <div style="display: flex; align-items: center; gap: 4px;">
              <span class="zone-faction-badge ${{factionClass}}">Faction ${{faction}}</span>
              <button type="button" class="btn-icon btn-edit-zone" data-zone-id="${{z.id}}" title="Edit Zone" style="padding: 2px; color: var(--text-muted); background: transparent; border: none; cursor: pointer;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
              </button>
              <!-- Delete Zone Button (R2) -->
              <button type="button" class="btn-icon btn-delete-zone" data-zone-id="${{z.id}}" title="Delete Zone" style="padding: 2px; color: var(--color-danger); background: transparent; border: none; cursor: pointer;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
          </div>
          <div class="zone-card-meta">
            <span>Template: <strong>${{zoneType}}</strong> | Damage: <strong>${{destruction}}</strong></span>
            <span>Radius: <strong>${{z.radius || 60}}m</strong> | Buildings: <strong>${{bldCount}}</strong></span>
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px; gap: 6px;">
            <span style="font-size: 10px; color: var(--text-muted);">${{this.getDensityBadgeText(densityVal)}}</span>
            <button type="button" class="btn-small btn-focus-zone" data-zone-index="${{idx}}">
              Focus Camera
            </button>
          </div>
          {edit_form_html}
        </div>
"""

content = re.sub(
    r'<div style="display: flex; align-items: center; gap: 4px;">.*?Focus Camera\s*</button>\s*</div>\s*</div>',
    replacement_card,
    content,
    flags=re.DOTALL
)

# Add event listeners for edit
event_listeners = """
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
"""

content = content.replace("const focusButtons = listContainer.querySelectorAll('.btn-focus-zone');", event_listeners + "\n    const focusButtons = listContainer.querySelectorAll('.btn-focus-zone');")

with open("frontend/src/components/zone_panel.js", "w") as f:
    f.write(content)
print("Patched zone editing")
