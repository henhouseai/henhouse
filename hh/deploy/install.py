"""
Install action - hookified architecture.

Handles system initialization via module hooks.
"""

from typing import List, Dict, Any
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.module_hooks import run_hooks
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.error.error_store import report_error, is_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section

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


@register_action('install')
@register_command('install')
def install() -> bool:
    """Install the project with hookified architecture."""
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

    # Phase 00: Always run - determines mode (template or install)
    if not is_error():
        log("Running pre-install validation hooks")
        results = run_hooks('install_00_pre_validate')
        if results:
            hook_results.extend(results)

    from hh.deploy.install_hooks import INSTALL_CONFIG
    mode = INSTALL_CONFIG["mode"]

    if mode == "template":
        # BRANCH A: Template generation phases
        if not is_error():
            log("Running template contribution hooks")
            results = run_hooks('install_01_template_contribute')
            if results:
                hook_results.extend(results)

        if not is_error():
            log("Running template write hooks")
            results = run_hooks('install_02_template_write')
            if results:
                hook_results.extend(results)

        trace_out()
        return not is_error()

    elif mode == "install":
        # BRANCH B: Installation phases 05-70
        installation_phases = [
            ('install_05_pre_validate', 'configuration validation'),
            ('install_10_conflict_check', 'conflict checking'),
            ('install_15_groups', 'core group creation'),
            ('install_20_users', 'tier user creation'),
            ('install_25_user_configs', 'user configuration'),
            ('install_30_htpasswd', 'HTTP Basic Auth setup'),
            ('install_35_project_groups', 'project group finalization'),
            ('install_40_git', 'git repository initialization'),
            ('install_45_scripts', 'gateway script creation'),
            ('install_50_user_env', 'user environment setup'),
            ('install_55_media_dirs', 'media directory creation'),
            ('install_60_permissions', 'deployment permissions'),
            ('install_65_cache_cleanup', 'cache cleanup'),
            ('install_70_manifest', 'manifest writing'),
        ]

        # Execute installation phases
        for hook_name, description in installation_phases:
            if not is_error():
                log(f"Running {description} hooks")
                results = run_hooks(hook_name)
                if results:
                    hook_results.extend(results)

        if not is_error():
            result_data = {
                "hook_results": hook_results
            }
            gateway.response.set_action_response(success_payload(result_data))
        else:
            log("Installation encountered problems")

        # Clear registry cache to prevent permission issues
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        clean_all_caches()

        return trace_out(not is_error())

    else:
        warn(f"Unknown install mode: {mode}")
        trace_out()
        return False


@register_parser('install')
def render_install_hookified() -> bool:
    """
    Hookified installation renderer - processes install_95_render hooks from modules.

    This follows the same rendering architecture as deploy where each module provides
    rendering instructions via install_95_render hooks. Results can be either:
    - {"table_data": TableData, "field_config": FieldConfig} for aggregation into main summary
    - {"render_block": "pre-rendered HTML"} for direct inclusion as separate tables

    Pieces are aggregated into ONE summary table, full tables are inserted between pieces.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_install_hookified")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    # Get project name from hook results (install_00_pre_validate)
    json_data = gateway.response.get_action_response()
    debug(json_data)
    source_data = get_data(json_data if json_data is not None else {})
    project_name = 'Unknown'
    hook_results = source_data.get('hook_results', [])
    for result in hook_results:
        if result.get('project_name'):
            project_name = result['project_name']
            break

    lines = []
    lines.append(render_header_block('l_install_header'))
    log(f"Processing hookified install data for project: {project_name}")

    # Call install_95_render hooks from all modules
    render_instructions = run_hooks('install_95_render')

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
        summary_field_config.add_header('install_summary')
        summary_block = render_block(summary_table_data, summary_field_config, table_overrides={'margin_l': 4}, block_type='install_summary')
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
