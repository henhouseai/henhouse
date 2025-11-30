from __future__ import annotations
from typing import Optional, Dict, Any

from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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


class Tile:
    """Represents a single tile with image, text, link, and metadata."""
    
    def __init__(
        self,
        image: Optional[Dict[str, Any]] = None,
        text: str = "",
        link: str = "#",
        metadata: Optional[Dict[str, Any]] = None,
        target_width: int = 300
    ):
        """Initialize a tile.
        
        Args:
            image: Dict with 'instances' list (all image sizes), can be None/empty
            text: Display text/caption for the tile
            link: URL href for the tile link
            metadata: Optional dict for extra data (JS actions, onClick IDs, etc.)
            target_width: Target width for tile rendering (default 300)
        """
        trace_in()
        self.image = image or {}
        self.text = text
        self.link = link
        self.metadata = metadata or {}
        self.target_width = target_width
        log(f"Created tile: text='{text}', link='{link}', has_image={bool(self.image.get('instances'))}")
        trace_out()
    
    def _find_best_image_instance(self) -> Optional[Dict[str, Any]]:
        """Find the best image instance for the target width."""
        trace_in()
        instances = self.image.get('instances', [])
        if not instances:
            trace_out()
            return None
        
        target_width = self.target_width
        best_instance = None
        
        # Find smallest instance that's >= target_width
        for instance in instances:
            width = instance.get('width', 0)
            if width >= target_width:
                if best_instance is None or width < best_instance.get('width', 0):
                    best_instance = instance
        
        # If no instance is large enough, use largest available
        if best_instance is None:
            best_instance = max(instances, key=lambda x: x.get('width', 0))
        
        log(f"Selected image instance: width={best_instance.get('width') if best_instance else 'N/A'}")
        trace_out()
        return best_instance
    
    def _render_image_html(self) -> str:
        """Render the image HTML for this tile."""
        trace_in()
        best_instance = self._find_best_image_instance()
        
        if best_instance and best_instance.get('src'):
            src_path = best_instance['src']
            img_src = f'/srv/images/{src_path}'
            alt_text = self.text or ""
            # Format with proper indentation (8 spaces for content inside <div class="tileWrapper">)
            img_html = f'        <img src="{img_src}" alt="{alt_text}">\n'
        else:
            # Empty image - create div to maintain width (CSS handles width)
            img_html = f'        <div class="emptyTileImage"></div>\n'
        
        trace_out()
        return img_html
    
    def render(self, as_link: bool = True, link_id: Optional[str] = None) -> str:
        """Render the tile as HTML.
        
        Args:
            as_link: If True, wrap in <a> tag, otherwise just render tile div
            link_id: Optional ID for link (if provided, no href attribute)
        
        Returns:
            HTML string for the tile
        """
        trace_in()
        img_html = self._render_image_html()
        caption_html = self.text if self.text else ""
        
        # Render tile wrapper
        classes = ["tileWrapper"]
        if self.metadata.get('extra_class'):
            classes.append(self.metadata['extra_class'])
        class_attr = " ".join(classes)
        tile_text_class = "tileText" + (" emptyTileText" if not caption_html else "")
        
        # Format tile HTML with proper indentation (for use inside <li>)
        # <li> is at 2 spaces, <a> at 4 spaces, <div> at 6 spaces, content at 8 spaces
        tile_html = (
            f'      <div class="{class_attr}">\n'
            f'{img_html}'
            f'        <div class="{tile_text_class}">{caption_html}</div>\n'
            f'      </div>'
        )
        
        # Wrap in link if requested
        if as_link:
            if link_id:
                a_attrs = f'id="{link_id}"'
            else:
                a_attrs = f'href="{self.link}"'
            result = f'    <a class="tileLink" {a_attrs}>\n{tile_html}\n    </a>'
        else:
            result = tile_html
        
        log(f"Rendered tile (width: {self.target_width}, as_link: {as_link})")
        trace_out()
        return result


def render_tile(img_html: str, target_width: int, caption_html: str = "", extra_class: str = "") -> str:
    """Legacy utility function for rendering a tile from pre-built HTML components."""
    trace_in()
    classes = ["tileWrapper"]
    if extra_class:
        classes.append(extra_class)
    class_attr = " ".join(classes)
    tile_text_class = "tileText" + (" emptyTileText" if len(caption_html) == 0 else "")
    result = (
        f"<div class=\"{class_attr}\">"
        f"{img_html}"
        f"<div class=\"{tile_text_class}\" style=\"width: {int(target_width)}px;\">{caption_html}</div>"
        f"</div>"
    )
    log(f"Rendered tile (width: {target_width}, has_caption: {bool(caption_html)})")
    trace_out()
    return result


def render_tile_link(href: str, img_html: str, target_width: int, caption_html: str = "", extra_class: str = "", link_id: Optional[str] = None) -> str:
    """Legacy utility function for rendering a tile link from pre-built HTML components."""
    trace_in()
    a_attrs = (
        f'id="{link_id}"' if link_id else f'href="{href}"'
    )
    result = f"<a class=\"tileLink\" {a_attrs}>{render_tile(img_html, target_width, caption_html, extra_class)}</a>"
    log(f"Rendered tile link (href: {href}, width: {target_width})")
    trace_out()
    return result


