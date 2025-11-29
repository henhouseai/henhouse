from __future__ import annotations
from typing import Dict, List, Any, Optional
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.render.render import render_block, TableData, FieldConfig
from hh.render.config.config import safe_str
from hh.render.html.tiles import render_image_tile_link

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


def render_images_section_html(images_data: List[Dict[str, Any]], page_id: int, view_type: str = 'table') -> str:
    """
    Render images section as HTML string.
    
    Args:
        images_data: List of image data dicts
        page_id: Page ID for generating unique IDs
        view_type: 'table' or 'tile'
    
    Returns:
        HTML string for the images section
    """
    trace_in()
    if not images_data:
        trace_out()
        return ''
    
    log(f"Rendering images section with {len(images_data)} images in {view_type} mode")
    
    if view_type == 'tile':
        # Render as tiles
        header_id = f'pageImageGroupHeader_{page_id}'
        content_id = f'pageImageGroup_{page_id}'
        
        # Determine opposite view type for toggle
        opposite_view = 'table'
        
        # Build header with toggle link
        header_html = f'<div id="{header_id}" class="contentHeader">'
        header_html += f'<a class="updatePageView_{page_id}" data-section="images" data-view-type="{opposite_view}">IMAGES</a>'
        header_html += '</div>'
        
        # Build tile list
        tile_list_items = []
        for image in images_data:
            tile_html = render_image_tile_link(image, target_width=300, link_id_prefix='imageGroup')
            tile_list_items.append(f'<li>{tile_html}</li>')
        
        content_html = f'<div id="{content_id}" class="content pageImageGroup">'
        content_html += '<ul>'
        content_html += ''.join(tile_list_items)
        content_html += '</ul></div>'
        content_html += '<div class="clearboth"></div>'
        
        result = header_html + content_html
    else:
        # Render as table (default)
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
            result = render_block(
                images_rows,
                FieldConfig()
                    .add_header('images_header')
                    .add_simple(['image_item']),
                table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},
                block_type='images',
                table_id='image_group'
            )
        else:
            result = ''
    
    trace_out()
    return result


@register_action('get_page_section')
@register_command('get_page_section')
def get_page_section_action() -> bool:
    """Return HTML snippet for a specific page section."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Validate required parameters
    if not gateway.is_set('id'):
        warn("No page id provided")
        report_error("action", "Page ID is required")
    if not gateway.is_set('section'):
        warn("No section provided")
        report_error("action", "Section is required (e.g., 'images', 'children', 'files')")
    
    if not is_error():
        page_id = gateway.get_arg('id')
        section = gateway.get_arg('section')
        view_type = gateway.get_arg('view_type') or None
        
        log(f"Getting page section: page_id={page_id}, section={section}, view_type={view_type}")
        
        try:
            page_id = int(page_id)
        except ValueError:
            warn(f"Invalid page ID: {page_id}")
            report_error("action", "Page ID must be a number")
        
        if not is_error():
            page_obj = get_page(page_id=page_id)
            if not page_obj:
                warn(f"Page {page_id} not found")
                report_error("action", f"Page {page_id} not found")
    
    if not is_error():
        # Determine view type
        if view_type is None:
            # Check URL flag for image_table override
            if section == 'images' and gateway.request.is_set('image_table'):
                view_type = 'table'
            elif section == 'images' and gateway.backend == 'http':
                view_type = 'tile'  # Default to tile for HTTP backend
            else:
                view_type = 'table'  # Default to table for parser backend
        
        # Get section data
        html_output = ''
        if section == 'images':
            images_data = page_obj.get_images_data()
            html_output = render_images_section_html(images_data, page_id, view_type)
        elif section == 'children':
            # TODO: Implement children section rendering
            warn("Children section not yet implemented")
            report_error("action", "Children section not yet implemented")
        elif section == 'files':
            # TODO: Implement files section rendering
            warn("Files section not yet implemented")
            report_error("action", "Files section not yet implemented")
        else:
            warn(f"Unknown section: {section}")
            report_error("action", f"Unknown section: {section}")
        
        if not is_error():
            # Return HTML in action response
            response_data = {'dom_content': html_output}
            gateway.response.set_action_response(success_payload(response_data))
            log(f"Successfully returned {section} section HTML")
    
    trace_out()
    return not is_error()


@register_parser('get_page_section')
def get_page_section_parser() -> bool:
    """Parser backend for get_page_section - returns table with metadata and HTML."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    try:
        from hh.gateway.response.json_standard import get_data
        from hh.render.render import render_header_block, finalize_output
        from hh.render.config.config import break_section
        
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data)
        
        # Extract data from action response
        dom_content = source_data.get('dom_content', '')
        
        # Get page info from action response or re-fetch if needed
        # The action should have set this, but we need page metadata for the table
        page_id = gateway.get_arg('id')
        section = gateway.get_arg('section')
        view_type = gateway.get_arg('view_type') or 'table'
        
        try:
            page_id = int(page_id)
        except (ValueError, TypeError):
            page_id = None
        
        # If we have page_id, get page object for metadata
        page_obj = None
        if page_id:
            page_obj = get_page(page_id=page_id)
        
        lines = []
        lines.append(render_header_block('get_page_section_header'))
        
        # Create table with metadata rows (vertical table format: label/value pairs)
        result_rows = TableData()
        result_rows.add_row('get_page_section_header', label='Field', value='Value')
        
        if page_obj:
            result_rows.add_row('get_page_section_page_id', label='Page ID', value=str(page_id))
            result_rows.add_row('get_page_section_page_name', label='Page Name', value=safe_str(page_obj.name or 'N/A'))
            result_rows.add_row('get_page_section_parent', label='Parent', value=str(page_obj.parent) if page_obj.parent else 'N/A')
            result_rows.add_row('get_page_section_class', label='Class', value=safe_str(page_obj.class_name or 'N/A'))
        else:
            result_rows.add_row('get_page_section_page_id', label='Page ID', value=str(page_id) if page_id else 'N/A')
            result_rows.add_row('get_page_section_page_name', label='Page Name', value='N/A')
            result_rows.add_row('get_page_section_parent', label='Parent', value='N/A')
            result_rows.add_row('get_page_section_class', label='Class', value='N/A')
        
        result_rows.add_row('get_page_section_section', label='Section', value=safe_str(section))
        result_rows.add_row('get_page_section_view_type', label='View Type', value=safe_str(view_type))
        result_rows.add_row('get_page_section_dom_content', label='DOM Content', value=dom_content)
        
        if result_rows.num_rows() > 0:
            result_block = render_block(
                result_rows,
                FieldConfig()
                    .add_header('get_page_section_header')
                    .add_simple([
                        'get_page_section_page_id',
                        'get_page_section_page_name',
                        'get_page_section_parent',
                        'get_page_section_class',
                        'get_page_section_section',
                        'get_page_section_view_type',
                        'get_page_section_dom_content'
                    ]),
                table_overrides={'margin_l': 2},
                block_type='get_page_section',
                table_id='get_page_section_result'
            )
            lines.append(result_block)
        
        break_section(lines)
        result = finalize_output(lines)
        gateway.response.add_output(result)
        log("Successfully rendered parser output")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Parser execution raised an exception: {e}")
        report_error("backend", f"Parser execution raised an exception: {e}")
        trace_out()
        return False

