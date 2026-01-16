"""
Cache deployment helper functions.

These functions handle cache-related deployment operations.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.render.render import TableData, FieldConfig

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_module_hook('deploy_render')
def render_cache_operations() -> Dict[str, Any]:
    """Render cache-specific deployment operations."""
    trace_in()

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Cache cleaning details - read from hook results
    for result in hook_results:
        if result.get('component') == 'cache_cleanup' and result.get('cache_cleaned'):
            cache_cleaned = result['cache_cleaned']
            if isinstance(cache_cleaned, dict):
                if cache_cleaned.get('pycache_dirs', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['pycache_dirs']} __pycache__ dirs")
                if cache_cleaned.get('pyc_files', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['pyc_files']} .pyc files")
                if cache_cleaned.get('cache_files', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['cache_files']} cache files")
                if cache_cleaned.get('cache_dirs', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['cache_dirs']} .cache dirs")
            break

    # Cache permissions - read from hook results
    cache_permissions_set = any(result.get('component') == 'cache' and result.get('status') == 'completed'
                               for result in hook_results)
    table_data.add_row('cache_permissions', value='Yes' if cache_permissions_set else 'No')

    field_config = FieldConfig()
    field_config.add_simple(['cache_cleaned', 'cache_permissions'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_permissions_special')
def set_cache_permissions() -> Dict[str, Any]:
    """Set special permissions for cache directories."""
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
        log(f"cache permissions: Cleared existing logs directory: {logs_dir}")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Set group write permissions for logs (2775)
    gateway.files.chmod(str(logs_dir), 0o2775)

    # Set ownership so cache operations can write logs
    project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
    user_info = gateway.os.get_user_by_name(project_highest_user)
    if not user_info:
        raise ValueError(f"User not found: {project_highest_user}")

    project_highest_uid = user_info["uid"]
    deploy_group_name = f"{project_name}_deploy"
    subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(logs_dir)], check=True)

    log(f"cache permissions: Created fresh logs directory with group write: {logs_dir}")
    log(f"cache permissions: Set logs directory ownership: {project_highest_user}:{deploy_group_name}")

    return trace_out({
        "status": "completed",
        "component": "cache",
        "permissions": "2775",
        "ownership": f"{project_highest_user}:{deploy_group_name}",
        "directory": str(logs_dir)
    })


@register_module_hook('deploy_permissions_base')
def set_cache_base_permissions() -> Dict[str, Any]:
    """Set base permissions for cache directories."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    dest = Path("/srv") / project_name
    cache_dir = dest / 'cache'

    if not cache_dir.exists():
        log("cache permissions: Cache directory does not exist, skipping base permissions")
        return trace_out({"status": "skipped", "component": "cache_base", "reason": "no_cache_dir"})

    # Ensure cache directory has proper permissions for web server access
    # Cache files should be readable by web server (644 for files, 755 for dirs)

    # Set directory permissions (755 - readable/executable by all, writable by owner)
    subprocess.run(['find', str(cache_dir), '-type', 'd', '-exec', 'chmod', '755', '{}', ';'], check=True)

    # Set file permissions (644 - readable by all, writable by owner)
    subprocess.run(['find', str(cache_dir), '-type', 'f', '-exec', 'chmod', '644', '{}', ';'], check=True)

    log(f"cache permissions: Set cache directory permissions: 755/644 for {cache_dir}")

    return trace_out({
        "status": "completed",
        "component": "cache_base",
        "permissions": "755/644",
        "directory": str(cache_dir),
        "note": "web_accessible_permissions"
    })


@register_module_hook('deploy_cache_cleanup')
def cleanup_cache_files() -> Dict[str, Any]:
    """Clean up cache files and directories."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches

    # Run cache cleanup
    cleanup_results = clean_all_caches()

    log(f"cache cleanup: Cleanup completed - {cleanup_results}")

    return trace_out({
        "status": "completed",
        "component": "cache_cleanup",
        "cache_cleaned": cleanup_results
    })