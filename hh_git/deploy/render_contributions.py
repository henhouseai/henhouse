"""
Git deployment render contributions for hh_git module.

Contributes Git-related permissions and operations to deployment summary.
"""
from typing import Dict, Any
from hh.render.render import TableData, FieldConfig
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


@register_module_hook('deploy_95_render', 'Contribute Git permissions to summary')
def render_git_permissions_contribution() -> Dict[str, Any]:
    """Contribute Git-related permissions to deployment summary table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find Git-related permission data
    git_perms = []
    for result in hook_results:
        if result.get('component') == 'git' and result.get('permissions'):
            ownership = result.get('ownership', '')
            permissions = result['permissions']
            git_perms.append(f"Repository: {permissions} ({ownership})")

    if not git_perms:
        return trace_out({})

    table_data = TableData()
    for perm in git_perms:
        table_data.add_row('git_permissions', value=perm)

    field_config = FieldConfig()
    field_config.add_simple(['git_permissions'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Contribute Git operations to summary')
def render_git_operations_contribution() -> Dict[str, Any]:
    """Contribute Git-related operations to deployment summary table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find Git-related operation data
    git_ops = []
    for result in hook_results:
        component = result.get('component', '')
        if component == 'git_preserve' and result.get('preserved'):
            git_dir = result.get('git_dir', '')
            git_ops.append(f"Git preserved: {git_dir}")
        elif component == 'git_restore' and result.get('restored'):
            git_dir = result.get('git_dir', '')
            git_ops.append(f"Git restored: {git_dir}")

    if not git_ops:
        return trace_out({})

    table_data = TableData()
    for op in git_ops:
        table_data.add_row('git_operations', value=op)

    field_config = FieldConfig()
    field_config.add_simple(['git_operations'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })