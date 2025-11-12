from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser, register_http, register_mcp
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import get_errors
from hh.render.text.color import get_color, apply_color_code, RESET_COLOR

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

def render_error_details(error_list: List[Dict], error_type: str, lines: List[str]) -> None:
    trace_in()
    if not error_list:
        trace_out()
        return
    block = 'error'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        log(f"Rendering {len(error_list)} {error_type} errors")
        error_color = None
        field_config = FieldConfig()
        field_config.add_header('error_header')
        field_config.add_simple_color('action_error', 'red')
        field_config.add_simple_color('backend_error', 'red')
        field_config.add_simple_color('request_error', 'red')
        field_config.add_simple_color('registry_error', 'red')
        field_config.add_simple_color('connection_error', 'red')
        field_config.add_simple_color('json_error', 'red')
        field_config.add_simple_color('syntax_error', 'red')
        for config_item in field_config.get_configs():
            if config_item['field_type'] == f'{error_type}_error' and 'color_key' in config_item:
                color_key = config_item['color_key']
                error_color = get_color(color_key)
                break
        for i, error in enumerate(error_list):
            error_info = error.get('error', {})
            table_data = TableData()
            table_data.add_row(
                f'{error_type}_error',
                value=f"{error_type.replace('_', ' ').title()} Error #{i+1}"
            )
            if 'message' in error_info:
                message_text = safe_str(error_info['message'])
                if error_color:
                    message_text = apply_color_code(message_text, error_color)
                table_data.add_row(
                    'error_message',
                    value=message_text
                )
            if 'code' in error_info:
                table_data.add_row(
                    'error_code',
                    value=safe_str(error_info['code'])
                )
            if 'source' in error_info:
                table_data.add_row(
                    'error_source',
                    value=safe_str(error_info['source'])
                )
            if 'retryable' in error_info:
                retryable_value = "Yes" if error_info['retryable'] else "No"
                table_data.add_row(
                    'retryable',
                    value=retryable_value
                )
            if 'info' in error_info and error_info['info']:
                import json
                info_str = json.dumps(error_info['info'], ensure_ascii=False, indent=2)
                table_data.add_row(
                    'error_info',
                    value=info_str
                )
            if table_data.num_rows() > 0:
                lines.append(render_block(
                    table_data,
                    field_config,
                    table_overrides={'margin_l': 6},
                    block_type=block
                ))
            break_section(lines)
    trace_out()

@register_parser('parser_error')
def parser_error() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Only handle new error system
    global_errors = get_errors()
    if not global_errors:
        log("No errors to display")
        trace_out()
        return True
    
    log(f"Processing {len(global_errors)} errors from global error store")
    lines = []
    lines.append(render_header_block('l_error'))
    
    # Group global errors by type
    error_groups = {}
    for error_entry in global_errors:
        error_type = error_entry.error_type.value
        if error_type not in error_groups:
            error_groups[error_type] = []
        
        # Create error data directly from error entry
        if isinstance(error_entry.content, str):
            error_data = {
                "error": {
                    "type": error_type,
                    "message": error_entry.content
                }
            }
        else:
            error_data = {
                "error": {
                    "type": error_type,
                    **error_entry.content
                }
            }
        error_groups[error_type].append(error_data)
    
    # Render each error type
    for error_type, errors in error_groups.items():
        if errors:
            render_error_details(errors, error_type, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Error parser execution completed successfully with {len(result)} characters")
    
    trace_out()
    return True

@register_http('http_error')
def http_error() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Only handle new error system
    global_errors = get_errors()
    if not global_errors:
        log("No errors to display")
        trace_out()
        return True
    
    log(f"Processing {len(global_errors)} errors from global error store")
    lines = []
    lines.append(render_header_block('l_error'))
    
    # Group global errors by type
    error_groups = {}
    for error_entry in global_errors:
        error_type = error_entry.error_type.value
        if error_type not in error_groups:
            error_groups[error_type] = []
        
        # Create error data directly from error entry
        if isinstance(error_entry.content, str):
            error_data = {
                "error": {
                    "type": error_type,
                    "message": error_entry.content
                }
            }
        else:
            error_data = {
                "error": {
                    "type": error_type,
                    **error_entry.content
                }
            }
        error_groups[error_type].append(error_data)
    
    # Render each error type
    for error_type, errors in error_groups.items():
        if errors:
            render_error_details(errors, error_type, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Error parser execution completed successfully with {len(result)} characters")
    
    trace_out()
    return True

@register_mcp('mcp_error')
def mcp_error() -> bool:
    return True
