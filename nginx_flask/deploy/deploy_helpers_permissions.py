"""
Permissions helper functions for nginx_flask module.

These functions handle special permission setup for Flask logs and site files.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error

log = lambda message: None
warn = lambda message: None

def _init_debug():
    global log, warn
    from hh.gateway.registry.debug import get_log, get_warn
    log = get_log(True)
    warn = get_warn(True)

try:
    _init_debug()
except:
    pass


def set_flask_logs_permissions_helper() -> Dict[str, Any]:
    """Set special permissions for Flask daemon logs directory."""
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
        log(f"nginx_flask permissions: Cleared existing logs directory: {logs_dir}")
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

    log(f"nginx_flask permissions: Created fresh logs directory with group write: {logs_dir}")
    log(f"nginx_flask permissions: Set logs directory ownership: {project_highest_user}:{deploy_group_name}")

    return {
        "status": "completed",
        "component": "flask_logs",
        "permissions": "2775",
        "ownership": f"{project_highest_user}:{deploy_group_name}",
        "directory": str(logs_dir)
    }


def set_site_permissions_helper() -> Dict[str, Any]:
    """Set special permissions for site files (HTML, JS, CSS, etc.)."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    dest = Path("/srv") / project_name
    site_dir = dest / 'site'

    if not site_dir.exists():
        log("nginx_flask permissions: Site directory does not exist, skipping site permissions")
        return {"status": "skipped", "component": "site", "reason": "no_site_dir"}

    # Ensure web-accessible files have proper permissions for nginx
    # Site files should be readable by web server (644 for files, 755 for dirs)

    # Set directory permissions (755 - readable/executable by all, writable by owner)
    subprocess.run(['find', str(site_dir), '-type', 'd', '-exec', 'chmod', '755', '{}', ';'], check=True)

    # Set file permissions (644 - readable by all, writable by owner)
    subprocess.run(['find', str(site_dir), '-type', 'f', '-exec', 'chmod', '644', '{}', ';'], check=True)

    log(f"nginx_flask permissions: Set site directory permissions: 755/644 for {site_dir}")

    return {
        "status": "completed",
        "component": "site",
        "permissions": "755/644",
        "directory": str(site_dir),
        "note": "web_accessible_permissions"
    }
