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


@register_module_hook('deploy_95_render', 'Render Maintenance daemon detail table')
def render_maintenance_detail_table() -> Dict[str, Any]:
    """Render Maintenance daemon details as a separate full table."""
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
    table_data.add_row('maint_header', daemon='Daemon', status='Status', user='User', deployed='Deployed')

    # Show each daemon from restart data
    if maint_restart_data:
        for daemon_name, daemon_info in maint_restart_data.items():
            if isinstance(daemon_info, dict) and daemon_info:
                status = daemon_info.get('status', 'unknown')
                user = daemon_info.get('user', '')
                log_file = daemon_info.get('log_file', '')
                deployed = 'Yes' if daemon_info.get('deployed', False) else 'No'

                table_data.add_row('maint_row',
                                 daemon=daemon_name,
                                 status=status,
                                 user=user,
                                 deployed=deployed)

    # Show deployed workers if no restart data
    if not maint_restart_data and workers_deployed:
        for worker in workers_deployed:
            table_data.add_row('maint_row',
                             daemon='Worker',
                             status='Deployed',
                             user='',
                             deployed=worker)

    field_config = FieldConfig()
    field_config.add_header('maint_header')
    field_config.add_simple(['maint_row'])

    # Return as full render_block
    maint_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='maintenance_daemons')
    return trace_out({
        "render_block": maint_table_html
    })
