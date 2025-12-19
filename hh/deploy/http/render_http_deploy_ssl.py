from __future__ import annotations
from typing import Dict, List, Union, Any
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


def render_http_deploy_ssl_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_http_deploy_ssl_section")
        trace_out()
        return
    
    block = 'domain'
    if not gateway.is_no(block):
        http_data = TableData()
        domain = source_data.get('domain', 'Unknown')
        config_installed = source_data.get('config_installed', False)
        nginx_active = source_data.get('nginx_active', False)
        certificate_path = source_data.get('certificate_path', 'N/A')
        
        log(f"Rendering HTTP deploy SSL section for: {domain}")
        debug(f"Source data keys: {list(source_data.keys())}")
        
        # Domain header
        http_data.add_row(
            'domain_header',
            value=safe_str(domain)
        )
        
        # Config installation status with separate rows for port and path
        if not gateway.is_no('config'):
            if config_installed:
                port = source_data.get('port', 443)
                config_file_path = source_data.get('config_file_path', '')
                http_data.add_row(
                    'port',
                    value=safe_str(port)
                )
                http_data.add_row(
                    'http_config_path',
                    value=safe_str(config_file_path)
                )
        
        # Certificate path
        if not gateway.is_no('cert'):
            http_data.add_row(
                'certificate_path',
                value=safe_str(certificate_path)
            )
        
        # Main domain
        if not gateway.is_no('main_domain'):
            main_domain = source_data.get('main_domain', domain)
            http_data.add_row('main_domain', value=safe_str(main_domain))
        
        # Subdomains - separate row for each
        if not gateway.is_no('subdomains'):
            subdomains_raw: Any = source_data.get('subdomains', [])
            subdomains: List[str] = subdomains_raw if isinstance(subdomains_raw, list) else []
            for subdomain in subdomains:
                http_data.add_row('subdomain', value=safe_str(subdomain))
        
        # Whitelist summary
        if not gateway.is_no('whitelist'):
            whitelist_raw: Any = source_data.get('whitelist_summary', {})
            whitelist: Dict[str, Any] = whitelist_raw if isinstance(whitelist_raw, dict) else {}
            if whitelist.get('js_files', 0) > 0:
                http_data.add_row('js_whitelist', value=safe_str(f"{whitelist.get('js_files')} files"))
            if whitelist.get('css_files', 0) > 0:
                http_data.add_row('css_whitelist', value=safe_str(f"{whitelist.get('css_files')} files"))
            if whitelist.get('misc_files', 0) > 0:
                http_data.add_row('misc_whitelist', value=safe_str(f"{whitelist.get('misc_files')} files"))
            if whitelist.get('context_folders', 0) > 0:
                http_data.add_row('context_whitelist', value=safe_str(f"{whitelist.get('context_folders')} folders"))
        
        # Nginx status (last row)
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
        
        debug(f"Final http_data: {http_data.num_rows()} items")
        
        lines.append(render_block(
            http_data,
            FieldConfig()
                .add_header('domain_header')
                .add_simple(['port', 'http_config_path', 'certificate_path', 'nginx_active', 'main_domain', 'subdomain', 'js_whitelist', 'css_whitelist', 'misc_whitelist', 'context_whitelist']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('http_deploy_ssl')
def http_deploy_ssl() -> bool:
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
    lines.append(render_header_block('l_http_deploy_ssl_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing HTTP deploy SSL data successfully")
    
    render_http_deploy_ssl_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

