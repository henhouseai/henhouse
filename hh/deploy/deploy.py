import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.error.error_store import report_error, is_error
from nginx_flask.deploy.http.deploy_helpers import should_ignore_context_path
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

from hh.deploy.deploy_utils import load_whitelist_with_extensions
from hh.gateway.registry.module_hooks import run_hooks

@register_action('deploy')
@register_command('deploy')
def deploy() -> bool:
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

    # Run pre-validation first
    if not is_error():
        log("Running pre-deployment validation hooks")
        results = run_hooks('deploy_00_pre_validate')
        if results:
            hook_results.extend(results)

    # Define remaining deployment phases
    deployment_phases = [
        # Pre-deployment preparation (continued)
        ('deploy_05_stop_daemons', 'daemon stop'),
        ('deploy_10_git_preserve_ops', 'git preservation operations'),
        ('deploy_15_sterilize_directory', 'directory sterilization'),
        ('deploy_20_git_restore_ops', 'git restoration operations'),

        # Core deployment
        ('deploy_25_modules', 'module deployment'),
        ('deploy_30_framework_cleanup', 'framework cleanup'),
        ('deploy_35_cache_cleanup', 'cache cleanup'),
        ('deploy_40_flask_apps', 'Flask app deployment'),
        ('deploy_45_flask_apps', 'maintenance worker deployment'),  # Uses same hook but different description

        # Site deployment
        ('deploy_50_client_files', 'client file deployment'),
        ('deploy_55_context', 'context deployment'),
        ('deploy_60_site_prepare', 'site preparation'),
        ('deploy_65_site', 'site deployment'),

        # Permissions and services
        ('deploy_70_permissions_base', 'base permissions setup'),
        ('deploy_75_permissions_special', 'special permissions setup'),
        ('deploy_80_restart_daemons', 'daemon restart'),

        # Final deployment steps
        ('deploy_85_nginx_and_ssl', 'NGINX and SSL deployment'),
        ('deploy_90_manifest', 'site manifest addition'),
    ]

    # Execute remaining deployment phases
    for hook_name, description in deployment_phases:
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
        log("Deployment encountered problems")

    # Clear registry cache to prevent permission issues
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    return trace_out(not is_error())


@register_parser('deploy')
def render_deploy_hookified() -> bool:
    """
    Hookified deployment renderer - processes deploy_render hooks from modules.

    This is the new rendering architecture where each module provides its own
    rendering instructions via deploy_render hooks. The results can be either:
    - {"table_data": TableData, "field_config": FieldConfig} for aggregation into main summary
    - {"render_block": "pre-rendered HTML"} for direct inclusion as separate tables

    Pieces are aggregated into ONE summary table, full tables are inserted between pieces.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_deploy_hookified")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False

    # Get project name from hook results (deploy_pre_validate)
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data if json_data is not None else {})
    project_name = 'Unknown'
    hook_results = source_data.get('hook_results', [])
    for result in hook_results:
        if result.get('project_name'):
            project_name = result['project_name']
            break

    lines = []
    lines.append(render_header_block('l_deploy_header'))
    log(f"Processing hookified deploy data for project: {project_name}")

    # Call deploy_render hooks from all modules
    from hh.gateway.registry.module_hooks import run_hooks
    render_instructions = run_hooks('deploy_95_render')

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
        summary_field_config.add_header('deploy_summary')
        summary_block = render_block(summary_table_data, summary_field_config, block_type='deploy_summary')
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
