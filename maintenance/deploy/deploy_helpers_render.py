"""
Maintenance deployment render hooks.

Detail table showing individual maintenance daemon status.
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


@register_module_hook('deploy_95_render', 'Contribute Maintenance status to summary')
def render_maintenance_summary_contribution() -> Dict[str, Any]:
    """Contribute maintenance daemon status to deployment summary table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find Maintenance data
    maint_restart_data = None
    workers_deployed = []

    for result in hook_results:
        if result.get('module') == 'maintenance':
            if result.get('action') == 'restart':
                maint_restart_data = result.get('maintenance_restart', {})
            elif result.get('action') == 'deploy_workers':
                workers_deployed = result.get('maintenance_workers_deployed', [])

    if not maint_restart_data and not workers_deployed:
        return trace_out({})

    table_data = TableData()

    # Count total daemons and determine status
    if maint_restart_data:
        daemon_count = len([k for k, v in maint_restart_data.items() if isinstance(v, dict) and v])
        if daemon_count > 0:
            main_status = maint_restart_data.get('main', {}).get('status', 'unknown')
            table_data.add_row('maintenance_summary', value=f"{daemon_count} daemon ({main_status})")
        else:
            table_data.add_row('maintenance_summary', value="No active maintenance daemons")
    elif workers_deployed:
        table_data.add_row('maintenance_summary', value=f"{len(workers_deployed)} worker(s) deployed")
    else:
        table_data.add_row('maintenance_summary', value="No maintenance processes")

    field_config = FieldConfig()
    field_config.add_simple(['maintenance_summary'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
