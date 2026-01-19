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


@register_module_hook('deploy_95_render', 'Render Maintenance daemon detail table')
def render_maintenance_detail_table() -> Dict[str, Any]:
    """Render Maintenance daemon details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find Maintenance restart data
    maint_restart_data = None
    for result in hook_results:
        if result.get('module') == 'maintenance' and result.get('action') == 'restart':
            maint_restart_data = result.get('maintenance_restart', {})
            break

    if not maint_restart_data:
        return trace_out({})

    table_data = TableData()
    table_data.add_row('maint_detail_header', name='Daemon', path='Path', permissions='Permissions')

    has_content = False

    # Status to field type mapping
    status_field_map = {
        'started': 'maint_started',
        'restarted': 'maint_restarted',
        'stopped': 'maint_stopped',
        'failed': 'maint_failed',
        'error': 'maint_error',
        'not_found': 'maint_error',
        'user_not_found': 'maint_error'
    }

    # Get project name for fallback path construction
    project_name = 'unknown'
    for result in hook_results:
        if result.get('project_name'):
            project_name = result['project_name']
            break

    # Main maintenance daemon
    main_daemon = maint_restart_data.get('main', {})
    if main_daemon and isinstance(main_daemon, dict):
        status = main_daemon.get('status', 'unknown')
        worker_path = main_daemon.get('worker_path', f"/srv/{project_name}/{project_name}_maintenance.py")
        field_type = status_field_map.get(status, 'maint_error')
        table_data.add_row(field_type, name='main', path=worker_path, permissions='755')
        has_content = True

    # EXT maintenance daemons
    ext_daemons = maint_restart_data.get('ext', {})
    if ext_daemons and isinstance(ext_daemons, dict):
        for daemon_name, daemon_data in ext_daemons.items():
            if daemon_data and isinstance(daemon_data, dict):
                status = daemon_data.get('status', 'unknown')
                worker_path = daemon_data.get('worker_path', f"/srv/{project_name}/{project_name}_maintenance_{daemon_name}.py")
                field_type = status_field_map.get(status, 'maint_error')
                table_data.add_row(field_type, name=daemon_name, path=worker_path, permissions='755')
                has_content = True

    if not has_content:
        return trace_out({})

    field_config = FieldConfig()
    field_config.add_header('maint_detail_header')
    field_config.add_simple(['maint_started', 'maint_restarted', 'maint_stopped'])
    field_config.add_simple_color('maint_failed', 'red')
    field_config.add_simple_color('maint_error', 'red')

    # Return as full render_block
    maint_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='maintenance_daemons')
    return trace_out({
        "render_block": maint_table_html
    })
