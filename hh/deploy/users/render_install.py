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


def render_install_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_install_section")
        trace_out()
        return
    
    block = 'project'
    if not gateway.is_no(block):
        init_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        git_repo = source_data.get('git_repo', 'Unknown')
        git_branch = source_data.get('git_branch', 'Unknown')
        groups_created_raw: Any = source_data.get('groups_created', [])
        groups_created: List[str] = groups_created_raw if isinstance(groups_created_raw, list) else []
        users_created_raw: Any = source_data.get('users_created', [])
        users_created: List[str] = users_created_raw if isinstance(users_created_raw, list) else []
        users_failed_raw: Any = source_data.get('users_failed', [])
        users_failed: List[str] = users_failed_raw if isinstance(users_failed_raw, list) else []
        ssh_keys_generated = source_data.get('ssh_keys_generated', 0)
        auto_scanned_keys_raw = source_data.get('auto_scanned_keys', 0)
        auto_scanned_keys = int(auto_scanned_keys_raw) if isinstance(auto_scanned_keys_raw, (int, str)) else 0
        human_scripts_created_raw: Any = source_data.get('human_scripts_created', [])
        human_scripts_created: List[str] = human_scripts_created_raw if isinstance(human_scripts_created_raw, list) else []
        root_scripts_created_raw: Any = source_data.get('root_scripts_created', [])
        root_scripts_created: List[str] = root_scripts_created_raw if isinstance(root_scripts_created_raw, list) else []
        project_ownership = source_data.get('project_ownership', 'Unknown')
        
        log(f"Rendering install section for: {project_name}")
        debug(f"Source data keys: {list(source_data.keys())}")
        
        # Project header
        init_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        
        # Git repository
        if not gateway.is_no('git'):
            init_data.add_row(
                'git_repo',
                value=safe_str(f"{git_repo} (branch: {git_branch})")
            )
        
        # Groups created
        if not gateway.is_no('groups'):
            groups_list = ', '.join(groups_created) if groups_created else 'None'
            init_data.add_row(
                'groups_created',
                value=safe_str(f"{len(groups_created)} groups: {groups_list}")
            )
        
        # Users created
        if not gateway.is_no('users'):
            users_list = ', '.join(users_created) if users_created else 'None'
            failed_list = ', '.join(users_failed) if users_failed else 'None'
            if users_failed:
                init_data.add_row(
                    'users_created',
                    value=safe_str(f"{len(users_created)} created: {users_list}")
                )
                init_data.add_row(
                    'users_created',
                    value=safe_str(f"{len(users_failed)} failed: {failed_list}")
                )
            else:
                init_data.add_row(
                    'users_created',
                    value=safe_str(f"{len(users_created)} users: {users_list}")
                )
        
        # SSH keys
        if not gateway.is_no('ssh'):
            ssh_info = f"{ssh_keys_generated} generated"
            if isinstance(auto_scanned_keys, int) and auto_scanned_keys > 0:
                ssh_info += f", {auto_scanned_keys} auto-scanned"
            init_data.add_row(
                'ssh_keys',
                value=safe_str(ssh_info)
            )
        
        # Human scripts
        if not gateway.is_no('scripts') and human_scripts_created:
            scripts_list = ', '.join(human_scripts_created)
            init_data.add_row(
                'human_scripts',
                value=safe_str(f"{len(human_scripts_created)} scripts: {scripts_list}")
            )
        
        # Root scripts
        if not gateway.is_no('root_scripts') and root_scripts_created:
            scripts_list = ', '.join(root_scripts_created)
            init_data.add_row(
                'root_scripts',
                value=safe_str(f"{len(root_scripts_created)} scripts: {scripts_list}")
            )
        
        # Ownership
        if not gateway.is_no('ownership'):
            init_data.add_row(
                'ownership',
                value=safe_str(project_ownership)
            )
        
        debug(f"Final install_data: {init_data.num_rows()} items")
        debug(f"Install data structure: {init_data}")
        
        lines.append(render_block(
            init_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['git_repo', 'groups_created', 'users_created', 'ssh_keys', 'human_scripts', 'root_scripts', 'ownership']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('install')
def install() -> bool:
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
    lines.append(render_header_block('l_install_header'))
    source_data = get_data(json_data) if json_data else {}
    log(f"Processing install data successfully")
    
    render_install_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
