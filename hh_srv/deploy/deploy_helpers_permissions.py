"""
Site permissions hooks for hh_srv module.

These functions handle special permission setup for site files.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.module_hooks import register_module_hook

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


@register_module_hook('deploy_75_permissions_special', 'Set site file permissions')
def set_site_permissions() -> Dict[str, Any]:
    """Set special permissions for site files (HTML, JS, CSS, etc.)."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    dest = Path("/srv") / project_name
    site_dir = dest / 'site'

    if not site_dir.exists():
        log("hh_srv permissions: Site directory does not exist, skipping site permissions")
        return trace_out({"status": "skipped", "component": "site", "reason": "no_site_dir"})

    # Ensure web-accessible files have proper permissions for nginx
    # Site files should be readable by web server (644 for files, 755 for dirs)

    # Set directory permissions (755 - readable/executable by all, writable by owner)
    subprocess.run(['find', str(site_dir), '-type', 'd', '-exec', 'chmod', '755', '{}', ';'], check=True)

    # Set file permissions (644 - readable by all, writable by owner)
    subprocess.run(['find', str(site_dir), '-type', 'f', '-exec', 'chmod', '644', '{}', ';'], check=True)

    log(f"hh_srv permissions: Set site directory permissions: 755/644 for {site_dir}")

    return trace_out({
        "status": "completed",
        "component": "site",
        "permissions": "755/644",
        "directory": str(site_dir),
        "note": "web_accessible_permissions"
    })
