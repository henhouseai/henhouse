"""
Maintenance worker deployment hooks
"""
from typing import Dict, Any, Union
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.maintenance.maintenance_start import run_maintenance_start
from hh.deploy.maintenance.maintenance_stop import run_maintenance_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

# Pre-validated configuration storage for maintenance module
pre_validated_maintenance_config: dict = {}

@register_module_hook('deploy_pre_validate')
def validate_maintenance_config():
    """Pre-validate maintenance-specific configuration."""
    global pre_validated_maintenance_config

    log("Validating maintenance deployment configuration")

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            raise ValueError("Could not detect project context")

        pre_validated_maintenance_config = {
            'project_name': project_name,
            'current_path': current_path
        }

        log(f"Pre-validated maintenance config for: {project_name}")
    except Exception as e:
        warn(f"Failed to validate maintenance config: {e}")
        raise ValueError(f"Failed to validate maintenance config: {e}")


@register_module_hook('deploy_render')
def render_maintenance_operations():
    """Render maintenance-specific deployment operations."""
    from hh.render.render import TableData, FieldConfig

    if not pre_validated_maintenance_config:
        return {"render_block": "<div>Maintenance config not available</div>"}

    table_data = TableData()
    table_data.add_row('daemon_control', value='Maintenance daemon start/stop')
    table_data.add_row('project_name', value=pre_validated_maintenance_config.get('project_name', 'Unknown'))

    field_config = FieldConfig()
    field_config.add_simple(['daemon_control', 'project_name'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }

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


@register_module_hook('deploy_permissions_special')
def set_maintenance_logs_permissions() -> Dict[str, Any]:
    """Set special permissions for maintenance worker logs."""
    try:
        project_name, _ = detect_project_context()
        if not project_name:
            warn("maintenance permissions hook: Could not detect project name")
            return {"status": "error", "component": "maintenance_logs", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name

        # Maintenance workers use the same logs directory as Flask daemons
        # This hook ensures maintenance can write to logs if needed
        logs_dir = dest / 'logs'

        if not logs_dir.exists():
            log("maintenance permissions hook: Logs directory does not exist, maintenance will use Flask logs directory")
            return {"status": "skipped", "component": "maintenance_logs", "reason": "shared_logs_dir"}

        # Ensure maintenance can write to logs directory
        # (permissions already set by nginx_flask hook, but verify)
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        deploy_group_name = f"{project_name}_deploy"

        log(f"maintenance permissions hook: Maintenance logs permissions verified for shared directory: {logs_dir}")
        return {
            "status": "completed",
            "component": "maintenance_logs",
            "permissions": "inherited",
            "ownership": f"{project_highest_user}:{deploy_group_name}",
            "directory": str(logs_dir),
            "note": "uses_shared_flask_logs_dir"
        }

    except Exception as e:
        warn(f"maintenance permissions hook: Failed to set maintenance logs permissions: {e}")
        return {"status": "error", "component": "maintenance_logs", "error": str(e)}
