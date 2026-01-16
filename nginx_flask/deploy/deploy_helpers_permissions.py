"""
Permissions hooks for nginx_flask module.

These functions handle special permission setup for Flask logs and site files.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error
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


@register_module_hook('deploy_permissions_special')
def set_flask_logs_permissions() -> Dict[str, Any]:
    """Set special permissions for Flask daemon logs directory."""
    trace_in()

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

    return trace_out({
        "status": "completed",
        "component": "flask_logs",
        "permissions": "2775",
        "ownership": f"{project_highest_user}:{deploy_group_name}",
        "directory": str(logs_dir)
    })


@register_module_hook('deploy_permissions_special')
def set_site_permissions() -> Dict[str, Any]:
    """Set special permissions for site files (HTML, JS, CSS, etc.)."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    dest = Path("/srv") / project_name
    site_dir = dest / 'site'

    if not site_dir.exists():
        log("nginx_flask permissions: Site directory does not exist, skipping site permissions")
        return trace_out({"status": "skipped", "component": "site", "reason": "no_site_dir"})

    # Ensure web-accessible files have proper permissions for nginx
    # Site files should be readable by web server (644 for files, 755 for dirs)

    # Set directory permissions (755 - readable/executable by all, writable by owner)
    subprocess.run(['find', str(site_dir), '-type', 'd', '-exec', 'chmod', '755', '{}', ';'], check=True)

    # Set file permissions (644 - readable by all, writable by owner)
    subprocess.run(['find', str(site_dir), '-type', 'f', '-exec', 'chmod', '644', '{}', ';'], check=True)

    log(f"nginx_flask permissions: Set site directory permissions: 755/644 for {site_dir}")

    return trace_out({
        "status": "completed",
        "component": "site",
        "permissions": "755/644",
        "directory": str(site_dir),
        "note": "web_accessible_permissions"
    })


def set_cache_permissions_helper() -> dict:
    """Set special permissions for cache directories."""
    try:
        from hh.deploy.deploy_utils import detect_project_context
        from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask permissions: Could not detect project name")
            return {"status": "error", "component": "cache", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name

        # Get project user info
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"nginx_flask permissions: User not found: {project_highest_user}")
            return {"status": "error", "component": "cache", "error": "user_not_found"}

        project_highest_uid = user_info["uid"]
        deploy_group_name = f"{project_name}_deploy"

        # Get cache directories that need special permissions
        from hh.deploy.cache.cache_cleanup_registry import get_cache_directories
        cache_dirs = [dest / cache_dir for cache_dir in get_cache_directories()]

        cache_results = []
        for cache_dir in cache_dirs:
            try:
                if cache_dir.exists():
                    # Set group write permissions for cache dirs (2775)
                    gateway.files.chmod(str(cache_dir), 0o2775)
                    log(f"nginx_flask permissions: Set cache directory permissions: {cache_dir}")
                else:
                    # Create cache directory if it doesn't exist
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    gateway.files.chmod(str(cache_dir), 0o2775)
                    log(f"nginx_flask permissions: Created cache directory with group write: {cache_dir}")

                # Set ownership so all tier users can write via group permissions
                subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(cache_dir)], check=True)
                log(f"nginx_flask permissions: Set cache directory ownership: {cache_dir} -> {project_highest_user}:{deploy_group_name}")

                cache_results.append({"directory": str(cache_dir), "status": "completed"})

            except Exception as e:
                warn(f"nginx_flask permissions: Failed to set permissions for {cache_dir}: {e}")
                cache_results.append({"directory": str(cache_dir), "status": "error", "error": str(e)})

        log("nginx_flask permissions: Cache directory permissions setup completed")
        return {
            "status": "completed",
            "component": "cache",
            "permissions": "2775",
            "ownership": f"{project_highest_user}:{deploy_group_name}",
            "directories": cache_results,
            # Render-related data (namespaced to avoid conflicts)
            "render_cache_permissions_set": True,
            "render_cache_dirs_count": len(cache_results)
        }

    except Exception as e:
        warn(f"nginx_flask permissions: Failed to set cache permissions: {e}")
        report_error("backend", f"nginx_flask permissions: Failed to set cache permissions: {e}")
        return {"status": "error", "component": "cache", "error": str(e)}


def set_base_permissions_helper() -> dict:
    """Set base ownership and permissions for entire deployment directory."""
    try:
        from hh.deploy.deploy_utils import detect_project_context
        from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask permissions: Could not detect project name")
            return {"status": "error", "component": "base", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name

        # Get project user info
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"nginx_flask permissions: User not found: {project_highest_user}")
            return {"status": "error", "component": "base", "error": "user_not_found"}

        project_highest_uid = user_info["uid"]
        deploy_group_name = f"{project_name}_deploy"

        # Set base ownership for entire deployment directory
        subprocess.run(['chown', '-R', f'{project_highest_uid}:{deploy_group_name}', str(dest)], check=True)

        # Set base permissions: directories 750, files 640
        subprocess.run(['find', str(dest), '-type', 'd', '-exec', 'chmod', '750', '{}', ';'], check=True)
        subprocess.run(['find', str(dest), '-type', 'f', '-exec', 'chmod', '640', '{}', ';'], check=True)

        log(f"nginx_flask permissions: Set base ownership and permissions: {project_highest_user}:{deploy_group_name} (750/640)")
        return {
            "status": "completed",
            "component": "base",
            "ownership": f"{project_highest_user}:{deploy_group_name}",
            "permissions": "750/640",
            "directory": str(dest),
            # Render-related data (namespaced to avoid conflicts)
            "render_base_permissions_set": True,
            "render_base_directory": str(dest)
        }

    except Exception as e:
        warn(f"nginx_flask permissions: Failed to set base permissions: {e}")
        report_error("backend", f"nginx_flask permissions: Failed to set base permissions: {e}")
        return {"status": "error", "component": "base", "error": str(e)}
