/**
 * Main HUD & UI Orchestrator Component
 * Manages tab switching, camera toolbar buttons, floating tooltips, compass gizmo,
 * detail modals (<dialog>), toast notifications, and global keyboard shortcuts.
 */
export class HudController {
  constructor(options = {}) {
    this.viewer = options.viewer || null;
    this.api = options.api || null;
    this.onGenerateWorld = options.onGenerateWorld || null;

    this.modal = document.getElementById('detail-modal');
    this.modalTitle = document.getElementById('modal-title');
    this.modalBody = document.getElementById('modal-body');
    this.btnCloseModal = document.getElementById('btn-close-modal');

    this.tooltip = document.getElementById('scene-tooltip');
    this.tooltipTitle = document.getElementById('tooltip-title');
    this.tooltipBody = document.getElementById('tooltip-body');

    this.spinnerOverlay = document.getElementById('generation-spinner');
    this.spinnerTitle = document.getElementById('spinner-title');
    this.spinnerDesc = document.getElementById('spinner-desc');

    this.init();
  }

  init() {
    this.setupTabs();
    this.setupCameraToolbar();
    this.setupModal();
    this.setupKeyboardShortcuts();
    this.setupQuickGenerate();
  }

  setupTabs() {
    // Left and Right Panel Tab Switchers
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const parentTabs = btn.closest('.panel-header');
        const sidePanel = btn.closest('.side-panel');
        const targetId = btn.dataset.target;

        // Deactivate sibling tabs
        parentTabs.querySelectorAll('.tab-btn').forEach((b) => {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');

        // Show target panel content
        sidePanel.querySelectorAll('.tab-content').forEach((content) => {
          if (content.id === targetId) {
            content.classList.add('active');
            content.removeAttribute('hidden');
          } else {
            content.classList.remove('active');
            content.setAttribute('hidden', '');
          }
        });
      });
    });
  }

  setupCameraToolbar() {
    const btnOrbit = document.getElementById('btn-cam-orbit');
    const btnTop = document.getElementById('btn-cam-top');
    const btnIso = document.getElementById('btn-cam-iso');
    const btnWireframe = document.getElementById('btn-toggle-wireframe');

    const setActiveCamButton = (activeBtn) => {
      [btnOrbit, btnTop, btnIso].forEach((b) => b.classList.remove('active'));
      if (activeBtn) activeBtn.classList.add('active');
    };

    btnOrbit?.addEventListener('click', () => {
      setActiveCamButton(btnOrbit);
      if (this.viewer) this.viewer.setCameraPreset('orbit');
    });

    btnTop?.addEventListener('click', () => {
      setActiveCamButton(btnTop);
      if (this.viewer) this.viewer.setCameraPreset('top');
    });

    btnIso?.addEventListener('click', () => {
      setActiveCamButton(btnIso);
      if (this.viewer) this.viewer.setCameraPreset('iso');
    });

    btnWireframe?.addEventListener('click', () => {
      if (this.viewer) {
        const isWire = this.viewer.toggleWireframe();
        btnWireframe.classList.toggle('active', isWire);
        this.showToast(isWire ? 'Wireframe Mode: ON' : 'Wireframe Mode: OFF');
      }
    });

    const btnZones = document.getElementById('btn-toggle-zones');
    btnZones?.addEventListener('click', () => {
      btnZones.classList.toggle('active');
      const isVisible = btnZones.classList.contains('active');
      if (this.viewer && this.viewer.zones && this.viewer.zones.group) {
        this.viewer.zones.group.visible = isVisible;
      }
    });

    const btnAssets = document.getElementById('btn-toggle-assets');
    btnAssets?.addEventListener('click', () => {
      btnAssets.classList.toggle('active');
      const isVisible = btnAssets.classList.contains('active');
      if (this.viewer && this.viewer.buildings && this.viewer.buildings.group) {
        this.viewer.buildings.group.visible = isVisible;
      }
    });
  }

  setupQuickGenerate() {
    const btnQuick = document.getElementById('btn-quick-generate');
    btnQuick?.addEventListener('click', () => {
      if (this.onGenerateWorld) {
        this.onGenerateWorld();
      }
    });
  }

  setupModal() {
    this.btnCloseModal?.addEventListener('click', () => {
      this.closeModal();
    });

    // Close on backdrop click
    this.modal?.addEventListener('click', (e) => {
      const rect = this.modal.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        this.closeModal();
      }
    });
  }

  setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // Ignore if typing in an input
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;

      if (e.key === '1') {
        document.getElementById('btn-cam-orbit')?.click();
      } else if (e.key === '2') {
        document.getElementById('btn-cam-top')?.click();
      } else if (e.key === '3') {
        document.getElementById('btn-cam-iso')?.click();
      } else if (e.key === 'w' || e.key === 'W') {
        document.getElementById('btn-toggle-wireframe')?.click();
      } else if (e.key === 'g' || e.key === 'G') {
        document.getElementById('btn-quick-generate')?.click();
      } else if (e.key === 'Escape') {
        this.closeModal();
      }
    });
  }

  /**
   * Display Object Hover Tooltip
   */
  showTooltip(userData, screenX, screenY) {
    if (!userData) {
      if (this.tooltip) this.tooltip.setAttribute('hidden', '');
      return;
    }

    if (!this.tooltip) return;

    if (userData.type === 'building') {
      const bld = userData.data;
      const dims = userData.dimensions || [0, 0, 0];
      this.tooltipTitle.textContent = bld.prefab_name || 'Building';
      this.tooltipBody.innerHTML = `
        <div class="tooltip-row">
          <span>Role:</span>
          <span class="tooltip-val">${bld.placement_role || 'structure'}</span>
        </div>
        <div class="tooltip-row">
          <span>Faction:</span>
          <span class="tooltip-val">Faction ${bld.faction || 'A'}</span>
        </div>
        <div class="tooltip-row">
          <span>Damage:</span>
          <span class="tooltip-val">Level ${bld.destruction || '01'}</span>
        </div>
        <div class="tooltip-row">
          <span>Size:</span>
          <span class="tooltip-val">${dims[0].toFixed(1)}m × ${dims[1].toFixed(1)}m × ${dims[2].toFixed(1)}m</span>
        </div>
      `;
    } else if (userData.type === 'zone') {
      const zone = userData.data;
      this.tooltipTitle.textContent = zone.name || 'Zone';
      this.tooltipBody.innerHTML = `
        <div class="tooltip-row">
          <span>Faction:</span>
          <span class="tooltip-val">Faction ${zone.faction || 'A'}</span>
        </div>
        <div class="tooltip-row">
          <span>Damage:</span>
          <span class="tooltip-val">Level ${zone.destruction || '01'}</span>
        </div>
        <div class="tooltip-row">
          <span>Radius:</span>
          <span class="tooltip-val">${zone.radius || 60}m</span>
        </div>
      `;
    }

    this.tooltip.style.left = `${screenX}px`;
    this.tooltip.style.top = `${screenY - 15}px`;
    this.tooltip.removeAttribute('hidden');
  }

  /**
   * Open Asset Detail Inspector Modal
   */
  openAssetModal(asset) {
    if (!this.modal || !asset) return;

    const bbox = asset.bounding_box || {};
    const size = bbox.size || bbox.dimensions || [0, 0, 0];
    const center = bbox.center || [0, 0, 0];
    const min = bbox.min || [0, 0, 0];
    const max = bbox.max || [0, 0, 0];

    const frontImg = asset.render_paths?.front || `/renders/${asset.name}_front.png`;
    const sideImg = asset.render_paths?.side || `/renders/${asset.name}_side.png`;
    const topImg = asset.render_paths?.top || `/renders/${asset.name}_top.png`;

    this.modalTitle.textContent = asset.name;
    this.modalBody.innerHTML = `
      <!-- Multi-Angle Render Gallery -->
      <div class="modal-renders-grid">
        <div class="modal-render-card">
          <img src="${frontImg}" alt="Front View" onerror="this.src='/favicon.svg';" />
          <span class="modal-render-label">Front</span>
        </div>
        <div class="modal-render-card">
          <img src="${sideImg}" alt="Side View" onerror="this.src='/favicon.svg';" />
          <span class="modal-render-label">Side</span>
        </div>
        <div class="modal-render-card">
          <img src="${topImg}" alt="Top View" onerror="this.src='/favicon.svg';" />
          <span class="modal-render-label">Top</span>
        </div>
      </div>

      <!-- Metadata Table -->
      <table class="modal-meta-table">
        <tbody>
          <tr>
            <td class="modal-meta-label">Prefab Name</td>
            <td class="modal-meta-value">${asset.name}</td>
          </tr>
          <tr>
            <td class="modal-meta-label">Placement Role</td>
            <td class="modal-meta-value">${asset.placement_role}</td>
          </tr>
          <tr>
            <td class="modal-meta-label">Category</td>
            <td class="modal-meta-value">${asset.category}</td>
          </tr>
          <tr>
            <td class="modal-meta-label">Tags</td>
            <td class="modal-meta-value">
              ${(asset.tags || []).map((t) => `<span class="filter-chip" style="font-size: 9px; padding: 1px 6px;">${t}</span>`).join(' ')}
            </td>
          </tr>
          <tr>
            <td class="modal-meta-label">Bounding Box Size</td>
            <td class="modal-meta-value">${size[0].toFixed(3)}m × ${size[1].toFixed(3)}m × ${size[2].toFixed(3)}m</td>
          </tr>
          <tr>
            <td class="modal-meta-label">Center Offset</td>
            <td class="modal-meta-value">[${center.map((v) => v.toFixed(3)).join(', ')}]</td>
          </tr>
          <tr>
            <td class="modal-meta-label">Bounds Min / Max</td>
            <td class="modal-meta-value">
              Min: [${min.map((v) => v.toFixed(2)).join(', ')}]<br/>
              Max: [${max.map((v) => v.toFixed(2)).join(', ')}]
            </td>
          </tr>
        </tbody>
      </table>
    `;

    this.modal.showModal();
  }

  closeModal() {
    if (this.modal && this.modal.open) {
      this.modal.close();
    }
  }

  /**
   * Show/Hide Full Screen Generation Radar Overlay
   */
  setGenerating(isGenerating, title = 'Generating World...', desc = 'Computing terrain & placing structures') {
    if (!this.spinnerOverlay) return;
    if (isGenerating) {
      this.spinnerTitle.textContent = title;
      this.spinnerDesc.textContent = desc;
      this.spinnerOverlay.removeAttribute('hidden');
    } else {
      this.spinnerOverlay.setAttribute('hidden', '');
    }

    const quickBtn = document.getElementById('btn-quick-generate');
    if (quickBtn) {
      quickBtn.disabled = isGenerating;
      quickBtn.classList.toggle('is-loading', isGenerating);
    }
  }

  /**
   * Update Status Bar Metrics
   */
  updateStatusBar(manifest) {
    if (!manifest) return;
    const seed = manifest.metadata?.seed ?? '-';
    const res = Array.isArray(manifest.terrain?.resolution)
      ? manifest.terrain.resolution.join('x')
      : (manifest.terrain?.resolution ?? '-');

    document.getElementById('status-seed').textContent = seed;
    document.getElementById('status-resolution').textContent = `${res} x ${res}`;
    document.getElementById('status-zones').textContent = manifest.zones?.length ?? 0;
    document.getElementById('status-buildings').textContent = manifest.buildings?.length ?? 0;
    document.getElementById('status-roads').textContent = manifest.roads?.length ?? 0;
  }

  /**
   * Update Backend Connection Badge
   */
  updateConnectionStatus(isOnline, info = null) {
    const badge = document.getElementById('connection-badge');
    const text = document.getElementById('connection-status-text');
    if (!badge || !text) return;

    if (isOnline) {
      badge.className = 'status-badge status-online';
      text.textContent = 'Backend Online';
    } else {
      badge.className = 'status-badge status-offline';
      text.textContent = 'Offline Mode (Cached)';
    }
  }

  /**
   * Update Performance & Compass Stats
   */
  updateStats(stats) {
    if (!stats) return;
    const fpsElem = document.getElementById('hud-fps-counter');
    const polyElem = document.getElementById('hud-poly-counter');
    const needle = document.getElementById('compass-needle');

    if (fpsElem && stats.fps !== undefined) {
      fpsElem.textContent = `${stats.fps} FPS`;
    }
    if (polyElem && stats.triangles !== undefined) {
      const kTris = (stats.triangles / 1000).toFixed(1);
      polyElem.textContent = `${kTris}k Tris`;
    }
    if (needle && stats.azimuthAngle !== undefined) {
      // Rotate needle relative to camera azimuth
      const deg = (stats.azimuthAngle * 180) / Math.PI;
      needle.style.transform = `translate(-50%, -50%) rotate(${-deg}deg)`;
    }
  }

  /**
   * Toast notification manager
   */
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'toast-error' : ''}`;
    toast.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.2s ease';
      setTimeout(() => toast.remove(), 200);
    }, 3200);
  }
}
