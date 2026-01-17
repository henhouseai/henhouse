"""
Project deployment hooks for framework project management.
"""

import subprocess
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

# Debug initialization
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

@register_module_hook('deploy_75_permissions_special', 'Set special permissions for git directory')
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


@register_module_hook('deploy_10_git_preserve_ops', 'Preserve git directory by moving to temp location')
def preserve_git_directory() -> dict:
    """Preserve git directory by moving it to a temporary location."""
    import shutil

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project git hook: Could not detect project name")
            return {"status": "error", "component": "git_preserve", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        git_dir = dest / 'git'
        temp_git_path = dest.parent / f'{project_name}_git'

        if not git_dir.exists():
            log("project git hook: Git directory does not exist, nothing to preserve")
            return {"status": "skipped", "component": "git_preserve", "reason": "no_git_dir"}

        # Clean up any existing temp git directory
        if temp_git_path.exists():
            shutil.rmtree(temp_git_path)
            log(f"project git hook: Removed existing temporary git directory: {temp_git_path}")

        # Move git directory to temp location
        shutil.move(str(git_dir), str(temp_git_path))
        log(f"project git hook: Preserved git directory to: {temp_git_path}")

        return {
            "status": "completed",
            "component": "git_preserve",
            "git_dir": str(git_dir),
            "temp_path": str(temp_git_path),
            "preserved": True
        }

    except Exception as e:
        warn(f"project git hook: Failed to preserve git directory: {e}")
        report_error("backend", f"project git hook: Failed to preserve git directory: {e}")
        return {"status": "error", "component": "git_preserve", "error": str(e)}


@register_module_hook('deploy_20_git_restore_ops', 'Restore git directory from temporary location')
def restore_git_directory() -> dict:
    """Restore git directory from temporary location."""
    import shutil

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project git hook: Could not detect project name")
            return {"status": "error", "component": "git_restore", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        git_dir = dest / 'git'
        temp_git_path = dest.parent / f'{project_name}_git'

        if not temp_git_path.exists():
            warn(f"project git hook: Temporary git directory not found: {temp_git_path}")
            return {"status": "error", "component": "git_restore", "error": "temp_git_missing"}

        # Move git directory back to its original location
        shutil.move(str(temp_git_path), str(git_dir))
        log(f"project git hook: Restored git directory to: {git_dir}")

        return {
            "status": "completed",
            "component": "git_restore",
            "git_dir": str(git_dir),
            "temp_path": str(temp_git_path),
            "restored": True
        }

    except Exception as e:
        warn(f"project git hook: Failed to restore git directory: {e}")
        report_error("backend", f"project git hook: Failed to restore git directory: {e}")
        return {"status": "error", "component": "git_restore", "error": str(e)}


@register_module_hook('deploy_25_modules', 'Deploy all discovered modules to destination')
def deploy_discovered_modules() -> dict:
    """Deploy all discovered modules to destination."""
    import shutil

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project modules hook: Could not detect project name")
            return {"status": "error", "component": "modules", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        source = current_path
        dest = Path("/srv") / project_name

        from hh.deploy.deploy_utils import get_active_modules
        modules = get_active_modules()
        deployed_modules = []

        for module in modules:
            module_source = source / module.path
            module_dest = dest / module.path
            try:
                if module_source.exists() and module_source.is_dir():
                    shutil.copytree(module_source, module_dest)
                    deployed_modules.append(module.name)
                    log(f"project modules hook: Deployed module {module.name}: {module_source} -> {module_dest}")
                else:
                    warn(f"project modules hook: Module source not found: {module_source}")
            except Exception as e:
                warn(f"project modules hook: Failed to deploy module {module.name}: {e}")
                report_error("backend", f"project modules hook: Failed to deploy module {module.name}: {e}")

        log(f"project modules hook: Deployed {len(deployed_modules)} modules")

        return {
            "status": "completed",
            "action": "deploy_modules",
            "modules_deployed": deployed_modules,
            "modules_count": len(deployed_modules)
        }

    except Exception as e:
        warn(f"project modules hook: Failed to deploy modules: {e}")
        report_error("backend", f"project modules hook: Failed to deploy modules: {e}")
        return {"status": "error", "component": "modules", "error": str(e)}


@register_module_hook('deploy_30_framework_cleanup', 'Clean module deploy directories, preserve whitelisted items')
def cleanup_module_deploy_directories() -> dict:
    """Clean module deploy directories but preserve whitelisted items."""
    import shutil

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project cleanup hook: Could not detect project name")
            return {"status": "error", "component": "framework_cleanup", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name

        from hh.deploy.deploy_utils import get_active_modules, load_whitelist_with_extensions
        active_modules = get_active_modules(force_regenerate=True)
        module_names = {module.name for module in active_modules}
        log(f"project cleanup hook: Active modules for deploy cleanup: {sorted(module_names)}")

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
                            log(f"project cleanup hook: Temporarily moved {full_item_path}: {item_path} -> {temp_path}")

                    # Remove entire module deploy directory contents
                    shutil.rmtree(module_deploy_dir)
                    log(f"project cleanup hook: Removed {module_name}/deploy directory: {module_deploy_dir}")

                    # Recreate module deploy directory and restore preserved items
                    module_deploy_dir.mkdir(parents=True, exist_ok=True)
                    for full_item_path, (original_path, temp_path) in module_preserved_items.items():
                        if temp_path.exists():
                            restored_path = dest / full_item_path
                            # Ensure parent directory exists
                            restored_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(temp_path), str(restored_path))
                            log(f"project cleanup hook: Restored {full_item_path}: {restored_path}")

                    cleaned_modules.append(module_name)

            except Exception as e:
                warn(f"project cleanup hook: Failed to clean {module_name}/deploy directory: {e}")
                report_error("backend", f"project cleanup hook: Failed to clean {module_name}/deploy directory: {e}")

        return {
            "status": "completed",
            "component": "framework_cleanup",
            "modules_cleaned": cleaned_modules,
            "modules_count": len(cleaned_modules)
        }

    except Exception as e:
        warn(f"project cleanup hook: Failed to cleanup module deploy directories: {e}")
        report_error("backend", f"project cleanup hook: Failed to cleanup module deploy directories: {e}")
        return {"status": "error", "component": "framework_cleanup", "error": str(e)}