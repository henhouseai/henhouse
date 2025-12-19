from __future__ import annotations
from typing import Dict, List, Union, Any
from hh.gateway.registry.registry import register_parser
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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


def render_deploy_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_deploy_section")
        trace_out()
        return
    
    block = 'project'
    if not gateway.is_no(block):
        deploy_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        source = source_data.get('source', 'Unknown')
        destination = source_data.get('destination', 'Unknown')
        code_deployed = source_data.get('code_deployed', False)
        deployment_cleaned = source_data.get('deployment_cleaned', False)
        cache_cleaned_raw: Any = source_data.get('cache_cleaned', {})
        cache_cleaned: Dict[str, Any] = cache_cleaned_raw if isinstance(cache_cleaned_raw, dict) else {}
        flask_deployed_raw: Any = source_data.get('flask_deployed', [])
        flask_deployed: List[str] = flask_deployed_raw if isinstance(flask_deployed_raw, list) else []
        flask_restart_raw: Any = source_data.get('flask_restart', {})
        flask_restart: Dict[str, Any] = flask_restart_raw if isinstance(flask_restart_raw, dict) else {}
        maintenance_restart_raw: Any = source_data.get('maintenance_restart', {})
        maintenance_restart: Dict[str, Any] = maintenance_restart_raw if isinstance(maintenance_restart_raw, dict) else {}
        context_deployed_raw: Any = source_data.get('context_deployed', [])
        context_deployed: List[str] = context_deployed_raw if isinstance(context_deployed_raw, list) else []
        js_count_raw = source_data.get('js_count', 0)
        js_count = int(js_count_raw) if isinstance(js_count_raw, (int, str)) else 0
        css_count_raw = source_data.get('css_count', 0)
        css_count = int(css_count_raw) if isinstance(css_count_raw, (int, str)) else 0
        misc_count_raw = source_data.get('misc_count', 0)
        misc_count = int(misc_count_raw) if isinstance(misc_count_raw, (int, str)) else 0
        ownership_set = source_data.get('ownership_set', False)
        cache_permissions_set = source_data.get('cache_permissions_set', False)
        
        log(f"Rendering deploy section for: {project_name}")
        debug(f"Source data keys: {list(source_data.keys())}")
        debug(f"Code deployed: {code_deployed}, type: {type(code_deployed)}")
        debug(f"Cache cleaned: {cache_cleaned}, type: {type(cache_cleaned)}")
        debug(f"Context deployed: {context_deployed}, type: {type(context_deployed)}")
        
        # Project header
        deploy_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        debug(f"Added project data: {deploy_data.num_rows()} items")
        
        # Code deployment
        if not gateway.is_no('code'):
            deploy_data.add_row(
                'code_deployed',
                value='Yes' if code_deployed else 'No'
            )
        
        # Deployment cleaning
        if not gateway.is_no('deployment'):
            deploy_data.add_row(
                'deployment_cleaned',
                value='Yes' if deployment_cleaned else 'No'
            )
        
        # Cache cleanup - show specific details
        if not gateway.is_no('cache'):
            debug(f"Processing cache_cleaned: {cache_cleaned}")
            if isinstance(cache_cleaned, dict):
                if cache_cleaned.get('pycache_dirs', 0) > 0:
                    deploy_data.add_row(
                        'cache_cleaned',
                        value=safe_str(f"{cache_cleaned['pycache_dirs']} __pycache__ dirs")
                    )
                    debug(f"Added pycache dirs: {cache_cleaned['pycache_dirs']}")
                if cache_cleaned.get('pyc_files', 0) > 0:
                    deploy_data.add_row(
                        'cache_cleaned',
                        value=safe_str(f"{cache_cleaned['pyc_files']} .pyc files")
                    )
                    debug(f"Added pyc files: {cache_cleaned['pyc_files']}")
                if cache_cleaned.get('cache_files', 0) > 0:
                    deploy_data.add_row(
                        'cache_cleaned',
                        value=safe_str(f"{cache_cleaned['cache_files']} cache files")
                    )
                    debug(f"Added cache files: {cache_cleaned['cache_files']}")
                if cache_cleaned.get('cache_dirs', 0) > 0:
                    deploy_data.add_row(
                        'cache_cleaned',
                        value=safe_str(f"{cache_cleaned['cache_dirs']} .cache dirs")
                    )
                    debug(f"Added cache dirs: {cache_cleaned['cache_dirs']}")
            else:
                debug(f"Cache cleaned is not a dict: {type(cache_cleaned)}")
        
        # Flask deployment - show each app
        if not gateway.is_no('flask'):
            for app in flask_deployed:
                deploy_data.add_row(
                    'flask_deployed',
                    value=safe_str(app)
                )
        if not gateway.is_no('flask') and flask_restart:
            daemons = flask_restart.get('daemons', [])
            for daemon in daemons:
                tier = daemon.get('tier', 'unknown')
                status = daemon.get('status', 'unknown')
                error = daemon.get('error')
                message = f"{tier}: {status}"
                if error:
                    message += f" ({error})"
                deploy_data.add_row(
                    'flask_restart',
                    value=safe_str(message)
                )
        
        # Context deployment - show each folder
        if not gateway.is_no('context'):
            for folder in context_deployed:
                deploy_data.add_row(
                    'context_deployed',
                    value=safe_str(folder)
                )
        
        # Site whitelist counts
        if not gateway.is_no('site'):
            if js_count > 0:
                deploy_data.add_row(
                    'js_count',
                    value=safe_str(f"{js_count} files")
                )
            if css_count > 0:
                deploy_data.add_row(
                    'css_count',
                    value=safe_str(f"{css_count} files")
                )
            if misc_count > 0:
                deploy_data.add_row(
                    'misc_count',
                    value=safe_str(f"{misc_count} files")
                )
        
        # Ownership - show what it was set to
        if not gateway.is_no('ownership') and ownership_set:
            project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
            deploy_group_name = f"{project_name}_deploy"
            deploy_data.add_row(
                'ownership_set',
                value=safe_str(f"{project_highest_user}:{deploy_group_name}")
            )
        
        # Cache permissions
        if not gateway.is_no('permissions'):
            deploy_data.add_row(
                'cache_permissions',
                value='Yes' if cache_permissions_set else 'No'
            )
        if not gateway.is_no('maintenance'):
            maint_status = maintenance_restart.get('status')
            if maint_status:
                detail = maint_status
                error = maintenance_restart.get('error')
                if error:
                    detail += f" ({error})"
                deploy_data.add_row(
                    'maintenance_restart',
                    value=safe_str(detail)
                )
        
        debug(f"Final deploy_data: {deploy_data.num_rows()} items")
        debug(f"Deploy data structure: {deploy_data}")
        
        lines.append(render_block(
            deploy_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple([
                    'project_info',
                    'code_deployed',
                    'deployment_cleaned',
                    'cache_cleaned',
                    'flask_deployed',
                    'flask_restart',
                    'context_deployed',
                    'js_count',
                    'css_count',
                    'misc_count',
                    'ownership_set',
                    'cache_permissions',
                    'maintenance_restart',
                ]),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('deploy')
def deploy() -> bool:
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
    lines.append(render_header_block('l_deploy_header'))
    source_data = get_data(json_data) if json_data else {}
    log(f"Processing deploy data successfully")
    
    render_deploy_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
