"""
Flask module installation hooks.

Handles Flask-specific configuration and port management.
"""

from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.deploy.install_helpers_conflicts import check_port_conflict

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

# Module-scoped config storage
flask_config: Dict[str, Any] = {}


@register_module_hook('install_01_template_contribute', 'Contribute Flask template sections')
def contribute_flask_template() -> Dict[str, Any]:
    """Contribute Flask-specific configuration to install template."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    if INSTALL_CONFIG["mode"] != "template":
        return trace_out({"status": "skipped"})

    flask_template = [
        "# ========================================",
        "# Flask Daemon Configuration",
        "# ========================================",
        "# Flask daemon starting port (reserves 100 ports: start_port through start_port+99)",
        "flask_start_port = 5001",
        "",
    ]

    INSTALL_CONFIG["template_lines"].extend(flask_template)
    log(f"hh_flask: Added {len(flask_template)} lines to template")
    return trace_out({"status": "success", "lines_contributed": len(flask_template)})


@register_module_hook('install_05_pre_validate', 'Validate Flask configuration')
def validate_flask_config() -> Dict[str, Any]:
    """Validate Flask-specific configuration."""
    trace_in()
    global flask_config
    from hh.deploy.install_hooks import INSTALL_CONFIG

    if INSTALL_CONFIG["mode"] != "install":
        return trace_out({"status": "skipped"})

    parsed = INSTALL_CONFIG["parsed_config"]

    # Validate flask_start_port
    port_str = parsed.get("flask_start_port", "5001").strip()
    try:
        flask_start_port = int(port_str)
        if flask_start_port < 1024 or flask_start_port > 65435:
            raise ValueError(f"Port {flask_start_port} out of valid range (1024-65435)")
    except ValueError as e:
        error_msg = f"Invalid flask_start_port: {e}"
        warn(f"hh_flask: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    flask_config["flask_start_port"] = flask_start_port
    log(f"hh_flask: Validated flask_start_port={flask_start_port}")
    return trace_out({"status": "success", "flask_start_port": flask_start_port})


@register_module_hook('install_10_conflict_check', 'Check Flask port conflicts')
def check_port_conflicts() -> Dict[str, Any]:
    """Check for port conflicts with other active installations."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, _ = detect_project_context()
    if not project_name:
        return trace_out({"status": "error", "error": "Could not detect project name"})

    flask_start_port = flask_config.get("flask_start_port", 5001)

    # Check for port conflicts using helper
    conflict_msg = check_port_conflict(flask_start_port, project_name)
    if conflict_msg:
        warn(f"hh_flask: {conflict_msg}")
        report_error("action", conflict_msg)
        return trace_out({"status": "error", "error": conflict_msg})

    log(f"hh_flask: No port conflicts found for port {flask_start_port}")
    return trace_out({"status": "success", "port_range": f"{flask_start_port}-{flask_start_port+99}"})


@register_module_hook('install_95_render', 'Render Flask summary')
def render_flask_summary() -> Dict[str, Any]:
    """Render Flask configuration summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - can add Flask-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
