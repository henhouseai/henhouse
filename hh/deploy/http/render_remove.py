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


def render_remove_section(source_data: Dict[str, Union[str, int, bool, List]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_remove_section")
        trace_out()
        return
    
    block = 'remove'
    if not gateway.is_no(block):
        remove_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        deployment_path = source_data.get('deployment_path', 'Unknown')
        domains_removed = source_data.get('domains_removed', [])
        domains_failed = source_data.get('domains_failed', [])
        flask_stopped = source_data.get('flask_stopped', False)
        maintenance_stopped = source_data.get('maintenance_stopped', False)
        files_removed = source_data.get('files_removed', False)
        manifest_cleared = source_data.get('manifest_cleared', False)
        nginx_active = source_data.get('nginx_active', False)
        nginx_enabled_sites = source_data.get('nginx_enabled_sites', [])
        
        log(f"Rendering removal section for project: {project_name}")
        
        # Project name
        remove_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        
        # Deployment path
        remove_data.add_row(
            'deployment_path',
            value=safe_str(deployment_path)
        )
        
        # Domains removed
        if domains_removed:
            remove_data.add_row(
                'domains_removed',
                value=', '.join(domains_removed) if isinstance(domains_removed, list) else safe_str(domains_removed)
            )
        
        # Domains failed
        if domains_failed:
            remove_data.add_row(
                'domains_failed',
                value=', '.join(domains_failed) if isinstance(domains_failed, list) else safe_str(domains_failed)
            )
        
        # Flask stopped
        remove_data.add_row(
            'flask_stopped',
            value='Yes' if flask_stopped else 'No'
        )
        
        # Maintenance stopped
        remove_data.add_row(
            'maintenance_stopped',
            value='Yes' if maintenance_stopped else 'No'
        )
        
        # Files removed
        remove_data.add_row(
            'files_removed',
            value='Yes' if files_removed else 'No'
        )
        
        # Manifest cleared
        remove_data.add_row(
            'manifest_cleared',
            value='Yes' if manifest_cleared else 'No'
        )
        
        # Nginx status
        if not gateway.is_no('nginx'):
            if nginx_active:
                remove_data.add_row(
                    'nginx_active',
                    value='Yes (nginx service running)'
                )
            else:
                remove_data.add_row(
                    'nginx_active',
                    value='No'
                )
            
            # Enabled sites
            if nginx_enabled_sites:
                remove_data.add_row(
                    'nginx_enabled_sites',
                    value=', '.join(nginx_enabled_sites) if isinstance(nginx_enabled_sites, list) else safe_str(nginx_enabled_sites)
                )
        
        lines.append(render_block(
            remove_data,
            FieldConfig()
                .add_simple(['project_header', 'deployment_path', 'domains_removed', 'domains_failed', 
                           'flask_stopped', 'maintenance_stopped', 'files_removed', 'manifest_cleared',
                           'nginx_active', 'nginx_enabled_sites']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('remove')
def remove() -> bool:
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
    lines.append(render_header_block('l_remove_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing removal data successfully")
    
    render_remove_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

