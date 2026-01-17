from typing import List, Dict, Any
from hh.gateway.registry.registry import register_action, register_command, register_parser
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

from hh.gateway.registry.module_hooks import run_hooks

@register_action('remove')
@register_command('remove')
def remove() -> bool:
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
        log("Running pre-removal validation hooks")
        results = run_hooks('remove_00_pre_validate')
        if results:
            hook_results.extend(results)

    # Define removal phases
    removal_phases = [
        ('remove_05_nginx_configs', 'NGINX config removal'),
        ('remove_10_nginx_reload', 'NGINX reload'),
        ('remove_15_nginx_decoy', 'NGINX decoy cleanup'),
        ('remove_20_stop_flask', 'Flask daemon stop'),
        ('remove_25_stop_maint', 'maintenance daemon stop'),
        ('remove_30_remove_files', 'deployment file removal'),
        ('remove_35_clear_manifest', 'manifest clearing'),
    ]

    # Execute removal phases
    for hook_name, description in removal_phases:
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
        log("Removal encountered problems")

    # Clear registry cache to prevent permission issues
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()

    return trace_out(not is_error())


@register_parser('remove')
def render_remove_hookified() -> bool:
    """
    Hookified removal renderer - processes remove_render hooks from modules.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_remove_hookified")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    # Get project name from hook results
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data if json_data is not None else {})
    project_name = 'Unknown'
    hook_results = source_data.get('hook_results', [])
    for result in hook_results:
        if result.get('project_name'):
            project_name = result['project_name']
            break

    lines = []
    lines.append(render_header_block('l_remove_header'))
    log(f"Processing hookified remove data for project: {project_name}")

    # Call remove_render hooks from all modules
    from hh.gateway.registry.module_hooks import run_hooks
    render_instructions = run_hooks('remove_95_render')

    # Separate pieces for summary table vs full tables
    summary_table_data = TableData()
    summary_field_config = FieldConfig()
    full_tables = []

    # Add project name as first row of summary table
    summary_table_data.add_row('project_header', value=project_name)

    # Process each render instruction and collect pieces
    for i, instruction in enumerate(render_instructions):
        if 'render_block' in instruction:
            full_tables.append((i, instruction['render_block']))
        elif 'table_data' in instruction and 'field_config' in instruction:
            piece_table_data = instruction['table_data']
            piece_field_config = instruction['field_config']

            for row in piece_table_data.rows:
                summary_table_data.rows.append(row)

            summary_field_config.configs.extend(piece_field_config.configs)

    # Build output: summary table first, then full tables
    if summary_table_data.num_rows() > 0:
        project_config = FieldConfig()
        project_config.add_simple(['project_header'])
        summary_field_config.configs.extend(project_config.configs)

        summary_field_config.add_header('remove_summary')
        summary_block = render_block(summary_table_data, summary_field_config, table_overrides={'margin_l': 4}, block_type='remove_summary')
        lines.append(summary_block)
        break_section(lines)

    for _, full_table_html in full_tables:
        lines.append(full_table_html)
        break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
