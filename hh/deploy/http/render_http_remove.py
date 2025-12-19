from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser
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


def render_http_remove_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_http_remove_section")
        trace_out()
        return
    
    block = 'domain'
    if not gateway.is_no(block):
        http_data = TableData()
        domain = source_data.get('domain', 'Unknown')
        config_removed = source_data.get('config_removed', False)
        nginx_active = source_data.get('nginx_active', False)
        
        log(f"Rendering HTTP remove section for: {domain}")
        
        # Domain row
        http_data.add_row(
            'domain_header',
            value=safe_str(domain)
        )
        
        # Config removal status - separate rows for sites-available and sites-enabled
        if not gateway.is_no('config'):
            # Sites-available removal
            http_data.add_row(
                'http_config_path',
                value=f'/etc/nginx/sites-available/{domain}'
            )
            
            # Sites-enabled removal  
            http_data.add_row(
                'http_config_path',
                value=f'/etc/nginx/sites-enabled/{domain}'
            )
        
        # Nginx status
        if not gateway.is_no('nginx'):
            if nginx_active:
                http_data.add_row(
                    'nginx_active',
                    value='Yes (nginx service running)'
                )
            else:
                http_data.add_row(
                    'nginx_active',
                    value='No'
                )
        
        lines.append(render_block(
            http_data,
            FieldConfig()
                .add_simple(['domain_header', 'http_config_path', 'nginx_active']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('http_remove')
def http_remove() -> bool:
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
    lines.append(render_header_block('l_http_remove_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing HTTP remove data successfully")
    
    render_http_remove_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

