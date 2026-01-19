"""
Git deployment render hooks for hh_git module.

Provides summary contribution and detail table for git operations.
"""
from typing import Dict, Any
from hh.render.render import TableData, FieldConfig, render_block
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init

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


@register_module_hook('deploy_95_render', 'Contribute Git summary')
def render_git_summary_contribution() -> Dict[str, Any]:
    """Contribute Git-related summary to deployment summary table (1 line)."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Collect all git-related activity
    git_preserved = False
    git_restored = False
    git_permissions_set = False
    modules_cleaned = 0

    for result in hook_results:
        component = result.get('component', '')
        if component == 'git_preserve' and result.get('preserved'):
            git_preserved = True
        elif component == 'git_restore' and result.get('restored'):
            git_restored = True
        elif component == 'git' and result.get('permissions'):
            git_permissions_set = True
        elif component == 'framework_cleanup' and result.get('modules_count'):
            modules_cleaned = result.get('modules_count', 0)

    # If nothing happened, don't add a row
    if not (git_preserved or git_restored or git_permissions_set or modules_cleaned > 0):
        return trace_out({})

    # Build summary line
    summary_parts = []
    if git_preserved or git_restored:
        summary_parts.append("repository managed")
    if git_permissions_set:
        summary_parts.append("permissions set")
    if modules_cleaned > 0:
        summary_parts.append(f"{modules_cleaned} modules cleaned")

    summary = ", ".join(summary_parts)

    table_data = TableData()
    table_data.add_row('git_summary', value=summary)

    field_config = FieldConfig()
    field_config.add_simple(['git_summary'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Render Git detail table')
def render_git_detail_table() -> Dict[str, Any]:
    """Render Git-related details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()
    table_data.add_row('git_detail_header', value='Value')

    has_content = False

    # Add git operations
    for result in hook_results:
        component = result.get('component', '')
        if component == 'git_preserve' and result.get('preserved'):
            git_dir = result.get('git_dir', '')
            table_data.add_row('git_preserve', value=git_dir)
            has_content = True
        elif component == 'git_restore' and result.get('restored'):
            git_dir = result.get('git_dir', '')
            table_data.add_row('git_restore', value=git_dir)
            has_content = True
        elif component == 'git' and result.get('permissions'):
            ownership = result.get('ownership', '')
            permissions = result['permissions']
            table_data.add_row('git_permissions_set', value=f"{permissions} ({ownership})")
            has_content = True
        elif component == 'framework_cleanup' and result.get('modules_count'):
            modules_count = result['modules_count']
            table_data.add_row('framework_cleanup', value=f"{modules_count} modules cleaned")
            has_content = True

    if not has_content:
        return trace_out({})

    field_config = FieldConfig()
    field_config.add_header('git_detail_header')
    field_config.add_simple(['git_preserve', 'git_restore', 'git_permissions_set', 'framework_cleanup'])

    git_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='git_operations')
    return trace_out({
        "render_block": git_table_html
    })