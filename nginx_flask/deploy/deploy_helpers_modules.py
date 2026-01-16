"""
Module deployment helpers for nginx_flask module.

Handles deployment of module files and cleanup of module deploy directories.
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


def deploy_modules_helper() -> Dict[str, Any]:
    """Deploy module files from DEPLOY_WHITELIST to deployment directory."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    source = current_path
    dest = Path("/srv") / project_name

    # Load DEPLOY_WHITELIST
    DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'DEPLOY_WHITELIST')

    deployed_items: List[str] = []
    file_count = 0
    dir_count = 0

    for item_str in DEPLOY_WHITELIST:
        source_item = source / item_str
        if source_item.exists():
            # Preserve the full path structure in destination
            dest_item = dest / item_str

            if source_item.is_dir():
                # Handle directories
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_item, dest_item)
                deployed_items.append(item_str)
                dir_count += 1
                log(f"nginx_flask modules: Deployed directory: {item_str}")
            elif source_item.is_file():
                # Handle files
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                if dest_item.exists():
                    dest_item.unlink()
                shutil.copy2(source_item, dest_item)
                deployed_items.append(item_str)
                file_count += 1
                log(f"nginx_flask modules: Deployed file: {item_str}")
            else:
                log(f"nginx_flask modules: Item is neither file nor directory: {item_str}")
        else:
            log(f"nginx_flask modules: Item not found: {item_str}")

    log(f"nginx_flask modules: Module deployment complete - {file_count} files, {dir_count} directories")

    return {
        "status": "completed",
        "component": "module_deployment",
        "files_deployed": file_count,
        "directories_deployed": dir_count,
        "total_items": len(deployed_items),
        "items": deployed_items
    }


def clean_module_deploy_directories_helper() -> Dict[str, Any]:
    """Clean up module deploy directories after deployment."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    dest = Path("/srv") / project_name

    # Get active modules
    from hh.deploy.deploy_utils import get_active_modules
    modules = get_active_modules()

    cleaned_dirs: List[str] = []

    for module in modules:
        # Remove module's deploy directory from deployed location
        module_deploy_dir = dest / module.path / 'deploy'
        if module_deploy_dir.exists():
            try:
                shutil.rmtree(module_deploy_dir)
                cleaned_dirs.append(f"{module.path}/deploy")
                log(f"nginx_flask modules: Cleaned module deploy directory: {module.path}/deploy")
            except Exception as e:
                warn(f"nginx_flask modules: Failed to clean {module.path}/deploy: {e}")

    log(f"nginx_flask modules: Module deploy directory cleanup complete - {len(cleaned_dirs)} directories")

    return {
        "status": "completed",
        "component": "module_deploy_cleanup",
        "directories_cleaned": len(cleaned_dirs),
        "cleaned_paths": cleaned_dirs
    }
