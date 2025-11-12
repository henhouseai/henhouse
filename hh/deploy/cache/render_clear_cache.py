from __future__ import annotations
from typing import List, TypedDict
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from hh.render.config.config import safe_str
from hh.gateway.registry.registry import register_parser, register_http
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


def render_clear_cache_section(source_data: dict, lines: List[str]) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_clear_cache_section")
        trace_out()
        return False
    
    block = 'rows'
    if not gateway.is_no(block):
        success = source_data.get('success', False)
        total_items = source_data.get('total_items_cleared', 0)
        details = source_data.get('details', {})
        
        log(f"Rendering clear cache results: {total_items} items cleared")
        
        if not success:
            warn("Cache clear was not successful")
            report_error("backend","Cache clear was not successful")
            trace_out()
            return False
        
        table_data = TableData()
        
        # Add header row with integrated count
        table_data.add_row(
            'success',
            label=f'{total_items} items cleared',
            item_type='Type',
            file_path='Path'
        )
        
        # Add cache files
        cache_files = details.get('cache_files', [])
        for cache_file in cache_files:
            table_data.add_row(
                'file_path',
                item_type='Cache File',
                file_path=safe_str(cache_file)
            )
        
        # Add __pycache__ directories
        pycache_dirs = details.get('pycache_dirs', [])
        for pycache_dir in pycache_dirs:
            table_data.add_row(
                'file_path',
                item_type='__pycache__',
                file_path=safe_str(pycache_dir)
            )
        
        # Add .pyc files
        pyc_files = details.get('pyc_files', [])
        for pyc_file in pyc_files:
            table_data.add_row(
                'file_path',
                item_type='.pyc File',
                file_path=safe_str(pyc_file)
            )
        
        rendered_block = render_block(
            table_data, 
            FieldConfig()
                .add_header('header')
                .add_simple_color('success', 'green')
                .add_simple(['count', 'item_type', 'file_path']),
            table_overrides={'margin_l': 4}, 
            block_type=block
        )
        lines.append(rendered_block)
        log(f"Rendered clear cache table with {table_data.num_rows()} rows")
    else:
        log("Rows block disabled, skipping clear cache rendering")
    
    trace_out()
    return True

@register_http('clear_cache')
@register_parser('clear_cache')
def clear_cache() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False
    
    json_data = gateway.response.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_clear_cache_header'))
        source_data = get_data(json_data)
        if not render_clear_cache_section(source_data, lines):
            warn("Failed to render clear cache section")
            report_error("backend","Failed to render clear cache section")
            trace_out()
            return False
        break_section(lines)
        result = finalize_output(lines)
        if len(result) == 0:
            warn("Backend response is empty")
        gateway.response.add_output(result)
        log(f"Parser execution completed successfully with {len(result)} lines.")
        trace_out()
        return True
    except Exception as e:
        warn("Parser execution raised an exception.")
        report_error("backend",f"Parser execution raised an exception: {e}")
        trace_out()
        return False
