from __future__ import annotations
import json
from typing import Dict, List, Union, TypedDict
from hh.render.config.config import ic, dc, out, mc, safe_str
from hh.render.table.table import TableBuilder
from hh.render.text.text import get_max_width
from hh.gateway.gateway import get_gateway
from hh.render.text.color import apply_color
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
# Import shared data structures from render module
from hh.render.render import TableData, FieldConfig

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

def render_flexible_table(table_data: TableData, table_id: str, field_configs: FieldConfig = None, table_class: str = 'standard', table_overrides: Dict[str, Union[str, int, bool]] = None) -> str:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    data = table_data.get_rows()
    if not isinstance(data, list) or not data:
        log("No data to render in flexible table")
        trace_out()
        return ""
    log(f"Rendering flexible table: {len(data)} rows, table_class={table_class}")
    if field_configs is None:
        field_configs = FieldConfig()
    else:
        field_configs = field_configs.get_configs()
    columns = []
    if data:
        first_row_keys = list(data[0].keys())
        for key in first_row_keys:
            if key != 'field_type':
                columns.append(key)
        log(f"Identified columns: {columns}")
    # Remove label column entirely if is_no('label') is true
    if gateway.is_no('label') and columns:
        columns = columns[1:]
        log(f"Label column removed, remaining columns: {columns}")
    if not columns:
        log("No columns found, returning empty")
        trace_out()
        return ""
    tb = TableBuilder(table_class, table_id)
    tb.set_columns(','.join(columns))
    if len(columns) > 1:
        final_column = columns[-1]
        tb.set_column_width(final_column, mc('config_trim_width'))
        tb.set_column_overflow(final_column, 'wrap')
        log(f"Set final column '{final_column}' width and overflow")
    if table_overrides:
        tb.apply_overrides(table_overrides)
        log(f"Applied table overrides: {table_overrides}")
    for row_idx, row_data in enumerate(data):
        matching_field_config = None
        if field_configs:
            for field_config in field_configs:
                if row_data.get('field_type') == field_config.get('field_type'):
                    matching_field_config = field_config
                    break
        if not matching_field_config:
            row_values = []
            for col in columns:
                row_values.append("")
            for i, col in enumerate(columns):
                if col in row_data:
                    row_values[i] = out(safe_str(row_data[col]))
            tb.row(keys=columns, values=row_values)
            continue
        if matching_field_config.get('no_flag') and gateway.is_no(matching_field_config['no_flag']):
            continue
        if matching_field_config.get('condition') and not matching_field_config['condition'](row_data):
            continue
        row_values = []
        for col in columns:
            row_values.append("")
        
        # Only process label content if label column wasn't removed
        if not gateway.is_no('label'):
            icon = ""
            label_text = ""
            if matching_field_config.get('icon_key'):
                icon = ic(matching_field_config['icon_key'])
            if matching_field_config.get('label_key'):
                label_text = dc(matching_field_config['label_key'], True)
                
                # Apply color wrapping to label_text if color_key is specified
                if matching_field_config.get('color_key') and label_text:
                    color_name = matching_field_config['color_key']
                    label_text = apply_color(label_text, color_name)
            
            if 'label' in row_data and row_data['label'] != '':
                first_column_content = row_data['label']
            else:
                first_column_content = icon + label_text
            row_values[0] = first_column_content
        
        # Process all remaining columns
        start_idx = 1 if not gateway.is_no('label') else 0
        for i, col in enumerate(columns[start_idx:], start_idx):
            if col in row_data:
                row_values[i] = out(safe_str(row_data[col]))
        tb.row(keys=columns, values=row_values)
    result = tb.render()
    log(f"Rendered flexible table with {len(data)} rows")
    trace_out()
    return result

def render_meta_table(
    table_data: TableData, 
    table_id: str,
    field_configs: FieldConfig = None, 
    table_class: str = 'div', 
    table_overrides: Dict[str, Union[str, int, bool]] = None,
    block_type: str = 'div'
) -> str:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    log(f"Rendering meta table: table_class={table_class}")
    t_class_arg = gateway.get_arg('t_class')
    if t_class_arg and t_class_arg != '':
        table_class = t_class_arg
    try:
        meta_data = table_data.get_rows()
        meta_obj = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
        log(f"Parsed meta object: {type(meta_obj)}")
        if not isinstance(meta_obj, dict):
            return ""
        meta_table_data = TableData()
        meta_table_data.add_row('meta_header', key='', value='')
        max_sub_meta_width = mc('config_trim_width')
        nested_overrides = table_overrides.copy() if table_overrides else {}
        nested_overrides.pop('margin_l', None)
        nested_overrides.pop('margin_r', None)
        nested_overrides.pop('margin_t', None)
        nested_overrides.pop('margin_b', None)
        for key, value in meta_obj.items():
            if isinstance(value, dict):
                nested_content = render_dict_contents(value, table_id, field_configs, table_class, nested_overrides, block_type)
                width = get_max_width(nested_content)
                if width > max_sub_meta_width:
                    max_sub_meta_width = width
            elif isinstance(value, list):
                nested_content = render_list_contents(value, table_id, field_configs, table_class, nested_overrides, block_type)
                width = get_max_width(nested_content)
                if width > max_sub_meta_width:
                    max_sub_meta_width = width
            else:
                nested_content = render_simple_value(value)
            meta_table_data.add_row('meta', key=key, value=nested_content)
        modified_overrides = table_overrides.copy() if table_overrides else {}
        modified_overrides['column_widths'] = {'value': max_sub_meta_width}
        modified_overrides['column_align'] = {'label': 'right', 'key': 'center'}
        from hh.render.render import render_block
        result = render_block(meta_table_data, field_configs, 'double', modified_overrides, 'div', table_id=table_id)
        log(f"Rendered meta table with {meta_table_data.num_rows()} rows")
        trace_out()
        return result
    except Exception as e:
        warn(f"render_meta_table metadata parsing error: {e}")
        trace_out()
        return ""

def _count_nodes_and_depth(data: Union[Dict, List, str, int, bool]) -> tuple[int, int, int]:
    if isinstance(data, dict):
        direct_children = len(data)
        total_nodes = 0
        max_depth = 0
        for value in data.values():
            child_direct, child_total, child_depth = _count_nodes_and_depth(value)
            total_nodes += child_total
            max_depth = max(max_depth, child_depth)
        return direct_children, total_nodes + direct_children, max_depth + 1
    elif isinstance(data, list):
        direct_children = len(data)
        total_nodes = 0
        max_depth = 0
        for item in data:
            child_direct, child_total, child_depth = _count_nodes_and_depth(item)
            total_nodes += child_total
            max_depth = max(max_depth, child_depth)
        return direct_children, total_nodes + direct_children, max_depth + 1
    else:
        return 0, 1, 1

def render_simple_value(value: Union[str, int, bool, None]) -> str:
    trace_in()
    result = safe_str(value)
    log(f"Rendered simple value: {type(value)} -> {len(result)} chars")
    trace_out()
    return result

def render_list_contents(
    value_list: List[Union[Dict, List, str, int, bool]], 
    table_id: str,
    field_configs: FieldConfig = None, 
    table_class: str = 'div',
    table_overrides: Dict[str, Union[str, int, bool]] = None,
    block_type: str = 'div'
) -> str:
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        return ""
    if not value_list:
        return ""
    if gateway.is_no('sub_meta'):
        direct_children, total_nodes, max_depth = _count_nodes_and_depth(value_list)
        return f"sub_meta summary {direct_children}/{total_nodes} nodes, max depth = {max_depth}"
    list_table_data = TableData()
    max_sub_meta_width = mc('config_trim_width')
    for item in value_list:
        if isinstance(item, dict):
            nested_content = render_dict_contents(item, table_id, field_configs, table_class, table_overrides, block_type)
            width = get_max_width(nested_content)
            if width > max_sub_meta_width:
                max_sub_meta_width = width
        elif isinstance(item, list):
            nested_content = render_list_contents(item, table_id, field_configs, table_class, table_overrides, block_type)
            width = get_max_width(nested_content)
            if width > max_sub_meta_width:
                max_sub_meta_width = width
        else:
            nested_content = render_simple_value(item)
        list_table_data.add_row('meta', value=nested_content)
    sub_meta_overrides = {'has_header': 0, 'column_widths': {'value': max_sub_meta_width}}
    if table_overrides:
        sub_meta_overrides.update(table_overrides)
    from hh.render.render import render_block
    return render_block(list_table_data, field_configs, table_class, sub_meta_overrides, block_type, table_id=table_id)

def render_dict_contents(
    value_dict: Dict[str, Union[Dict, List, str, int, bool]], 
    table_id: str,
    field_configs: FieldConfig = None, 
    table_class: str = 'div',
    table_overrides: Dict[str, Union[str, int, bool]] = None,
    block_type: str = 'div'
) -> str:
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        return ""
    if not value_dict:
        return ""
    if gateway.is_no('sub_meta'):
        direct_children, total_nodes, max_depth = _count_nodes_and_depth(value_dict)
        return f"sub_meta summary {direct_children}/{total_nodes} nodes, max depth = {max_depth}"
    dict_table_data = TableData()
    max_sub_meta_width = mc('config_trim_width')
    for key, value in value_dict.items():
        if isinstance(value, dict):
            nested_content = render_dict_contents(value, table_id, field_configs, table_class, table_overrides, block_type)
            width = get_max_width(nested_content)
            if width > max_sub_meta_width:
                max_sub_meta_width = width
        elif isinstance(value, list):
            nested_content = render_list_contents(value, table_id, field_configs, table_class, table_overrides, block_type)
            width = get_max_width(nested_content)
            if width > max_sub_meta_width:
                max_sub_meta_width = width
        else:
            nested_content = render_simple_value(value)
        dict_table_data.add_row('meta', key=key, value=nested_content)
    sub_meta_overrides = {'has_header': 0, 'column_widths': {'value': max_sub_meta_width}}
    if table_overrides:
        sub_meta_overrides.update(table_overrides)
    from hh.render.render import render_block
    return render_block(dict_table_data, field_configs, table_class, sub_meta_overrides, block_type, table_id=table_id)


def render_parser_header(subheader_key: str, header_id: str) -> str:
    """Parser/CLI renderer - renders headers as plain text for CLI output."""
    trace_in()
    from hh.render.config.config import dc, break_section
    from hh.render.render import finalize_output
    
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    
    log("Parser backend detected - using CLI header renderer")
    
    # Determine headers (no longer stored as response metadata; seeds are used instead)
    main_header = None
    sub_header = None
    if not gateway.is_no('main_header'):
        main_header = dc('l_main_header', True)
    if subheader_key and not gateway.is_no('sub_header'):
        sub_header = dc(subheader_key, True)
    
    # Generate rendered output for backward compatibility (direct injection into lines)
    lines = []
    header_parts = []
    if main_header:
        header_parts.append(main_header)
        log(f"Added main header: {main_header}")
    if sub_header:
        header_parts.append(sub_header)
        log(f"Added sub header: {sub_header}")
    if header_parts:
        lines.append("\n")
        lines.append("".join(header_parts))
        break_section(lines)
        log(f"Generated header with {len(header_parts)} parts (header_id={header_id} stored but not used)")
    else:
        log("No header parts generated")
    result = finalize_output(lines)
    trace_out()
    return result
