import re

with open("frontend/src/components/zone_panel.js", "r") as f:
    content = f.read()

edit_form_html = """
          <div class="zone-edit-form" id="edit-form-${z.id}" style="display: none; flex-direction: column; gap: 8px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-subtle);">
            <div class="form-group-compact" style="display: flex; flex-direction: column; gap: 2px;">
              <label style="font-size: 10px; color: var(--text-muted);">Template</label>
              <select class="edit-zone-template input-select input-compact" data-zone-id="${z.id}" style="font-size: 11px; padding: 2px 4px;">
                ${this.templates.map((t) => `<option value="${t.id}" ${t.id === (z.type || z.zone_type || 'military_base') ? 'selected' : ''}>${t.name}</option>`).join('')}
              </select>
            </div>
            <div class="form-group-compact" style="display: flex; flex-direction: column; gap: 2px;">
              <label style="font-size: 10px; color: var(--text-muted);">Radius (${z.radius || 60}m)</label>
              <input type="number" class="edit-zone-radius input-text input-compact" data-zone-id="${z.id}" value="${z.radius || 60}" style="font-size: 11px; padding: 2px 4px;" />
            </div>
            <div class="form-group-compact" style="display: flex; flex-direction: column; gap: 2px;">
              <label style="font-size: 10px; color: var(--text-muted);">Density (${z.density || 0.6})</label>
              <input type="number" class="edit-zone-density input-text input-compact" data-zone-id="${z.id}" step="0.05" value="${z.density || 0.6}" style="font-size: 11px; padding: 2px 4px;" />
            </div>
            <div style="display: flex; gap: 8px;">
                <div class="form-group-compact" style="display: flex; flex-direction: column; gap: 2px; flex: 1;">
                  <label style="font-size: 10px; color: var(--text-muted);">Faction</label>
                  <select class="edit-zone-faction input-select input-compact" data-zone-id="${z.id}" style="font-size: 11px; padding: 2px 4px;">
                    <option value="A" ${faction === 'A' ? 'selected' : ''}>A</option>
                    <option value="B" ${faction === 'B' ? 'selected' : ''}>B</option>
                    <option value="C" ${faction === 'C' ? 'selected' : ''}>C</option>
                  </select>
                </div>
                <div class="form-group-compact" style="display: flex; flex-direction: column; gap: 2px; flex: 1;">
                  <label style="font-size: 10px; color: var(--text-muted);">Damage</label>
                  <select class="edit-zone-destruction input-select input-compact" data-zone-id="${z.id}" style="font-size: 11px; padding: 2px 4px;">
                    <option value="0" ${destruction === '0' ? 'selected' : ''}>0</option>
                    <option value="1" ${destruction === '1' ? 'selected' : ''}>1</option>
                    <option value="2" ${destruction === '2' ? 'selected' : ''}>2</option>
                    <option value="3" ${destruction === '3' ? 'selected' : ''}>3</option>
                    <option value="4" ${destruction === '4' ? 'selected' : ''}>4</option>
                  </select>
                </div>
            </div>
            <button class="btn-primary btn-save-zone-edit" data-zone-id="${z.id}" style="font-size: 11px; padding: 4px; margin-top: 4px;">Apply Changes</button>
          </div>
"""

old_block = """            <div style="display: flex; align-items: center; gap: 4px;">
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
              Focus Camera
            </button>
          </div>
        </div>"""

new_block = """            <div style="display: flex; align-items: center; gap: 4px;">
              <span class="zone-faction-badge ${factionClass}">Faction ${faction}</span>
              <!-- Edit Zone Button -->
              <button type="button" class="btn-icon btn-edit-zone" data-zone-id="${z.id}" title="Edit Zone" style="padding: 2px; color: var(--text-muted); background: transparent; border: none; cursor: pointer;">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
              </button>
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
              Focus Camera
            </button>
          </div>
""" + edit_form_html + """
        </div>"""

content = content.replace(old_block, new_block)

with open("frontend/src/components/zone_panel.js", "w") as f:
    f.write(content)
print("Patched zone_panel HTML")
