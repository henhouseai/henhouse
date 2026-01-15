"""
Maintenance worker deployment hooks
"""
from typing import Dict, Any, Union
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.maintenance.maintenance_start import run_maintenance_start
from hh.deploy.maintenance.maintenance_stop import run_maintenance_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn

log = lambda message: None
warn = lambda message: None

def _init_debug():
    global log, warn
    log = get_log(True)
    warn = get_warn(True)

try:
    _init_debug()
except:
    pass

@register_module_hook('deploy_stop_daemons')
def stop_maintenance_daemon() -> Union[Dict[str, Any], bool]:
    """Stop maintenance worker daemon before deployment."""
    try:
        project_name, _ = detect_project_context()
        if not project_name:
            warn("maintenance hook: Could not detect project name")
            return False

        log(f"maintenance hook: Stopping maintenance daemon for {project_name}")
        run_maintenance_stop(project_name)
        log(f"maintenance hook: Maintenance daemon stopped")

        return {"module": "maintenance", "action": "stop", "status": "stopped"}
    except Exception as e:
        warn(f"maintenance hook: Failed to stop maintenance daemon: {e}")
        return False


@register_module_hook('deploy_restart_daemons')
def restart_maintenance_daemon() -> Union[Dict[str, Any], bool]:
    """Restart maintenance worker daemon after deployment."""
    try:
        project_name, _ = detect_project_context()
        if not project_name:
            warn("maintenance hook: Could not detect project name")
            return False

        log(f"maintenance hook: Starting maintenance daemon for {project_name}")
        maintenance_restart_info = run_maintenance_start(project_name)
        log(f"maintenance hook: Maintenance restart status: {maintenance_restart_info.get('status')}")

        return {"module": "maintenance", "action": "restart", "maintenance_restart": maintenance_restart_info}
    except Exception as e:
        warn(f"maintenance hook: Failed to restart maintenance daemon: {e}")
        return False
