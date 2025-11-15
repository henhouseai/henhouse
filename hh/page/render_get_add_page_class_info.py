from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data

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


def render_allowed_classes_section(source_data: Dict[str, Union[str, int, List]], lines: List[str]) -> None:
    trace_in()
    block = 'rows'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.is_no(block):
        page_id = source_data.get('page_id', 0)
        parent_class = source_data.get('parent_class', 'unknown')
        allowed_classes = source_data.get('allowed_classes', [])
        
        log(f"Rendering allowed child classes for page {page_id} (parent_class={parent_class}): {len(allowed_classes)} classes")
        
        # Create table data with header row
        table_data = TableData()
        # Add header row
        table_data.add_row(
            'table_class_header',
            class_name='Class Name',
            allow_null='Allow Null',
            allow_duplicate='Allow Duplicate',
            auto_link='Auto Link'
        )
        # Add data rows
        for class_info in allowed_classes:
            class_name = class_info.get('class_name', 'unknown')
            allow_null = class_info.get('allow_null_names', False)
            allow_duplicate = class_info.get('allow_duplicate_names', True)
            auto_link = class_info.get('auto_link_name', True)
            table_data.add_row(
                'table_class',
                class_name=class_name,
                allow_null='Yes' if allow_null else 'No',
                allow_duplicate='Yes' if allow_duplicate else 'No',
                auto_link='Yes' if auto_link else 'No'
            )
        
        if len(allowed_classes) == 0:
            # Add a message row if no classes are allowed
            table_data.add_row(
                'table_class',
                class_name='(none)',
                allow_null='-',
                allow_duplicate='-',
                auto_link='-'
            )
        
        lines.append(render_block(
            table_data,
            FieldConfig()
                .add_header('table_class_header')
                .add_simple(['table_class']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


@register_http('get_add_page_class_info')
@register_parser('get_add_page_class_info')
def get_add_page_class_info() -> bool:
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
    
    json_data = gateway.response.get_action_response()
    lines = []
    
    # Get source data
    source_data = get_data(json_data)
    page_id = source_data.get('page_id', 0)
    parent_class = source_data.get('parent_class', 'unknown')
    
    # Render header with page info
    header_text = f"Allowed Child Classes for Page {page_id} (Class: {parent_class})"
    lines.append(render_header_block(header_text))
    
    log("Processing get_add_page_class_info data successfully")
    render_allowed_classes_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

