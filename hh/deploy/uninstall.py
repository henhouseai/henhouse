"""
Uninstall action - hookified architecture.

Handles system uninstallation via module hooks.
"""

from typing import List, Dict, Any
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.module_hooks import run_hooks
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.error.error_store import report_error, is_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section, safe_str

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


@register_action('uninstall')
@register_command('uninstall')
def uninstall() -> bool:
    """Uninstall the project with hookified architecture."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Check if running in deployed Unix environment with privileges
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False

    # Initialize hook results collection
    hook_results: List[Dict[str, Any]] = []

    # Uninstall phases
    uninstall_phases = [
        ('uninstall_00_pre_validate', 'context validation'),
        ('uninstall_15_users', 'tier user removal'),
        ('uninstall_20_manifest', 'manifest update'),
        ('uninstall_25_project_dir', 'project directory removal'),
        ('uninstall_30_groups', 'group cleanup'),
        ('uninstall_40_htpasswd', 'htpasswd cleanup'),
        ('uninstall_50_user_env', 'user environment cleanup'),
        ('uninstall_65_cache_cleanup', 'cache cleanup'),
    ]

    # Execute uninstall phases
    for hook_name, description in uninstall_phases:
        if not is_error():
            log(f"Running {description} hooks")
            results = run_hooks(hook_name)
            if results:
                hook_results.extend(results)

    # Build result data
    from hh.deploy.uninstall_hooks import UNINSTALL_CONFIG
    from hh_user_tiers.deploy.uninstall_hooks import tier_config
    from hh.deploy.user_accounts import detect_project_owner
    from pathlib import Path

    project_name = UNINSTALL_CONFIG.get("project_name", "Unknown")
    project_path = UNINSTALL_CONFIG.get("project_path")
    removed_users = tier_config.get("removed_users", [])
    users_skipped = tier_config.get("users_skipped", [])
    users_total_attempted = tier_config.get("users_total_attempted", 0)
    project_directory_removed = tier_config.get("project_directory_removed", False)
    project_directory_path = tier_config.get("project_directory_path", "")
    groups_deleted = tier_config.get("groups_deleted", [])
    groups_total_attempted = tier_config.get("groups_total_attempted", 0)

    # Get human/root scripts removed from hook results
    human_scripts_removed = []
    root_scripts_removed = []
    for result in hook_results:
        if result.get("human_scripts_removed"):
            human_scripts_removed = result["human_scripts_removed"]
        if result.get("root_scripts_removed"):
            root_scripts_removed = result["root_scripts_removed"]

    project_owner = detect_project_owner(project_path) if project_path else None

    if not is_error():
        log("System uninstall completed successfully")

        result_data = {
            "project_name": project_name,
            "project_path": str(project_path) if project_path else "",
            "project_owner": project_owner,
            "users_removed": removed_users,
            "users_skipped": users_skipped,
            "users_total_attempted": users_total_attempted,
            "project_directory_removed": project_directory_removed,
            "project_directory_path": project_directory_path,
            "groups_deleted": groups_deleted,
            "groups_total_attempted": groups_total_attempted,
            "human_scripts_removed": human_scripts_removed,
            "root_scripts_removed": root_scripts_removed,
            "safety_checks_passed": len(removed_users),
            "safety_checks_failed": len(users_skipped),
            "status": "uninstalled",
            "hook_results": hook_results
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("System uninstall encountered problems")

    return trace_out(not is_error())


@register_parser('uninstall')
def render_uninstall_hookified() -> bool:
    """
    Hookified uninstall renderer - processes uninstall_95_render hooks from modules.

    Follows the same rendering architecture as install where each module provides
    rendering instructions via uninstall_95_render hooks.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_uninstall_hookified")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data if json_data is not None else {})

    project_name = source_data.get('project_name', 'Unknown')
    project_owner = source_data.get('project_owner', 'Unknown')
    users_removed = source_data.get('users_removed', [])
    users_skipped = source_data.get('users_skipped', [])
    users_total_attempted = source_data.get('users_total_attempted', 0)
    project_directory_removed = source_data.get('project_directory_removed', False)
    project_directory_path = source_data.get('project_directory_path', 'Unknown')
    groups_deleted = source_data.get('groups_deleted', [])
    groups_total_attempted = source_data.get('groups_total_attempted', 0)
    human_scripts_removed = source_data.get('human_scripts_removed', [])
    root_scripts_removed = source_data.get('root_scripts_removed', [])
    safety_checks_passed = source_data.get('safety_checks_passed', 0)
    safety_checks_failed = source_data.get('safety_checks_failed', 0)

    lines = []
    lines.append(render_header_block('l_uninstall_header'))
    log(f"Processing hookified uninstall data for project: {project_name}")

    # Build uninstall summary table
    block = 'project'
    if not gateway.is_no(block):
        uninstall_data = TableData()

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

        lines.append(render_block(
            uninstall_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['users_removed', 'project_directory', 'groups_deleted', 'human_scripts', 'root_scripts', 'safety_checks']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)

    # Call uninstall_95_render hooks from all modules for additional rendering
    render_instructions = run_hooks('uninstall_95_render')

    # Process any full table render blocks from modules
    for instruction in render_instructions:
        if 'render_block' in instruction:
            lines.append(instruction['render_block'])
            break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
