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


def render_uninstall_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_uninstall_section")
        trace_out()
        return
    
    block = 'project'
    if not gateway.is_no(block):
        uninstall_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        project_owner = source_data.get('project_owner', 'Unknown')
        users_removed_raw: Any = source_data.get('users_removed', [])
        users_removed: List[str] = users_removed_raw if isinstance(users_removed_raw, list) else []
        users_skipped_raw: Any = source_data.get('users_skipped', [])
        users_skipped: List[str] = users_skipped_raw if isinstance(users_skipped_raw, list) else []
        users_total_attempted = source_data.get('users_total_attempted', 0)
        project_directory_removed = source_data.get('project_directory_removed', False)
        project_directory_path = source_data.get('project_directory_path', 'Unknown')
        groups_deleted_raw: Any = source_data.get('groups_deleted', [])
        groups_deleted: List[str] = groups_deleted_raw if isinstance(groups_deleted_raw, list) else []
        groups_total_attempted = source_data.get('groups_total_attempted', 0)
        human_scripts_removed_raw: Any = source_data.get('human_scripts_removed', [])
        human_scripts_removed: List[str] = human_scripts_removed_raw if isinstance(human_scripts_removed_raw, list) else []
        root_scripts_removed_raw: Any = source_data.get('root_scripts_removed', [])
        root_scripts_removed: List[str] = root_scripts_removed_raw if isinstance(root_scripts_removed_raw, list) else []
        safety_checks_passed = source_data.get('safety_checks_passed', 0)
        safety_checks_failed = source_data.get('safety_checks_failed', 0)
        
        log(f"Rendering uninstall section for: {project_name}")
        debug(f"Source data keys: {list(source_data.keys())}")
        
        # Project header
        uninstall_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        
        # Users removed
        if not gateway.is_no('users'):
            if users_removed:
                users_list = ', '.join(users_removed)
                uninstall_data.add_row(
                    'users_removed',
                    value=safe_str(f"{len(users_removed)}/{users_total_attempted} users: {users_list}")
                )
            if users_skipped:
                skipped_list = ', '.join(users_skipped)
                uninstall_data.add_row(
                    'users_removed',
                    value=safe_str(f"{len(users_skipped)} skipped (safety failed): {skipped_list}")
                )
            if not users_removed and not users_skipped:
                uninstall_data.add_row(
                    'users_removed',
                    value=safe_str("No users to remove")
                )
        
        # Project directory
        if not gateway.is_no('directory'):
            status = "Removed" if project_directory_removed else "Preserved (highest user exists)"
            uninstall_data.add_row(
                'project_directory',
                value=safe_str(f"{status}: {project_directory_path}")
            )
        
        # Groups deleted
        if not gateway.is_no('groups'):
            if groups_deleted:
                groups_list = ', '.join(groups_deleted)
                uninstall_data.add_row(
                    'groups_deleted',
                    value=safe_str(f"{len(groups_deleted)}/{groups_total_attempted} groups: {groups_list}")
                )
            else:
                uninstall_data.add_row(
                    'groups_deleted',
                    value=safe_str("No groups deleted")
                )
        
        # Human scripts removed
        if not gateway.is_no('scripts') and human_scripts_removed:
            scripts_list = ', '.join(human_scripts_removed)
            uninstall_data.add_row(
                'human_scripts',
                value=safe_str(f"{len(human_scripts_removed)} scripts: {scripts_list}")
            )
        
        # Root scripts removed
        if not gateway.is_no('root_scripts') and root_scripts_removed:
            scripts_list = ', '.join(root_scripts_removed)
            uninstall_data.add_row(
                'root_scripts',
                value=safe_str(f"{len(root_scripts_removed)} scripts: {scripts_list}")
            )
        
        # Safety checks
        if not gateway.is_no('safety'):
            uninstall_data.add_row(
                'safety_checks',
                value=safe_str(f"{safety_checks_passed} passed, {safety_checks_failed} failed")
            )
        
        debug(f"Final uninstall_data: {uninstall_data.num_rows()} items")
        debug(f"Uninstall data structure: {uninstall_data}")
        
        lines.append(render_block(
            uninstall_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['users_removed', 'project_directory', 'groups_deleted', 'human_scripts', 'root_scripts', 'safety_checks']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('uninstall')
def uninstall() -> bool:
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
    lines = []
    lines.append(render_header_block('l_uninstall_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing uninstall data successfully")
    
    render_uninstall_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
