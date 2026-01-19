"""
Flask removal hooks for nginx_flask module (hh_flask category).

Handles stopping Flask and maintenance daemons.
"""
from typing import Dict, Any
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.maintenance.maintenance_stop import run_maintenance_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.render.render import TableData, FieldConfig

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


@register_module_hook('remove_20_stop_flask', 'Stop Flask daemons')
def stop_flask_daemons() -> Dict[str, Any]:
    """Stop Flask tier daemons before removal."""
    trace_in()

    project_name, _ = detect_project_context()
    if not project_name:
        warn("Could not detect project name")
        return trace_out({"status": "error", "component": "flask_stop", "error": "no_project"})

    try:
        log(f"Stopping Flask daemons for {project_name}")
        flask_stop_info = run_flask_stop(project_name)
        log("Flask daemons stopped successfully")

        return trace_out({
            "status": "completed",
            "component": "flask_stop",
            "flask_stopped": True,
            "stop_info": flask_stop_info
        })

    except Exception as e:
        warn(f"Failed to stop Flask daemons: {e}")
        report_error("backend", f"Failed to stop Flask daemons: {e}")
        return trace_out({"status": "error", "component": "flask_stop", "error": str(e)})


@register_module_hook('remove_25_stop_maint', 'Stop maintenance daemon')
def stop_maintenance_daemon() -> Dict[str, Any]:
    """Stop maintenance daemon before removal."""
    trace_in()

    project_name, _ = detect_project_context()
    if not project_name:
        warn("Could not detect project name")
        return trace_out({"status": "error", "component": "maint_stop", "error": "no_project"})

    try:
        log(f"Stopping maintenance daemon for {project_name}")
        maint_stop_info = run_maintenance_stop(project_name)
        log("Maintenance daemon stopped successfully")

        return trace_out({
            "status": "completed",
            "component": "maint_stop",
            "maintenance_stopped": True,
            "stop_info": maint_stop_info
        })

    except Exception as e:
        warn(f"Failed to stop maintenance daemon: {e}")
        report_error("backend", f"Failed to stop maintenance daemon: {e}")
        return trace_out({"status": "error", "component": "maint_stop", "error": str(e)})


@register_module_hook('remove_95_render', 'Render Flask removal status')
def render_flask_removal() -> Dict[str, Any]:
    """Render Flask module's removal status (daemons stopped)."""
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Get flask-specific data
    flask_stopped = False
    maintenance_stopped = False

    for result in hook_results:
        if result.get('component') == 'flask_stop':
            flask_stopped = result.get('flask_stopped', False)
        elif result.get('component') == 'maint_stop':
            maintenance_stopped = result.get('maintenance_stopped', False)

    # Summary row
    summary_parts = []
    if flask_stopped:
        summary_parts.append("Flask stopped")
    if maintenance_stopped:
        summary_parts.append("Maintenance stopped")
    summary = ', '.join(summary_parts) if summary_parts else 'No operations'
    table_data.add_row('flask_summary', value=summary)

    field_config = FieldConfig()
    field_config.add_simple(['flask_summary'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }
