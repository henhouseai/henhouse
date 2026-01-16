"""
Client files deployment helper for nginx_flask module.

Handles deployment of client files (whitelisted top-level files).
"""
import shutil
from pathlib import Path
from typing import Dict, Any, List
from hh.deploy.deploy_utils import detect_project_context, load_whitelist_with_extensions
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


def deploy_client_files_helper() -> Dict[str, Any]:
    """Deploy client files from CLIENT_WHITELIST to deployment directory."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    source = current_path
    dest = Path("/srv") / project_name

    # Load CLIENT_WHITELIST
    CLIENT_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'CLIENT_WHITELIST')

    deployed_files: List[str] = []

    for rel_path in CLIENT_WHITELIST:
        src = source / rel_path
        if src.exists():
            dst = dest / src.name
            shutil.copy2(src, dst)
            deployed_files.append(rel_path)
            log(f"nginx_flask clients: Deployed client file: {rel_path}")
        else:
            log(f"nginx_flask clients: Client file not found: {rel_path}")

    log(f"nginx_flask clients: Client file deployment complete - {len(deployed_files)} files")

    return {
        "status": "completed",
        "component": "client_files",
        "files_deployed": len(deployed_files),
        "files": deployed_files
    }
