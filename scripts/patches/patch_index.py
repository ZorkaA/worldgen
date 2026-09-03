import re

with open("frontend/index.html", "r") as f:
    content = f.read()

replacement = """          <button type="button" class="btn-tool" id="btn-toggle-wireframe" title="Toggle Terrain Wireframe Mode (Shortcut: W)">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"/><path d="M4 12h16M12 4v16"/></svg>
          </button>
          <button type="button" class="btn-tool active" id="btn-toggle-zones" title="Toggle Zones Visibility">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>
            <span>Zones</span>
          </button>
          <button type="button" class="btn-tool active" id="btn-toggle-assets" title="Toggle Assets Visibility">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/></svg>
            <span>Assets</span>
          </button>"""

content = content.replace("""          <button type="button" class="btn-tool" id="btn-toggle-wireframe" title="Toggle Terrain Wireframe Mode (Shortcut: W)">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"/><path d="M4 12h16M12 4v16"/></svg>
            <span>Wireframe</span>
          </button>""", replacement)

with open("frontend/index.html", "w") as f:
    f.write(content)
