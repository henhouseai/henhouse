import json
from typing import Dict, Any, List, Optional, Union
from hh.tp.tp_decorator_registry import register_tp_decorator
from hh.render.text.color import apply_color, RESET_COLOR
from hh.render.render import TableData, FieldConfig, render_block
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.image.image_size_tiers import IMAGE_SIZE_TIERS

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

@register_tp_decorator('mcp')
def mcp_decorator(json_data: Dict[str, Any], **kwargs: Any) -> str:
    if isinstance(json_data, dict):
        return json.dumps(json_data, indent=2)
    else:
        return str(json_data)


@register_tp_decorator('parser')
def parser_decorator(json_data: Dict[str, Any], **kwargs: Any) -> str:
    if not isinstance(json_data, dict):
        return str(json_data)
    element_type = json_data.get('type', 'unknown')
    if element_type == 'text':
        return json_data.get('content', '')

    table_data = TableData()
    field_config = FieldConfig()
    field_config.add_simple(['page_link', 'image_link_page', 'image_link_image'])
    
    if element_type == 'page_link':
        page = json_data.get('resolved_page', {})
        page_id = page.get('id')
        page_name = page.get('name_override') or page.get('name', 'Unknown')
        cmd = apply_color(f'hen show-page -id {page_id}', 'green')
        field_config.add_header('page_link_header')
        table_data.add_row('page_link_header', name='', command='')
        table_data.add_row('page_link', name=page_name, command=cmd)
        
    elif element_type == 'image_link':
        page = json_data.get('resolved_page', {})
        page_id = page.get('id')
        page_name = page.get('name', 'Unknown')
        image_link = page.get('resolved_image', {})
        image = image_link.get('resolved_image', {}) if isinstance(image_link, dict) else {}
        image_id = image.get('id')
        image_caption = image.get('caption_override') or image.get('caption', '')
        field_config.add_header('image_link_header')
        table_data.add_row('image_link_header', name='', command='')
        table_data.add_row('image_link_page', name=page_name, command=apply_color(f'hen show-page -id {page_id}', 'green'))
        if image_id is not None:
            if image_caption:
                table_data.add_row('image_link_image', name=image_caption, command=apply_color(f'hen show-image -id {image_id}', 'blue'))
            else:
                table_data.add_row('image_link_image', name=f'#{image_id}', command=apply_color(f'hen show-image -id {image_id}', 'blue'))
    
    elif element_type == 'image':
        image = json_data.get('resolved_image', {})
        image_id = image.get('id')
        caption = image.get('caption_override') or image.get('caption', '')
        filename = image.get('filename', 'unknown.jpg')
        cmd = apply_color(f'hen show-image -id {image_id}', 'blue') if image_id is not None else ''
        display_name = caption if caption else filename
        field_config.add_header('image_header')
        table_data.add_row('image_header', name='', command='')
        table_data.add_row('image_link_image', name=display_name, command=cmd)
    
    elif element_type == 'custom':
        field_config.add_header('custom_header')
        fields = [k for k in json_data.keys() if k != 'type']
        # Filter out fields with empty string values
        non_empty_fields = [k for k in fields if str(json_data.get(k, '')) != '']
        if non_empty_fields:
            table_data.add_row('custom_header', value='')
        for field_name, field_value in json_data.items():
            if field_name != 'type':
                # Skip if value is empty string
                if str(field_value) == '':
                    continue
                row_type = f"custom_{field_name}"
                field_config.add_simple([row_type])
                debug(f"field_name: {field_name}, field_value: {field_value} row_type: {row_type}")
                value = apply_color(str(field_value), 'magenta')
                table_data.add_row(row_type, value=value)
    
    else:
        field_config.add_header('unknown_header')
        field_config.add_simple_color('unknown_row', 'magenta')
        
        table_data.add_row('unknown_header', name='', value='')
        table_data.add_row('unknown_row', content=str(json_data))
    
    if table_data.num_rows() > 0:
        return "\n" + render_block(table_data, field_config, table_class='standard', table_overrides={'margin_l': 2}) + "\n"
    else:
        return ''


def _select_image_instance(instances: List[Dict[str, Any]], preferred_size: Any = None, preferred_size_pixels: Optional[int] = None) -> Dict[str, Any]:
    """Select appropriate image instance based on size preferences."""
    if not instances:
        return {}
    
    # If no size preference, return largest
    if preferred_size is None and preferred_size_pixels is None:
        return max(instances, key=lambda x: x.get('width', 0))
    
    # Determine target width
    target_width: Optional[Union[int, float]] = None
    if preferred_size_pixels is not None:
        target_width = preferred_size_pixels
    elif preferred_size == 'fullsize':
        target_width = float('inf')  # Use largest available
    elif preferred_size in IMAGE_SIZE_TIERS:
        target_width = IMAGE_SIZE_TIERS[preferred_size]
    
    if target_width is None:
        # Unknown named size, use largest
        return max(instances, key=lambda x: x.get('width', 0))
    
    # For fullsize, return largest
    if target_width == float('inf'):
        return max(instances, key=lambda x: x.get('width', 0))
    
    # Find smallest instance that is at least as wide as target_width
    suitable = [inst for inst in instances if inst.get('width', 0) >= target_width]
    if suitable:
        return min(suitable, key=lambda x: x.get('width', 0))
    
    # No instance is large enough, use largest available
    return max(instances, key=lambda x: x.get('width', 0))


@register_tp_decorator('http')
def http_decorator(json_data: Dict[str, Any], **kwargs: Any) -> str:
    """HTTP decorator - outputs actual HTML hyperlinks and images for web display."""
    trace_in()
    if not isinstance(json_data, dict):
        trace_out()
        return str(json_data)
    
    element_type = json_data.get('type', 'unknown')
    
    if element_type == 'text':
        result = json_data.get('content', '')
        result = result.replace('\n\n', '<br><br>')
        trace_out()
        return result
    
    if element_type == 'page_link':
        page = json_data.get('resolved_page', {})
        page_id = page.get('id')
        page_name = page.get('name_override') or page.get('name', 'Unknown')
        # Create actual hyperlink using helper
        from hh.render.html.link_helpers import create_page_link
        href = create_page_link(page_id)
        result = f'<a href="{href}">{page_name}</a>'
        trace_out()
        return result
        
    elif element_type == 'image_link':
        page = json_data.get('resolved_page', {})
        page_id = page.get('id')
        image_link = page.get('resolved_image', {})
        image = image_link.get('resolved_image', {}) if isinstance(image_link, dict) else {}
        image_id = image.get('id')
        instances = image.get('instances', [])
        caption = image.get('caption_override') or image.get('caption', '')
        
        # Get size preferences from image metadata
        preferred_size = image.get('_preferred_size')
        preferred_size_pixels = image.get('_preferred_size_pixels')
        
        # Select appropriate instance based on size preferences
        selected_instance = _select_image_instance(instances, preferred_size, preferred_size_pixels)
        img_src = ''
        if selected_instance:
            src_path = selected_instance.get('src', '')
            if src_path:
                # Image URL: /srv/images/{src_path}
                img_src = f'/srv/images/{src_path}'
        
        # Create <a> with <img> inside using helper
        from hh.render.html.link_helpers import create_page_link
        href = create_page_link(page_id)
        alt_text = caption or f'Image {image_id}' if image_id else 'Image'
        if img_src:
            result = f'<a href="{href}"><img src="{img_src}" alt="{alt_text}"></a>'
        else:
            # Fallback if no image src
            page_name = page.get('name', 'Unknown')
            result = f'<a href="{href}">{page_name}</a>'
        trace_out()
        return result
    
    elif element_type == 'image':
        image = json_data.get('resolved_image', {})
        image_id = image.get('id')
        instances = image.get('instances', [])
        caption = image.get('caption_override') or image.get('caption', '')
        
        # Get size preferences from image metadata
        preferred_size = image.get('_preferred_size')
        preferred_size_pixels = image.get('_preferred_size_pixels')
        
        # Select appropriate instance based on size preferences
        selected_instance = _select_image_instance(instances, preferred_size, preferred_size_pixels)
        img_src = ''
        if selected_instance:
            src_path = selected_instance.get('src', '')
            if src_path:
                # Image URL: /srv/images/{src_path}
                img_src = f'/srv/images/{src_path}'
        
        # Create actual <img> tag
        alt_text = caption or f'Image {image_id}' if image_id else 'Image'
        if img_src:
            result = f'<img src="{img_src}" alt="{alt_text}">'
        else:
            result = f'<span>Image {image_id}</span>' if image_id else '<span>Image</span>'
        trace_out()
        return result
    
    elif element_type == 'custom':
        # Passthru value directly (can be empty string or anything)
        result = str(json_data.get('value', ''))
        trace_out()
        return result
    
    else:
        result = str(json_data)
        trace_out()
        return result