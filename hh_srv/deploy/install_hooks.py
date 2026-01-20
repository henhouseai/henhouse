"""
Server infrastructure module installation hooks.

Handles /srv directory checks and deployment permissions.
"""

from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_module_hook('install_10_conflict_check', 'Check for existing /srv directory')
def check_srv_conflicts() -> Dict[str, Any]:
    """Check for existing /srv/{project} directory."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, _ = detect_project_context()
    if not project_name:
        return trace_out({"status": "error", "error": "Could not detect project name"})

    srv_project = Path(f'/srv/{project_name}')
    if srv_project.exists():
        error_msg = f"Project directory already exists: {srv_project}"
        warn(f"hh_srv: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    log(f"hh_srv: No /srv directory conflicts found")
    return trace_out({"status": "success"})


@register_module_hook('install_60_permissions', 'Set deployment ownership and permissions')
def setup_deployment_permissions() -> Dict[str, Any]:
    """Set deployment ownership and permissions."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, _ = detect_project_context()
    if not project_name:
        error_msg = "Could not detect project name"
        warn(f"hh_srv: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        from hh_srv.deploy.http.deploy_helpers import setup_deployment_ownership_and_permissions
        setup_deployment_ownership_and_permissions(project_name)

        log(f"hh_srv: Set deployment ownership and permissions for {project_name}")
        return trace_out({
            "status": "success",
            "project_name": project_name
        })

    except Exception as e:
        error_msg = f"Failed to set deployment permissions: {str(e)}"
        warn(f"hh_srv: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_95_render', 'Render server infrastructure summary')
def render_srv_summary() -> Dict[str, Any]:
    """Render server infrastructure summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - can add srv-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
