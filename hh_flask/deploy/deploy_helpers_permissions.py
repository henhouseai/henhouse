"""
Flask permissions hooks.

These functions handle special permission setup for Flask logs.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
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


@register_module_hook('deploy_75_permissions_special', 'Set Flask log permissions')
def set_flask_logs_permissions() -> Dict[str, Any]:
    """Set special permissions for Flask daemon logs directory."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    import shutil
    gateway = get_gateway()
    dest = Path("/srv") / project_name
    logs_dir = dest / 'logs'

    # Clear existing logs directory and recreate
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
        log(f"hh_flask permissions: Cleared existing logs directory: {logs_dir}")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Set group write permissions for logs (2775)
    gateway.files.chmod(str(logs_dir), 0o2775)

    # Set ownership so Flask daemons can write logs
    project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
    user_info = gateway.os.get_user_by_name(project_highest_user)
    if not user_info:
        raise ValueError(f"User not found: {project_highest_user}")

    project_highest_uid = user_info["uid"]
    deploy_group_name = f"{project_name}_deploy"
    subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(logs_dir)], check=True)

    log(f"hh_flask permissions: Created fresh logs directory with group write: {logs_dir}")
    log(f"hh_flask permissions: Set logs directory ownership: {project_highest_user}:{deploy_group_name}")

    return trace_out({
        "status": "completed",
        "component": "flask_logs",
        "permissions": "2775",
        "ownership": f"{project_highest_user}:{deploy_group_name}",
        "directory": str(logs_dir)
    })
