"""
Directory sterilization helper for nginx_flask module.

Handles clearing and preparing the deployment directory.
"""
import shutil
from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
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


@register_module_hook('deploy_15_sterilize_directory')
def sterilize_deployment_directory() -> Dict[str, Any]:
    """Sterilize deployment directory by removing all contents except preserved items."""
    trace_in()

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

    return trace_out({
        "status": "completed",
        "component": "directory_sterilization",
        "directory": str(dest),
        "action": action,
        "items_removed": removed_count
    })
