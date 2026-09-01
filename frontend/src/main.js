/**
 * WorldGen 3D — Main Application Entry Point
 * Bootstraps Three.js 3D Visualizer, HUD Side Panels, API Client, and Event Wiring.
 */
import './style.css';
import { ApiClient } from './api/client.js';
import { WorldViewer } from './scene/viewer.js';
import { HudController } from './components/hud.js';
import { TerrainPanel } from './components/terrain_panel.js';
import { ZonePanel } from './components/zone_panel.js';
import { CatalogBrowser } from './components/catalog_browser.js';
import { ManifestPanel } from './components/manifest_panel.js';

class WorldGenApp {
  constructor() {
    this.api = new ApiClient();
    this.viewer = null;
    this.hud = null;
    this.terrainPanel = null;
    this.zonePanel = null;
    this.catalogBrowser = null;
    this.manifestPanel = null;

    this.activeManifest = null;
  }

  async start() {
    // 1. Initialize Three.js 3D Viewport
    const canvas = document.getElementById('webgl-canvas');
    this.viewer = new WorldViewer(canvas, {
      onHover: (userData, x, y) => this.hud?.showTooltip(userData, x, y),
      onClick: (userData) => this.handleSceneObjectClick(userData),
      onStats: (stats) => this.hud?.updateStats(stats),
    });

    // 2. Initialize HUD Controller
    this.hud = new HudController({
      viewer: this.viewer,
      api: this.api,
      onGenerateWorld: () => this.handleGenerateWorld(),
    });

    // 3. Initialize Side Panels
    const terrainContainer = document.getElementById('terrain-controls-container');
    this.terrainPanel = new TerrainPanel(terrainContainer, (config) => {
      this.handleGenerateWorld(config);
    });

    const zoneContainer = document.getElementById('zone-controls-container');
    this.zonePanel = new ZonePanel(zoneContainer, {
      onFocusZone: (zone) => {
        if (zone.center) {
          this.viewer.focusOn(zone.center, (zone.radius || 60) * 1.6);
          this.hud.showToast(`Focused on ${zone.name}`);
        }
      },
    });

    const catalogContainer = document.getElementById('catalog-browser-container');
    this.catalogBrowser = new CatalogBrowser(catalogContainer, {
      onInspectAsset: (asset) => this.hud.openAssetModal(asset),
    });

    const manifestContainer = document.getElementById('manifest-export-container');
    this.manifestPanel = new ManifestPanel(manifestContainer, {
      onNotify: (msg, type) => this.hud.showToast(msg, type),
    });

    // 4. Check Backend Health
    this.hud.setGenerating(true, 'Initializing WorldGen 3D...', 'Checking backend services and loading assets');
    const health = await this.api.checkHealth();
    this.hud.updateConnectionStatus(health.online, health.data);

    // 5. Load Asset Catalog
    const catalog = await this.api.getCatalog();
    this.catalogBrowser.setCatalog(catalog);

    // 6. Load Initial World Manifest
    try {
      const initialManifest = await this.api.getManifest();
      this.applyManifest(initialManifest);
      this.hud.showToast('World Manifest Loaded Successfully');
    } catch (err) {
      console.error('Failed to load initial manifest', err);
      this.hud.showToast('Error loading initial manifest, synthesized fallback', 'error');
    } finally {
      this.hud.setGenerating(false);
    }
  }

  /**
   * Execute World Generation with combined UI parameters
   */
  async handleGenerateWorld(overrideConfig = null) {
    const terrainConfig = this.terrainPanel.getConfig();
    const zoneConfig = this.zonePanel.getConfig();

    const mergedConfig = {
      ...terrainConfig,
      ...zoneConfig,
      ...(overrideConfig || {}),
    };

    this.hud.setGenerating(true, 'Synthesizing Tactical World...', 'Computing multifractal terrain, Poisson zones & SAT buildings');
    this.terrainPanel.setLoading(true);

    try {
      const response = await this.api.generateWorld(mergedConfig);
      if (response && response.manifest) {
        this.applyManifest(response.manifest);
        const execTime = response.execution_time_seconds || 0;
        this.hud.showToast(`Generated World (Seed: ${response.seed}) in ${execTime.toFixed(2)}s`);
      } else {
        throw new Error('Invalid generation response');
      }
    } catch (err) {
      console.error('Generation failed', err);
      this.hud.showToast('Generation failed. Check console for details.', 'error');
    } finally {
      this.hud.setGenerating(false);
      this.terrainPanel.setLoading(false);
    }
  }

  /**
   * Apply manifest across 3D Scene and UI Panels
   */
  applyManifest(manifest) {
    if (!manifest) return;
    this.activeManifest = manifest;

    // Update 3D Scene
    this.viewer.loadManifest(manifest);

    // Update UI Panels
    this.zonePanel.updateZonesList(manifest.zones, manifest.buildings);
    this.manifestPanel.setManifest(manifest);
    this.hud.updateStatusBar(manifest);
  }

  handleSceneObjectClick(userData) {
    if (!userData) return;

    if (userData.type === 'zone') {
      const zone = userData.data;
      if (zone.center) {
        this.viewer.focusOn(zone.center, (zone.radius || 60) * 1.5);
        this.hud.showToast(`Selected Zone: ${zone.name}`);
      }
    } else if (userData.type === 'building') {
      const bld = userData.data;
      if (bld.position) {
        this.viewer.focusOn(bld.position, 40);
        this.hud.showToast(`Selected Building: ${bld.prefab_name}`);
      }
    }
  }
}

// Bootstrap on DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  const app = new WorldGenApp();
  app.start();
});
