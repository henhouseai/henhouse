"""
Cache management helper for nginx_flask module.

Handles cache file cleanup and validation.
"""

from pathlib import Path
from typing import Dict, Any
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.cache.cache_cleanup_registry import get_cache_directories
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


@register_module_hook('deploy_pre_validate')
def validate_cache_config() -> dict:
    """Pre-validate cache-specific configuration."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            raise ValueError("Could not detect project context")

        # Validate cache directories exist or can be created
        cache_dirs = get_cache_directories()

        return {
            'project_name': project_name,
            'current_path': current_path,
            'cache_directories': cache_dirs
        }

    except Exception as e:
        warn(f"Failed to validate cache config: {e}")
        raise ValueError(f"Failed to validate cache config: {e}")


@register_module_hook('deploy_cache_cleanup')
def cleanup_deployment_cache_files() -> dict:
    """Clean cache files from deployment directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask cache: Could not detect project name")
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
        warn(f"nginx_flask cache: Failed to clean cache files: {e}")
        report_error("backend", f"nginx_flask cache: Failed to clean cache files: {e}")
        return {"status": "error", "component": "cache_cleanup", "error": str(e)}