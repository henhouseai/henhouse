"""
Cache deployment hooks for framework cache management.
"""

import subprocess
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

log = lambda message: None
warn = lambda message: None

def _init_debug():
    global log, warn
    log = get_log(True)
    warn = get_warn(True)

try:
    _init_debug()
except:
    pass

# Pre-validated configuration storage for cache module
pre_validated_cache_config: dict = {}

@register_module_hook('deploy_pre_validate')
def validate_cache_config():
    """Pre-validate cache-specific configuration."""
    global pre_validated_cache_config

    log("Validating cache deployment configuration")

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            raise ValueError("Could not detect project context")

        # Validate cache directories exist or can be created
        from hh.deploy.cache.cache_cleanup_registry import get_cache_directories
        cache_dirs = get_cache_directories()

        pre_validated_cache_config = {
            'project_name': project_name,
            'current_path': current_path,
            'cache_directories': cache_dirs
        }

        log(f"Pre-validated cache config for: {project_name}")
    except Exception as e:
        warn(f"Failed to validate cache config: {e}")
        raise ValueError(f"Failed to validate cache config: {e}")


@register_module_hook('deploy_render')
def render_cache_operations():
    """Render cache-specific deployment operations."""
    from hh.render.render import TableData, FieldConfig
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}

    table_data = TableData()

    # Cache cleaning details
    cache_cleaned = source_data.get('cache_cleaned', {})
    if isinstance(cache_cleaned, dict):
        if cache_cleaned.get('pycache_dirs', 0) > 0:
            table_data.add_row('cache_cleaned', value=f"{cache_cleaned['pycache_dirs']} __pycache__ dirs")
        if cache_cleaned.get('pyc_files', 0) > 0:
            table_data.add_row('cache_cleaned', value=f"{cache_cleaned['pyc_files']} .pyc files")
        if cache_cleaned.get('cache_files', 0) > 0:
            table_data.add_row('cache_cleaned', value=f"{cache_cleaned['cache_files']} cache files")
        if cache_cleaned.get('cache_dirs', 0) > 0:
            table_data.add_row('cache_cleaned', value=f"{cache_cleaned['cache_dirs']} .cache dirs")

    # Cache permissions
    cache_permissions_set = source_data.get('cache_permissions_set', False)
    table_data.add_row('cache_permissions', value='Yes' if cache_permissions_set else 'No')

    field_config = FieldConfig()
    field_config.add_simple(['cache_cleaned', 'cache_permissions'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }

@register_module_hook('deploy_permissions_special')
def set_cache_permissions() -> dict:
    """Set special permissions for cache directories."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("cache permissions hook: Could not detect project name")
            return {"status": "error", "component": "cache", "error": "no_project"}

        gateway = get_gateway()
        dest = Path("/srv") / project_name

        # Get project user info
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"cache permissions hook: User not found: {project_highest_user}")
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
                    log(f"cache permissions hook: Set cache directory permissions: {cache_dir}")
                else:
                    # Create cache directory if it doesn't exist
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    gateway.files.chmod(str(cache_dir), 0o2775)
                    log(f"cache permissions hook: Created cache directory with group write: {cache_dir}")

                # Set ownership so all tier users can write via group permissions
                subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(cache_dir)], check=True)
                log(f"cache permissions hook: Set cache directory ownership: {cache_dir} -> {project_highest_user}:{deploy_group_name}")

                cache_results.append({"directory": str(cache_dir), "status": "completed"})

            except Exception as e:
                warn(f"cache permissions hook: Failed to set permissions for {cache_dir}: {e}")
                cache_results.append({"directory": str(cache_dir), "status": "error", "error": str(e)})

        log("cache permissions hook: Cache directory permissions setup completed")
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
        warn(f"cache permissions hook: Failed to set cache permissions: {e}")
        report_error("backend", f"cache permissions hook: Failed to set cache permissions: {e}")
        return {"status": "error", "component": "cache", "error": str(e)}


@register_module_hook('deploy_permissions_base')
def set_base_permissions() -> dict:
    """Set base ownership and permissions for entire deployment directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("cache permissions hook: Could not detect project name")
            return {"status": "error", "component": "base", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name

        # Get project user info
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"cache permissions hook: User not found: {project_highest_user}")
            return {"status": "error", "component": "base", "error": "user_not_found"}

        project_highest_uid = user_info["uid"]
        deploy_group_name = f"{project_name}_deploy"

        # Set base ownership for entire deployment directory
        import subprocess
        subprocess.run(['chown', '-R', f'{project_highest_uid}:{deploy_group_name}', str(dest)], check=True)

        # Set base permissions: directories 750, files 640
        subprocess.run(['find', str(dest), '-type', 'd', '-exec', 'chmod', '750', '{}', ';'], check=True)
        subprocess.run(['find', str(dest), '-type', 'f', '-exec', 'chmod', '640', '{}', ';'], check=True)

        log(f"cache permissions hook: Set base ownership and permissions: {project_highest_user}:{deploy_group_name} (750/640)")
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
        warn(f"cache permissions hook: Failed to set base permissions: {e}")
        report_error("backend", f"cache permissions hook: Failed to set base permissions: {e}")
        return {"status": "error", "component": "base", "error": str(e)}


@register_module_hook('deploy_cache_cleanup')
def cleanup_deployment_cache_files() -> dict:
    """Clean cache files from deployment directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("cache cleanup hook: Could not detect project name")
            return {"status": "error", "component": "cache_cleanup", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name

        cache_cleaned = {
            'pycache_dirs': 0,
            'pyc_files': 0,
            'cache_files': 0,
            'cache_dirs': 0
        }

        # Remove __pycache__ directories
        for pycache_dir in dest.rglob('__pycache__'):
            import shutil
            shutil.rmtree(pycache_dir)
            cache_cleaned['pycache_dirs'] += 1
            log(f"Removed __pycache__ directory: {pycache_dir}")

        # Remove .pyc files
        for pyc_file in dest.rglob('*.pyc'):
            pyc_file.unlink()
            cache_cleaned['pyc_files'] += 1
            log(f"Removed .pyc file: {pyc_file}")

        # Remove cache files
        cache_patterns = ['*-reg.json', '*.cycle.json', 'cache.json', '*.cache']
        for pattern in cache_patterns:
            for cache_file in dest.rglob(pattern):
                cache_file.unlink()
                cache_cleaned['cache_files'] += 1
                log(f"Removed cache file: {cache_file}")

        # Remove .cache directories
        for cache_dir in dest.rglob('.cache'):
            import shutil
            shutil.rmtree(cache_dir)
            cache_cleaned['cache_dirs'] += 1
            log(f"Removed .cache directory: {cache_dir}")

        log(f"Cache cleanup complete: {cache_cleaned['pycache_dirs']} __pycache__ dirs, {cache_cleaned['pyc_files']} .pyc files, {cache_cleaned['cache_files']} cache files, {cache_cleaned['cache_dirs']} .cache dirs")

        return {
            "status": "completed",
            "component": "cache_cleanup",
            "cache_cleaned": cache_cleaned,
            "directory": str(dest),
            # Render-related data (namespaced to avoid conflicts)
            "render_cache_cleaned": cache_cleaned
        }

    except Exception as e:
        warn(f"cache cleanup hook: Failed to clean cache files: {e}")
        report_error("backend", f"cache cleanup hook: Failed to clean cache files: {e}")
        return {"status": "error", "component": "cache_cleanup", "error": str(e)}