"""
Client files deployment helper for nginx_flask module.

Handles deployment of client files (whitelisted top-level files).
"""
import shutil
from pathlib import Path
from typing import Dict, Any, List
from hh.deploy.deploy_utils import detect_project_context, load_whitelist_with_extensions
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


@register_module_hook('deploy_50_client_files', 'Deploy client files from CLIENT_WHITELIST to deployment directory')
def deploy_client_files() -> Dict[str, Any]:
    """Deploy client files from CLIENT_WHITELIST to deployment directory."""
    trace_in()

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

    return trace_out({
        "status": "completed",
        "component": "client_files",
        "files_deployed": len(deployed_files),
        "files": deployed_files
    })
