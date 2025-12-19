from __future__ import annotations
from typing import Dict, List, Union, Any
from hh.gateway.registry.registry import register_parser
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section, safe_str
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


def render_install_cursor_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_install_cursor_section")
        trace_out()
        return
    
    block = 'rows'
    if not gateway.is_no(block):
        cursor_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        users_processed = source_data.get('users_processed', 0)
        users_successful_raw = source_data.get('users_successful', 0)
        users_successful = int(users_successful_raw) if isinstance(users_successful_raw, (int, str)) else 0
        users_failed_raw = source_data.get('users_failed', 0)
        users_failed = int(users_failed_raw) if isinstance(users_failed_raw, (int, str)) else 0
        cursor_results_raw: Any = source_data.get('cursor_results', [])
        cursor_results: List[Dict[str, Any]] = cursor_results_raw if isinstance(cursor_results_raw, list) else []
        
        log(f"Rendering cursor installation results for: {project_name}")
        debug(f"Users processed: {users_processed}, successful: {users_successful}, failed: {users_failed}")
        
        # Project header
        cursor_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        
        # Summary row
        cursor_data.add_row(
            'users_processed',
            value=safe_str(f"{users_processed} users processed")
        )
        
        # Success/failure counts
        if users_successful > 0:
            cursor_data.add_row(
                'success_count',
                value=safe_str(f"{users_successful} successful")
            )
        
        if users_failed > 0:
            cursor_data.add_row(
                'failed_count',
                value=safe_str(f"{users_failed} failed")
            )
        
        # Individual user results
        for result in cursor_results:
            if not isinstance(result, dict):
                continue
            username = result.get('username', 'Unknown')
            status = result.get('status', 'unknown')
            error = result.get('error', '')
            
            # Determine field type based on status
            if status == 'success':
                field_type = 'success_count'
            else:
                field_type = 'failed_count'
            
            cursor_data.add_row(
                field_type,
                username=safe_str(username),
                status=safe_str(status.title()),
                error=safe_str(error) if error else ''
            )
        
        debug(f"Final cursor_data: {cursor_data.num_rows()} items")
        
        lines.append(render_block(
            cursor_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['users_processed', 'username', 'status', 'error'])
                .add_simple_color('success_count', 'green')
                .add_simple_color('failed_count', 'red'),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('install_cursor')
def install_cursor() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False
    
    json_data = gateway.response.get_action_response()
    lines = []
    lines.append(render_header_block('l_install_cursor_header'))
    source_data = get_data(json_data) if json_data else {}
    log(f"Processing cursor installation data successfully")
    
    render_install_cursor_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
