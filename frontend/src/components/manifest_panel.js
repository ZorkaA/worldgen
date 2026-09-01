/**
 * World Manifest & Export Panel Component
 * Displays summary metrics (zones, buildings, roads, world size),
 * formatted JSON manifest preview, file download, and clipboard copy.
 */
export class ManifestPanel {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.onRefresh = options.onRefresh || null;
    this.onNotify = options.onNotify || null;

    this.manifest = null;

    this.render();
  }

  render() {
    this.container.innerHTML = `
      <!-- Manifest Summary Stats -->
      <div class="config-section">
        <div class="section-title">
          <span>World Statistics</span>
        </div>
        <div class="manifest-stats-grid">
          <div class="stat-box">
            <span class="stat-box-title">World Seed</span>
            <span class="stat-box-value" id="manifest-stat-seed">-</span>
          </div>
          <div class="stat-box">
            <span class="stat-box-title">Resolution</span>
            <span class="stat-box-value" id="manifest-stat-res">-</span>
          </div>
          <div class="stat-box">
            <span class="stat-box-title">Military Zones</span>
            <span class="stat-box-value" id="manifest-stat-zones">0</span>
          </div>
          <div class="stat-box">
            <span class="stat-box-title">Buildings Placed</span>
            <span class="stat-box-value" id="manifest-stat-buildings">0</span>
          </div>
          <div class="stat-box">
            <span class="stat-box-title">Road Segments</span>
            <span class="stat-box-value" id="manifest-stat-roads">0</span>
          </div>
          <div class="stat-box">
            <span class="stat-box-title">World Bounds</span>
            <span class="stat-box-value" id="manifest-stat-bounds">1000m</span>
          </div>
        </div>
      </div>

      <!-- Export Actions -->
      <div class="config-section">
        <div class="section-title">
          <span>Export & Sync</span>
        </div>
        <div class="action-buttons-row">
          <button type="button" class="btn-secondary" id="btn-download-manifest">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <span>Download JSON</span>
          </button>
          <button type="button" class="btn-secondary" id="btn-copy-manifest">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            <span>Copy JSON</span>
          </button>
        </div>
      </div>

      <!-- JSON Preview Box -->
      <div class="config-section">
        <div class="section-title">
          <span>world_manifest.json Preview</span>
        </div>
        <pre class="json-viewer-box" id="manifest-json-preview">Loading manifest data...</pre>
      </div>
    `;

    this.attachEventListeners();
  }

  attachEventListeners() {
    const btnDownload = this.container.querySelector('#btn-download-manifest');
    btnDownload.addEventListener('click', () => {
      this.downloadManifestFile();
    });

    const btnCopy = this.container.querySelector('#btn-copy-manifest');
    btnCopy.addEventListener('click', () => {
      this.copyManifestToClipboard();
    });
  }

  setManifest(manifest) {
    if (!manifest) return;
    this.manifest = manifest;

    const seed = manifest.metadata?.seed ?? '-';
    const res = Array.isArray(manifest.terrain?.resolution)
      ? manifest.terrain.resolution.join('x')
      : (manifest.terrain?.resolution ?? '-');
    const zonesCount = manifest.zones?.length ?? 0;
    const bldCount = manifest.buildings?.length ?? 0;
    const roadCount = manifest.roads?.length ?? 0;
    const worldSize = manifest.terrain?.world_size || [1000, 150, 1000];

    this.container.querySelector('#manifest-stat-seed').textContent = seed;
    this.container.querySelector('#manifest-stat-res').textContent = `${res} x ${res}`;
    this.container.querySelector('#manifest-stat-zones').textContent = zonesCount;
    this.container.querySelector('#manifest-stat-buildings').textContent = bldCount;
    this.container.querySelector('#manifest-stat-roads').textContent = roadCount;
    this.container.querySelector('#manifest-stat-bounds').textContent = `${worldSize[0]}m × ${worldSize[2]}m`;

    // Format JSON preview (trimming giant heightmap array for smooth rendering)
    const previewObj = {
      $schema: manifest.$schema || 'https://json-schema.org/draft/2020-12/schema',
      metadata: manifest.metadata,
      terrain: {
        resolution: manifest.terrain?.resolution,
        world_size: manifest.terrain?.world_size,
        height_scale: manifest.terrain?.height_scale,
        heightmap_sample: `[Array of ${manifest.terrain?.heightmap?.length || 0} rows x ${manifest.terrain?.heightmap?.[0]?.length || 0} cols]`
      },
      zones_count: manifest.zones?.length,
      zones: manifest.zones?.slice(0, 3),
      buildings_count: manifest.buildings?.length,
      buildings: manifest.buildings?.slice(0, 3),
      roads_count: manifest.roads?.length,
      roads: manifest.roads
    };

    const jsonBox = this.container.querySelector('#manifest-json-preview');
    if (jsonBox) {
      jsonBox.textContent = JSON.stringify(previewObj, null, 2);
    }
  }

  downloadManifestFile() {
    if (!this.manifest) {
      if (this.onNotify) this.onNotify('No manifest available to download', 'error');
      return;
    }

    const jsonStr = JSON.stringify(this.manifest, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `world_manifest_seed_${this.manifest.metadata?.seed || 42}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    if (this.onNotify) {
      this.onNotify('world_manifest.json downloaded successfully!');
    }
  }

  copyManifestToClipboard() {
    if (!this.manifest) {
      if (this.onNotify) this.onNotify('No manifest available to copy', 'error');
      return;
    }

    const jsonStr = JSON.stringify(this.manifest, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
      if (this.onNotify) this.onNotify('Manifest JSON copied to clipboard!');
    }).catch((err) => {
      console.error('Failed to copy manifest', err);
      if (this.onNotify) this.onNotify('Failed to copy to clipboard', 'error');
    });
  }
}
