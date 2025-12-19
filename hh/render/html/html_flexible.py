from __future__ import annotations
from typing import Dict, Union, Optional
from hh.render.html.html_table import HtmlTableBuilder
from hh.render.html.link_helpers import create_page_link, create_image_link, create_image_file_link, create_file_link
from hh.render.render import TableData, FieldConfig
from hh.render.config.config import ic, dc, out, safe_str
from hh.render.text.color import apply_color
from hh.gateway.gateway import get_gateway
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

def render_html_flexible_table(
    table_data: TableData, 
    field_configs: Optional[FieldConfig] = None, 
    table_class: str = 'standard', 
    table_overrides: Optional[Dict[str, Union[str, int, bool]]] = None,
    wrapper_id: Optional[str] = None,
    wrapper_extra_classes: Optional[str] = None
) -> str:
    """Render table data as HTML - mirrors render_flexible_table() but uses HtmlTableBuilder."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    
    data = table_data.get_rows()
    if not isinstance(data, list) or not data:
        log("No data to render in HTML flexible table")
        trace_out()
        return ""
    
    log(f"Rendering HTML flexible table: {len(data)} rows, table_class={table_class}")
    
    if field_configs is None:
        field_configs_obj = FieldConfig()
    else:
        field_configs_obj = field_configs
    field_config_list = field_configs_obj.get_configs()
    
    # Extract columns from first row
    columns = []
    if data:
        first_row_keys = list(data[0].keys())
        for key in first_row_keys:
            if key != 'field_type':
                columns.append(key)
        log(f"Identified columns: {columns}")
    
    # Remove label column if is_no('label')
    if gateway.is_no('label') and columns:
        columns = columns[1:]
        log(f"Label column removed, remaining columns: {columns}")
    
    if not columns:
        log("No columns found, returning empty")
        trace_out()
        return ""
    
    # Create HTML table builder with wrapper configuration
    tb = HtmlTableBuilder(table_class, wrapper_id=wrapper_id, wrapper_extra_classes=wrapper_extra_classes)
    tb.set_columns(','.join(columns))
    
    # Set final column width/overflow if multiple columns (stored for future, not used in Phase 1)
    if len(columns) > 1:
        from hh.render.config.config import mc
        final_column = columns[-1]
        tb.set_column_width(final_column, mc('config_trim_width'))
        tb.set_column_overflow(final_column, 'wrap')
        log(f"Set final column '{final_column}' width and overflow")
    
    # Apply table overrides
    if table_overrides:
        tb.apply_overrides(table_overrides)
        log(f"Applied table overrides: {table_overrides}")
    
    # Process each row
    for row_idx, row_data in enumerate(data):
        matching_field_config = None
        
        # Find matching field config
        if field_config_list:
            for field_config_item in field_config_list:
                if isinstance(field_config_item, dict):
                    field_type = field_config_item.get('field_type')  # type: ignore[typeddict-item]
                    if row_data.get('field_type') == field_type:
                        matching_field_config = field_config_item
                        break
        
        # Handle rows without field config
        if not matching_field_config:
            row_values = []
            for col in columns:
                row_values.append("")
            
            # Check for link metadata
            links = row_data.get('_links', {})  # type: ignore[typeddict-item]
            
            for i, col in enumerate(columns):
                if col in row_data:
                    cell_content = out(safe_str(row_data[col]))  # type: ignore[typeddict-item,literal-required]
                    
                    # Wrap with link if metadata present
                    if isinstance(links, dict) and col in links:
                        link_info = links[col]
                        link_type = link_info.get('type')
                        link_id = link_info.get('id')
                        src_path = link_info.get('src_path')
                        
                        if link_type == 'page' and link_id is not None:
                            href = create_page_link(link_id)
                            cell_content = f'<a href="{href}">{cell_content}</a>'
                        elif link_type == 'image' and link_id is not None:
                            href = create_image_link(link_id)
                            cell_content = f'<a href="{href}">{cell_content}</a>'
                        elif link_type == 'file' and link_id is not None:
                            href = create_file_link(file_id=link_id)
                            cell_content = f'<a href="{href}">{cell_content}</a>'
                    
                    row_values[i] = cell_content
            tb.row(keys=columns, values=row_values)
            continue
        
        # Check no_flag
        if matching_field_config and isinstance(matching_field_config, dict):
            no_flag = matching_field_config.get('no_flag')  # type: ignore[typeddict-item]
            if no_flag and gateway.is_no(no_flag):
                continue
            
            # Check condition
            condition = matching_field_config.get('condition')  # type: ignore[typeddict-item]
            if condition and callable(condition) and not condition(row_data):
                continue
        
        # Build row values
        row_values = []
        for col in columns:
            row_values.append("")
        
        # Process label column if not disabled
        if not gateway.is_no('label'):
            icon = ""
            label_text = ""
            if matching_field_config and isinstance(matching_field_config, dict):
                icon_key = matching_field_config.get('icon_key')  # type: ignore[typeddict-item]
                if icon_key:
                    icon = ic(icon_key)
                label_key = matching_field_config.get('label_key')  # type: ignore[typeddict-item]
                if label_key:
                    label_text = dc(label_key, True)
                    
                    # Apply color wrapping to label_text if color_key is specified
                    color_key = matching_field_config.get('color_key')  # type: ignore[typeddict-item]
                    if color_key and label_text:
                        label_text = apply_color(label_text, color_key)
            
            if 'label' in row_data and row_data['label'] != '':
                first_column_content = row_data['label']
            else:
                first_column_content = f"{icon}{label_text}".strip()
            
            if first_column_content:
                cell_content = out(safe_str(first_column_content))
                
                # Check for link metadata on label column and wrap if present
                links = row_data.get('_links', {})  # type: ignore[typeddict-item]
                if isinstance(links, dict) and 'label' in links:
                    link_info = links['label']
                    link_type = link_info.get('type')
                    link_id = link_info.get('id')
                    src_path = link_info.get('src_path')
                    
                    if link_type == 'page' and link_id is not None:
                        href = create_page_link(link_id)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                    elif link_type == 'image' and link_id is not None:
                        href = create_image_link(link_id)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                    elif link_type == 'image_file' and src_path:
                        href = create_image_file_link(src_path)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                    elif link_type == 'file' and link_id is not None:
                        href = create_file_link(file_id=link_id)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                
                row_values[0] = cell_content
        
        # Process all remaining columns
        start_idx = 1 if not gateway.is_no('label') else 0
        for i, col in enumerate(columns[start_idx:], start_idx):
            if col in row_data:
                cell_content = out(safe_str(row_data[col]))  # type: ignore[typeddict-item,literal-required]
                
                # Check for link metadata and wrap if present
                links = row_data.get('_links', {})  # type: ignore[typeddict-item]
                if isinstance(links, dict) and col in links:
                    link_info = links[col]
                    link_type = link_info.get('type')
                    link_id = link_info.get('id')
                    src_path = link_info.get('src_path')
                    
                    if link_type == 'page' and link_id is not None:
                        href = create_page_link(link_id)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                    elif link_type == 'image' and link_id is not None:
                        href = create_image_link(link_id)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                    elif link_type == 'image_file' and src_path:
                        href = create_image_file_link(src_path)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                    elif link_type == 'file' and link_id is not None:
                        href = create_file_link(file_id=link_id)
                        cell_content = f'<a href="{href}">{cell_content}</a>'
                
                row_values[i] = cell_content
        
        tb.row(keys=columns, values=row_values)
    
    # Render HTML table
    result = tb.render()
    log(f"Rendered HTML flexible table with {len(data)} rows")
    trace_out()
    return result

