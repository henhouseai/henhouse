"""Tile group base class for rendering groups of tiles."""

from __future__ import annotations

from typing import List

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.html.tiles import Tile

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class TileGroup:
    """Base class for groups of tiles (images, pages, files, etc.)."""
    
    def __init__(self, target_width: int = 300):
        """Initialize an empty tile group.
        
        Args:
            target_width: Target width for tiles (default 300)
        """
        trace_in()
        self.tiles: List[Tile] = []
        self.target_width = target_width
        log(f"Created TileGroup with target_width={target_width}")
        trace_out()
    
    def add_tile(self, tile: Tile) -> None:
        """Add a tile to this group."""
        trace_in()
        self.tiles.append(tile)
        log(f"Added tile to group (total: {len(self.tiles)})")
        trace_out()
    
    def render(self) -> str:
        """Render the tile group as HTML <ul> structure.
        
        Returns:
            HTML string: Wrapped content div with <ul> containing tiles
        """
        trace_in()
        
        if not self.tiles:
            log("No tiles to render")
            trace_out()
            return ""
        
        log(f"Rendering tile group with {len(self.tiles)} tiles")
        html_parts = ['<ul>\n']
        for tile in self.tiles:
            tile_html = tile.render(as_link=True)
            # Tile HTML is already formatted with indentation, just wrap in <li>
            html_parts.append(f'  <li>\n{tile_html}\n  </li>\n')
        html_parts.append('</ul>')
        result = ''.join(html_parts)
        
        # Always call finalize_output hook (overridden by derived classes)
        # This wraps the content in divs with IDs - it doesn't set response
        html_output = self.finalize_output(result)
        
        log(f"Generated tile group HTML for {len(self.tiles)} tiles")
        trace_out()
        return html_output
    
    def finalize_output(self, html_content: str) -> str:
        """Hook for derived classes to process output (e.g., set response, wrap in divs).
        
        Base implementation just returns the HTML as-is.
        Derived classes should override this to set response sections.
        
        Args:
            html_content: The rendered HTML content
        
        Returns:
            HTML string (may be modified by derived classes)
        """
        trace_in()
        log("Base finalize_output called (no-op)")
        trace_out()
        return html_content

