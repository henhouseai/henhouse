"""
Directory sterilization helper for nginx_flask module.

Handles clearing and preparing the deployment directory.
"""
import shutil
from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn

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


def sterilize_deployment_directory_helper() -> Dict[str, Any]:
    """Sterilize deployment directory by removing all contents except preserved items."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    dest = Path("/srv") / project_name

    if dest.exists():
        # Remove all contents
        removed_count = 0
        for item in dest.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                log(f"nginx_flask directory: Removed: {item}")
                removed_count += 1
            except Exception as e:
                warn(f"nginx_flask directory: Failed to remove {item}: {e}")
        log(f"nginx_flask directory: Sterilized deployment directory: {dest}")
        action = "sterilized"
    else:
        dest.mkdir(parents=True, exist_ok=True)
        log(f"nginx_flask directory: Created deployment directory: {dest}")
        removed_count = 0
        action = "created"

    return {
        "status": "completed",
        "component": "directory_sterilization",
        "directory": str(dest),
        "action": action,
        "items_removed": removed_count
    }
