"""
Project deployment hooks for framework project management.
"""

import subprocess
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
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

@register_module_hook('deploy_permissions_special')
def set_git_permissions() -> dict:
    """Set special permissions for git directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project permissions hook: Could not detect project name")
            return {"status": "error", "component": "git", "error": "no_project"}

        gateway = get_gateway()
        dest = Path("/srv") / project_name
        git_dir = dest / 'git'

        if not git_dir.exists():
            log("project permissions hook: Git directory does not exist, skipping git permissions")
            return {"status": "skipped", "component": "git", "reason": "no_git_dir"}

        # Get project user info
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"project permissions hook: User not found: {project_highest_user}")
            return {"status": "error", "component": "git", "error": "user_not_found"}

        project_highest_uid = user_info["uid"]

        # Set git directory permissions (770/660 - more permissive than base)
        # Git needs group write for collaboration
        subprocess.run(['chown', '-R', f'{project_highest_uid}:{project_name}', str(git_dir)], check=True)
        subprocess.run(['find', str(git_dir), '-type', 'd', '-exec', 'chmod', '770', '{}', ';'], check=True)
        subprocess.run(['find', str(git_dir), '-type', 'f', '-exec', 'chmod', '660', '{}', ';'], check=True)

        log(f"project permissions hook: Set git directory permissions: {project_highest_user}:{project_name} (770/660)")
        return {"status": "completed", "component": "git", "permissions": "770/660", "ownership": f"{project_highest_user}:{project_name}"}

    except Exception as e:
        warn(f"project permissions hook: Failed to set git permissions: {e}")
        report_error("backend", f"project permissions hook: Failed to set git permissions: {e}")
        return {"status": "error", "component": "git", "error": str(e)}