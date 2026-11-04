"""
Hookified database user removal orchestrator.

Calls module hooks to revoke permissions and remove tier-based users in a distributed way.
Each module owns permission revocation for its tables.
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.module_hooks import run_hooks
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path
from hh.deploy.db_config import DB_CONFIG
from hh.render.render import render_header_block, finalize_output
import configparser

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


@register_action('remove_db_users')
@register_command('remove_db_users')
def remove_db_users(args: Optional[List[str]] = None) -> bool:
    """Revoke permissions and remove tier-based database users using module hooks."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False

    # Validate privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("remove_db_users requires sudo/root privileges")
        report_error("action", "remove_db_users requires sudo/root privileges")
        trace_out()
        return False

    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for remove_db_users")
        report_error("action", "Root flag (-root) is required for remove_db_users")
        trace_out()
        return False

    project_name, project_path = detect_project_context()
    log(f"Starting hookified database user removal for project: {project_name}")

    hook_results: List[Dict[str, Any]] = []

    # Phase 00: Pre-validation (load config, create credential files)
    if not is_error():
        log("Running pre-validation hooks")
        results = run_hooks('remove_db_users_00_pre_validate')
        if results:
            hook_results.extend(results)

    # Phase 05: Revoke permissions on cache DB for media modules (all parallel)
    if not is_error():
        log("Revoking media module permissions on cache database")
        results = run_hooks('remove_db_users_05_revoke_media_cache')
        if results:
            hook_results.extend(results)

    # Phase 10: Revoke permissions on cache DB for page module
    if not is_error():
        log("Revoking page module permissions on cache database")
        results = run_hooks('remove_db_users_10_revoke_page_cache')
        if results:
            hook_results.extend(results)

    # Phase 15: Revoke permissions on main DB for media modules (all parallel)
    if not is_error():
        log("Revoking media module permissions on main database")
        results = run_hooks('remove_db_users_15_revoke_media_main')
        if results:
            hook_results.extend(results)

    # Phase 20: Revoke permissions on main DB for page module
    if not is_error():
        log("Revoking page module permissions on main database")
        results = run_hooks('remove_db_users_20_revoke_page_main')
        if results:
            hook_results.extend(results)

    # Phase 25: Remove tier users (after all permissions revoked)
    if not is_error():
        log("Removing tier-based database users")
        results = run_hooks('remove_db_users_25_remove_users')
        if results:
            hook_results.extend(results)

    # Phase 90: Cleanup (remove credential files)
    if not is_error():
        log("Running cleanup hooks")
        results = run_hooks('remove_db_users_90_cleanup')
        if results:
            hook_results.extend(results)

    if not is_error():
        result_data = {
            "hook_results": hook_results,
            "project_name": project_name
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Database user removal encountered problems")

    return trace_out(not is_error())


@register_parser('remove_db_users')
def render_remove_db_users() -> bool:
    """
    Hookified renderer for remove_db_users action.

    Processes remove_db_users_95_render hooks from modules to build summary table.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_remove_db_users")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    # Get project name from action response
    json_data = gateway.response.get_action_response()
    debug(json_data)
    source_data = get_data(json_data if json_data is not None else {})
    project_name = source_data.get('project_name', 'Unknown')

    lines = []
    lines.append(render_header_block('l_remove_db_users_header'))
    log(f"Processing hookified remove_db_users data for project: {project_name}")

    # Call remove_db_users_95_render hooks from all modules
    from hh.render.render import render_block, FieldConfig, TableData
    from hh.render.config.config import break_section

    render_instructions = run_hooks('remove_db_users_95_render')

    # Separate pieces for summary table vs full tables
    summary_table_data = TableData()
    summary_field_config = FieldConfig()
    full_tables = []  # List of (instruction_index, render_block) tuples

    # Add project name as first row of summary table
    summary_table_data.add_row('project_header', value=project_name)

    # Process each render instruction and collect pieces
    for i, instruction in enumerate(render_instructions):
        if 'render_block' in instruction:
            # Full table - collect for insertion at this position
            full_tables.append((i, instruction['render_block']))
        elif 'table_data' in instruction and 'field_config' in instruction:
            # Piece for summary table - aggregate it
            piece_table_data = instruction['table_data']
            piece_field_config = instruction['field_config']

            # Merge table data (add all rows)
            for row in piece_table_data.rows:
                summary_table_data.rows.append(row)

            # Merge field configs (add all simple fields - hooks should NOT define headers)
            summary_field_config.configs.extend(piece_field_config.configs)

    # Build output: summary table first, then full tables
    if summary_table_data.num_rows() > 0:
        # Add project_header field to config
        project_config = FieldConfig()
        project_config.add_simple(['project_header'])
        summary_field_config.configs.extend(project_config.configs)

        # Add summary header since we have content (hooks only provide simple fields)
        summary_field_config.add_header('remove_db_users_summary')
        summary_block = render_block(summary_table_data, summary_field_config, table_overrides={'margin_l': 4}, block_type='remove_db_users_summary')
        lines.append(summary_block)
        break_section(lines)

    # Add full tables in the order they appeared
    for _, full_table_html in full_tables:
        lines.append(full_table_html)
        break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
