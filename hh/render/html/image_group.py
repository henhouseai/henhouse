"""Image group rendering functions for table and tile views."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.html.tiles import render_image_tile_link
from hh.render.render import FieldConfig, TableData, render_block
from hh.render.config.config import safe_str

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


def render_image_group_html(
    images_data: List[Dict[str, Any]], page_id: int, view_type: Optional[str] = None
) -> str:
    """Render image group HTML in either table or tile format.
    
    Args:
        images_data: List of image data dicts with 'id', 'caption', 'instances', 'image_rank'
        page_id: Page ID for generating unique element IDs
        view_type: 'table' or 'tile' (defaults based on backend: HTTP=tile, parser=table)
    
    Returns:
        HTML string for the image group section
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    
    # Determine view_type if not provided
    if not view_type:
        # Default: HTTP backend = tile for images, parser = table
        if gateway.backend == "http":
            view_type = "tile"
        else:
            view_type = "table"
    
    # Check URL override flag
    if gateway.request.is_set("image_table"):
        view_type = "table"
    
    if not images_data:
        log("No images data provided")
        trace_out()
        return ""
    
    page_id_str = str(page_id)
    header_id = f"pageImageGroupHeader_{page_id_str}"
    content_id = f"pageImageGroup_{page_id_str}"
    
    if view_type == "tile":
        # Render as tiles
        log(f"Rendering {len(images_data)} images as tiles for page {page_id}")
        opposite_view = "table"
        header_html = f'<div id="{header_id}" class="contentHeader"><a class="updatePageView_{page_id_str}" data-section="images" data-view-type="{opposite_view}">IMAGES</a></div>'
        
        content_html = f'<div id="{content_id}" class="content pageImageGroup"><ul>'
        for image in images_data:
            tile_html = render_image_tile_link(image, target_width=300)
            content_html += f"<li>{tile_html}</li>"
        content_html += "</ul></div><div class=\"clearboth\"></div>"
        
        result = header_html + content_html
        log(f"Generated tile HTML for {len(images_data)} images")
        trace_out()
        return result
    else:
        # Render as table
        log(f"Rendering {len(images_data)} images as table for page {page_id}")
        page_id_str = str(page_id)
        header_id = f"pageImageGroupHeader_{page_id_str}"
        content_id = f"pageImageGroup_{page_id_str}"
        opposite_view = "tile"
        header_html = f'<div id="{header_id}" class="contentHeader"><a class="updatePageView_{page_id_str}" data-section="images" data-view-type="{opposite_view}">IMAGES</a></div>'
        
        images_rows = TableData()
        images_rows.add_row(
            'images_header',
            label='Images',
            rank='Rank',
            id='ID',
            caption='Caption',
            uploaded='Uploaded',
            instances='Instances'
        )
        for image in images_data:
            image_id = image.get('id')
            instances_count = len(image.get('instances', []))
            images_rows.add_row(
                'image_item',
                rank=str(image.get('image_rank', 'N/A')),
                id=str(image_id) if image_id is not None else 'N/A',
                caption=safe_str(image.get('caption', 'untitled')),
                uploaded=safe_str(image.get('uploaded', 'N/A')),
                instances=str(instances_count)
            )
            if image_id is not None:
                images_rows.add_image_link_to_column('label', image_id)
                images_rows.add_image_link_to_column('rank', image_id)
                images_rows.add_image_link_to_column('id', image_id)
                images_rows.add_image_link_to_column('caption', image_id)
        
        if images_rows.num_rows() > 0:
            images_block = render_block(
                images_rows,
                FieldConfig()
                    .add_header('images_header')
                    .add_simple(['image_item']),
                table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},
                block_type='images',
                table_id='image_group',
                backend='http'
            )
            # Wrap table in content div with unique ID
            content_html = f'<div id="{content_id}" class="content pageImageGroup">{images_block}</div>'
            result = header_html + content_html
            log(f"Generated table HTML for {len(images_data)} images")
            trace_out()
            return result
        log("No images to render")
        trace_out()
        return ""

