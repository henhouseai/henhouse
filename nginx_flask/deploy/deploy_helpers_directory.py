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


@register_module_hook('deploy_sterilize_directory')
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


@register_module_hook('deploy_modules')
def deploy_discovered_modules() -> dict:
    """Deploy all discovered modules to destination."""
    import shutil
    from pathlib import Path
    from hh.deploy.deploy_utils import detect_project_context, get_active_modules
    from hh.gateway.gateway import get_gateway
    from hh.gateway.error.error_store import report_error

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask directory: Could not detect project name")
            return {"status": "error", "component": "modules", "error": "no_project"}

        gateway = get_gateway()
        source = current_path
        dest = Path("/srv") / project_name

        modules = get_active_modules()
        deployed_modules = []

        for module in modules:
            module_source = source / module.path
            module_dest = dest / module.path
            try:
                if module_source.exists() and module_source.is_dir():
                    shutil.copytree(module_source, module_dest)
                    deployed_modules.append(module.name)
                    log(f"nginx_flask directory: Deployed module {module.name}: {module_source} -> {module_dest}")
                else:
                    warn(f"nginx_flask directory: Module source not found: {module_source}")
            except Exception as e:
                warn(f"nginx_flask directory: Failed to deploy module {module.name}: {e}")
                report_error("backend", f"nginx_flask directory: Failed to deploy module {module.name}: {e}")

        log(f"nginx_flask directory: Deployed {len(deployed_modules)} modules")

        return {
            "status": "completed",
            "action": "deploy_modules",
            "modules_deployed": deployed_modules,
            "modules_count": len(deployed_modules)
        }

    except Exception as e:
        warn(f"nginx_flask directory: Failed to deploy modules: {e}")
        report_error("backend", f"nginx_flask directory: Failed to deploy modules: {e}")
        return {"status": "error", "component": "modules", "error": str(e)}


@register_module_hook('deploy_framework_cleanup')
def cleanup_module_deploy_directories() -> dict:
    """Clean module deploy directories but preserve whitelisted items."""
    import shutil
    from pathlib import Path
    from hh.deploy.deploy_utils import detect_project_context, get_active_modules, load_whitelist_with_extensions
    from hh.gateway.gateway import get_gateway
    from hh.gateway.error.error_store import report_error

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask directory: Could not detect project name")
            return {"status": "error", "component": "framework_cleanup", "error": "no_project"}

        gateway = get_gateway()
        dest = Path("/srv") / project_name

        active_modules = get_active_modules(force_regenerate=True)
        module_names = {module.name for module in active_modules}
        log(f"nginx_flask directory: Active modules for deploy cleanup: {sorted(module_names)}")

        DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'DEPLOY_WHITELIST')
        cleaned_modules = []

        # Clean deploy directories for all active modules
        for module_name in sorted(module_names):
            module_deploy_dir = dest / module_name / 'deploy'
            module_preserved_items = {}

            try:
                if module_deploy_dir.exists():
                    # Find whitelisted items for this module
                    module_whitelist_items = [
                        item for item in DEPLOY_WHITELIST
                        if item.startswith(f'{module_name}/deploy/')
                    ]

                    # Temporarily move whitelisted items out
                    for full_item_path in module_whitelist_items:
                        item_path = dest / full_item_path
                        if item_path.exists():
                            # Create a safe temp name from the full path
                            temp_name = full_item_path.replace('/', '_').replace('.', '_')
                            temp_path = dest / f".{project_name}_{temp_name}_tmp"

                            # Clean up existing temp if it exists
                            if temp_path.exists():
                                if temp_path.is_dir():
                                    shutil.rmtree(temp_path)
                                else:
                                    temp_path.unlink()

                            # Move item to temp location
                            shutil.move(str(item_path), str(temp_path))
                            module_preserved_items[full_item_path] = (item_path, temp_path)
                            log(f"nginx_flask directory: Temporarily moved {full_item_path}: {item_path} -> {temp_path}")

                    # Remove entire module deploy directory contents
                    shutil.rmtree(module_deploy_dir)
                    log(f"nginx_flask directory: Removed {module_name}/deploy directory: {module_deploy_dir}")

                    # Recreate module deploy directory and restore preserved items
                    module_deploy_dir.mkdir(parents=True, exist_ok=True)
                    for full_item_path, (original_path, temp_path) in module_preserved_items.items():
                        if temp_path.exists():
                            restored_path = dest / full_item_path
                            # Ensure parent directory exists
                            restored_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(temp_path), str(restored_path))
                            log(f"nginx_flask directory: Restored {full_item_path}: {restored_path}")

                    cleaned_modules.append(module_name)

            except Exception as e:
                warn(f"nginx_flask directory: Failed to clean {module_name}/deploy directory: {e}")
                report_error("backend", f"nginx_flask directory: Failed to clean {module_name}/deploy directory: {e}")

        return {
            "status": "completed",
            "component": "framework_cleanup",
            "modules_cleaned": cleaned_modules,
            "modules_count": len(cleaned_modules)
        }

    except Exception as e:
        warn(f"nginx_flask directory: Failed to cleanup module deploy directories: {e}")
        report_error("backend", f"nginx_flask directory: Failed to cleanup module deploy directories: {e}")
        return {"status": "error", "component": "framework_cleanup", "error": str(e)}
