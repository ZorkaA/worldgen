/**
 * Asset Catalog Browser Component
 * Interactive visual gallery with multi-angle renders, search & category filtering,
 * responsive container cards, and detailed 3D bounding box metadata inspector.
 */
export class CatalogBrowser {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.onInspectAsset = options.onInspectAsset || null;

    this.allAssets = [];
    this.filteredAssets = [];
    this.searchQuery = '';
    this.selectedCategory = 'all';
    this.selectedTag = null;

    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div class="config-section">
        <div class="section-title">
          <span>Synty PolygonMilitary Assets</span>
          <span id="catalog-asset-count" style="font-size: 10px; color: var(--text-muted);">Loading...</span>
        </div>

        <!-- Search Bar -->
        <div class="catalog-search-bar">
          <input type="search" id="catalog-search-input" class="input-text" placeholder="Search prefabs, roles, tags (e.g. tent, tower)..." />

          <!-- Category Filter Chips -->
          <div class="catalog-filter-tags">
            <button type="button" class="filter-chip active" data-category="all">All</button>
            <button type="button" class="filter-chip" data-category="building">Buildings</button>
            <button type="button" class="filter-chip" data-category="structures">Structures</button>
            <button type="button" class="filter-chip" data-category="props">Props</button>
            <button type="button" class="filter-chip" data-category="vehicles">Vehicles</button>
            <button type="button" class="filter-chip" data-category="decals">Decals</button>
          </div>
        </div>

        <!-- Asset Cards Grid (Container Queries applied) -->
        <div id="catalog-grid" class="catalog-grid" style="max-height: 480px; overflow-y: auto; scrollbar-gutter: stable; overscroll-behavior: contain; padding-right: 4px;">
          <p style="grid-column: 1 / -1; font-size: 11px; color: var(--text-muted); text-align: center; padding: 24px 0;">Loading asset catalog...</p>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  attachEventListeners() {
    const searchInput = this.container.querySelector('#catalog-search-input');
    searchInput.addEventListener('input', (e) => {
      this.searchQuery = e.target.value.toLowerCase().trim();
      this.filterAndRenderGrid();
    });

    const categoryChips = this.container.querySelectorAll('.filter-chip');
    categoryChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        categoryChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        this.selectedCategory = chip.dataset.category;
        this.filterAndRenderGrid();
      });
    });
  }

  /**
   * Populate catalog with loaded data
   */
  setCatalog(catalogData) {
    if (!catalogData) return;

    const rawAssets = catalogData.assets || catalogData.prefabs || {};
    this.allAssets = Object.entries(rawAssets).map(([key, item]) => {
      return {
        id: key,
        name: item.name || item.prefab_name || key,
        category: (item.category || 'building').toLowerCase(),
        placement_role: item.placement_role || 'structure',
        tags: Array.isArray(item.tags) ? item.tags : [],
        description: item.description || '',
        bounding_box: item.bounding_box || item.bbox || { size: [4, 4, 4], center: [0, 2, 0] },
        render_paths: item.render_paths || item.multi_angle_renders || {
          front: `/renders/${key}_front.png`,
          side: `/renders/${key}_side.png`,
          top: `/renders/${key}_top.png`
        }
      };
    });

    const countLabel = this.container.querySelector('#catalog-asset-count');
    if (countLabel) countLabel.textContent = `${this.allAssets.length} Assets`;

    this.filterAndRenderGrid();
  }

  filterAndRenderGrid() {
    const grid = this.container.querySelector('#catalog-grid');
    if (!grid) return;

    this.filteredAssets = this.allAssets.filter((asset) => {
      // Category filter
      if (this.selectedCategory !== 'all') {
        if (!asset.category.includes(this.selectedCategory) && !asset.placement_role.includes(this.selectedCategory)) {
          return false;
        }
      }

      // Search query filter
      if (this.searchQuery) {
        const matchesName = asset.name.toLowerCase().includes(this.searchQuery);
        const matchesRole = asset.placement_role.toLowerCase().includes(this.searchQuery);
        const matchesTags = asset.tags.some((t) => t.toLowerCase().includes(this.searchQuery));
        if (!matchesName && !matchesRole && !matchesTags) {
          return false;
        }
      }

      return true;
    });

    if (this.filteredAssets.length === 0) {
      grid.innerHTML = `<p style="grid-column: 1 / -1; font-size: 11px; color: var(--text-muted); text-align: center; padding: 24px 0;">No assets matching criteria.</p>`;
      return;
    }

    // Render first 60 assets for performance
    const displayList = this.filteredAssets.slice(0, 60);

    grid.innerHTML = displayList.map((asset, idx) => {
      const bbox = asset.bounding_box;
      const size = bbox.size || bbox.dimensions || [0, 0, 0];
      const dimsStr = `${size[0].toFixed(1)}m × ${size[1].toFixed(1)}m × ${size[2].toFixed(1)}m`;
      const frontImg = asset.render_paths?.front || `/renders/${asset.name}_front.png`;

      return `
        <div class="catalog-card" data-index="${idx}" title="Click to inspect ${asset.name}">
          <div class="catalog-thumb-wrapper">
            <img class="catalog-thumb" src="${frontImg}" alt="${asset.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
            <div class="catalog-thumb-placeholder" style="display: none;">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
              <span style="font-size: 9px;">3D Model</span>
            </div>
          </div>
          <div class="catalog-card-info">
            <div class="catalog-card-title">${asset.name}</div>
            <div class="catalog-card-role">${asset.placement_role}</div>
            <div class="catalog-card-dims">${dimsStr}</div>
          </div>
        </div>
      `;
    }).join('');

    // Attach card click handlers
    const cards = grid.querySelectorAll('.catalog-card');
    cards.forEach((card) => {
      card.addEventListener('click', () => {
        const idx = parseInt(card.dataset.index, 10);
        const asset = displayList[idx];
        if (asset && this.onInspectAsset) {
          this.onInspectAsset(asset);
        }
      });
    });
  }
}
