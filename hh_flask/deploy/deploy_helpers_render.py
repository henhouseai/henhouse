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


@register_module_hook('deploy_95_render', 'Contribute Flask summary')
def render_flask_summary_contribution() -> Dict[str, Any]:
    """Contribute Flask summary to deployment summary table (1 line)."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Collect flask activity
    daemons_started = 0
    daemons_deployed = 0

    for result in hook_results:
        if result.get('module') == 'hh_flask':
            if result.get('action') == 'restart':
                flask_restart = result.get('flask_restart', {})
                daemons = flask_restart.get('daemons', [])
                daemons_started = len(daemons)
            elif result.get('action') == 'deploy_apps':
                flask_deployed = result.get('flask_deployed', [])
                daemons_deployed = len(flask_deployed)

    if daemons_started == 0 and daemons_deployed == 0:
        return trace_out({})

    # Build summary line
    if daemons_started > 0:
        summary = f"{daemons_started} daemons started"
    elif daemons_deployed > 0:
        summary = f"{daemons_deployed} apps deployed"
    else:
        summary = "no activity"

    table_data = TableData()
    table_data.add_row('flask_summary', value=summary)

    field_config = FieldConfig()
    field_config.add_simple(['flask_summary'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


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
    table_data.add_row('flask_detail_header', status='Status', permissions='Permissions')

    # Show each daemon from restart data
    daemons = flask_restart_data.get('daemons', []) if flask_restart_data else []
    for daemon in daemons:
        tier = daemon.get('tier', 'unknown')
        status = daemon.get('status', 'unknown')
        port = daemon.get('port', '?')
        permissions = '755'  # Default Flask permissions

        # Map tier to field type
        tier_field_map = {
            'guest': 'daemon_guest',
            'verified': 'daemon_verified',
            'admin': 'daemon_admin',
            'root': 'daemon_root',
            'media': 'daemon_media'
        }
        field_type = tier_field_map.get(tier, 'daemon_guest')

        table_data.add_row(field_type, status=f"{status} (port {port})", permissions=permissions)

    # Show deployed apps if no restart data (fallback - shouldn't normally happen)
    if not daemons and flask_deployed:
        for app in flask_deployed:
            table_data.add_row('daemon_guest', status='Deployed', permissions='755')
        if media_deployed:
            table_data.add_row('daemon_media', status='Deployed', permissions='755')

    if not daemons and not flask_deployed:
        return trace_out({})

    field_config = FieldConfig()
    field_config.add_header('flask_detail_header')
    field_config.add_simple(['daemon_guest', 'daemon_verified', 'daemon_admin', 'daemon_root', 'daemon_media'])

    # Return as full render_block
    flask_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='flask_daemons')
    return trace_out({
        "render_block": flask_table_html
    })
