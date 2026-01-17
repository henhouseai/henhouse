"""
Flask deployment render hooks for hh_flask module.

Detail table showing individual Flask daemon status.
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


@register_module_hook('deploy_95_render', 'Render Flask daemon detail table')
def render_flask_detail_table() -> Dict[str, Any]:
    """Render Flask daemon details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find Flask restart data
    flask_restart_data = None
    flask_deployed = []
    media_deployed = False

    for result in hook_results:
        if result.get('module') == 'hh_flask':
            if result.get('action') == 'restart':
                flask_restart_data = result.get('flask_restart', {})
            elif result.get('action') == 'deploy_apps':
                flask_deployed = result.get('flask_deployed', [])
                media_deployed = result.get('media_deployed', False)

    if not flask_restart_data and not flask_deployed:
        return trace_out({})

    table_data = TableData()
    table_data.add_row('flask_detail_header', value='')

    field_names = []

    # Show each daemon from restart data
    daemons = flask_restart_data.get('daemons', []) if flask_restart_data else []
    for daemon in daemons:
        tier = daemon.get('tier', 'unknown')
        status = daemon.get('status', 'unknown')
        port = daemon.get('port', '?')
        user = daemon.get('user', '')
        value = f"{status} (port {port})"
        if user:
            value += f" as {user}"
        field_type = f'daemon_{tier}'
        table_data.add_row(field_type, value=value)
        field_names.append(field_type)

    # Show deployed apps if no restart data
    if not daemons and flask_deployed:
        for app in flask_deployed:
            table_data.add_row('deployed_app', value=app)
            field_names.append('deployed_app')
        if media_deployed:
            table_data.add_row('media_server', value='deployed')
            field_names.append('media_server')

    if not field_names:
        return trace_out({})

    field_config = FieldConfig()
    field_config.add_header('flask_detail_header')
    # Use unique field names (dedup while preserving order)
    unique_fields = list(dict.fromkeys(field_names))
    field_config.add_simple(unique_fields)

    # Return as full render_block
    flask_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='flask_daemons')
    return trace_out({
        "render_block": flask_table_html
    })
