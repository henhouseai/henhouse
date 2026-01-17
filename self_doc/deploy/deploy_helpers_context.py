"""
Context deployment helper for nginx_flask module.

Handles deployment of context files and folders.
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


def should_ignore_context_path(directory: str, contents: List[str]) -> List[str]:
    """
    Ignore function for context folder deployment.

    Ignores common development artifacts that shouldn't be deployed.
    """
    ignored = []
    ignore_patterns = {
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.git',
        '.gitignore',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        'Thumbs.db'
    }

    for item in contents:
        if item in ignore_patterns or item.endswith(('.pyc', '.pyo', '.pyd')):
            ignored.append(item)

    return ignored


@register_module_hook('deploy_55_context', 'Deploy context folders and files to deployment directory')
def deploy_context() -> Dict[str, Any]:
    """Deploy context folders and files to deployment directory."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    source = current_path
    dest = Path("/srv") / project_name

    # Load CONTEXT_WHITELIST
    CONTEXT_WHITELIST = load_whitelist_with_extensions('context_whitelist', 'CONTEXT_WHITELIST')

    deployed_items: List[str] = []
    file_count = 0
    dir_count = 0

    for item_str in CONTEXT_WHITELIST:
        source_item = source / item_str
        if source_item.exists():
            dest_item = dest / 'context' / item_str
            if source_item.is_dir():
                # Handle directories
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(source_item, dest_item, ignore=should_ignore_context_path)
                deployed_items.append(item_str)
                dir_count += 1
                log(f"nginx_flask context: Deployed context folder: {item_str} -> context/{item_str}")
            elif source_item.is_file():
                # Handle files
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_item, dest_item)
                deployed_items.append(item_str)
                file_count += 1
                log(f"nginx_flask context: Deployed context file: {item_str} -> context/{item_str}")
            else:
                log(f"nginx_flask context: Context item is neither file nor directory: {item_str}")
        else:
            log(f"nginx_flask context: Context item not found: {item_str}")

    log(f"nginx_flask context: Context deployment complete - {file_count} files, {dir_count} directories")

    return trace_out({
        "status": "completed",
        "component": "context_deployment",
        "files_deployed": file_count,
        "directories_deployed": dir_count,
        "total_items": len(deployed_items),
        "items": deployed_items
    })
