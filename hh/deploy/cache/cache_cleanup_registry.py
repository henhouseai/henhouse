"""
Cache cleanup registry system.

Each module with a cache can register its own cleanup method.
The system scans for @register_cache_cleanup decorators and provides
a centralized way to clean individual or all caches.
"""
from __future__ import annotations
import os
import importlib
from pathlib import Path
from typing import Dict, Callable, Optional, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.utils import detect_project_context

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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

# Global registry for cache cleanup functions (hot cache only)
CleanupResult = Dict[str, Any]
CleanupFunction = Callable[[], CleanupResult]
_cleanup_registry: Dict[str, Optional[CleanupFunction]] = {}
_cache_dir_registry: Dict[str, Optional[str]] = {}

def _scan_for_cache_cleanups() -> list[str]:
    """Scan hh folder tree for files containing @register_cache_cleanup decorator"""
    trace_in()
    found_files = []
    try:
        import hh
        hh_path = Path(hh.__file__).parent
        for py_file in hh_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "@register_cache_cleanup" in content:
                        rel_path = py_file.relative_to(hh_path)
                        module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                        module_path = "hh." + ".".join(module_parts)
                        found_files.append(module_path)
                        log(f"Found @register_cache_cleanup in {module_path}")
            except Exception as e:
                warn(f"Error reading {py_file}: {e}")
    except Exception as e:
        warn(f"Error scanning for cache cleanups: {e}")
    trace_out()
    return found_files

def _load_cleanup_modules():
    """Load all modules that have cache cleanup registrations"""
    trace_in()
    module_paths = _scan_for_cache_cleanups()
    loaded_count = 0
    failed_count = 0
    
    for module_path in module_paths:
        try:
            importlib.import_module(module_path)
            log(f"Successfully imported {module_path}")
            loaded_count += 1
        except Exception as e:
            warn(f"Failed to import {module_path}: {e}")
            failed_count += 1
    
    log(f"Loaded {loaded_count} cache cleanup modules, {failed_count} failed")
    trace_out()
    return loaded_count, failed_count

def register_cache_cleanup(cache_name: str, cache_dir: Optional[str] = None):
    """
    Decorator for registering cache cleanup methods.
    
    Usage:
        @register_cache_cleanup('page_classes', cache_dir='hh/page/cache')
        def cleanup_page_class_cache():
            # Clean up page class cache
            cache_file.unlink()
            _page_class_registry.clear()
    
    Args:
        cache_name: Unique name for this cache (e.g., 'page_classes', 'tp_decorators')
        cache_dir: Relative path to cache directory from project root (e.g., 'hh/page/cache')
                   If None, this cache won't appear in get_cache_directories()
    """
    def decorator(func: CleanupFunction) -> CleanupFunction:
        _cleanup_registry[cache_name] = func
        _cache_dir_registry[cache_name] = cache_dir
        log(f"Registered cache cleanup: {cache_name} -> {func.__module__}.{func.__name__} (cache_dir: {cache_dir})")
        return func
    return decorator

def discover_cache_cleanups() -> Dict[str, CleanupFunction]:
    """
    Discover and load all cache cleanup functions.
    Returns dictionary of cache_name -> cleanup_function.
    """
    trace_in()
    _load_cleanup_modules()
    result = {k: v for k, v in _cleanup_registry.items() if v is not None}
    log(f"Discovered {len(result)} cache cleanup functions: {list(result.keys())}")
    trace_out()
    return result

def clean_cache(cache_name: str) -> Dict[str, Any]:
    """
    Clean a specific cache by name.
    
    Args:
        cache_name: The cache to clean (e.g., 'page_classes')
    
    Returns:
        Dictionary with cleanup results including success status and detailed counts
    """
    trace_in()
    
    # Ensure all cleanups are discovered
    if cache_name not in _cleanup_registry:
        log(f"Cache '{cache_name}' not in registry, discovering...")
        discover_cache_cleanups()
    
    cleanup_func = _cleanup_registry.get(cache_name)
    if cleanup_func is None:
        warn(f"No cleanup function registered for cache '{cache_name}'")
        trace_out()
        return {'success': False, 'error': f'No cleanup function registered for cache {cache_name}'}
    
    try:
        log(f"Cleaning cache: {cache_name}")
        result = cleanup_func()
        log(f"Successfully cleaned cache: {cache_name}")
        trace_out()
        return result
    except Exception as e:
        warn(f"Error cleaning cache '{cache_name}': {e}")
        trace_out()
        return {'success': False, 'error': str(e)}

def clean_all_caches() -> Dict[str, Any]:
    """
    Clean all registered caches.
    
    Returns:
        Dictionary with aggregated cleanup results including detailed counts
    """
    trace_in()
    cleanups = discover_cache_cleanups()
    results = {}
    aggregated = {
        'pycache_dirs': 0,
        'pyc_files': 0,
        'cache_files': 0,
        'cache_dirs': 0,
        'pycache_dirs_list': [],
        'pyc_files_list': [],
        'cache_files_list': [],
        'cache_dirs_list': []
    }
    
    for cache_name, cleanup_func in cleanups.items():
        try:
            log(f"Cleaning cache: {cache_name}")
            cleanup_result = cleanup_func()
            results[cache_name] = cleanup_result
            
            # Aggregate any fields that exist in the result
            if isinstance(cleanup_result, dict):
                for field in ['pycache_dirs', 'pyc_files', 'cache_files', 'cache_dirs']:
                    if field in cleanup_result:
                        aggregated[field] += cleanup_result[field]
                
                for field in ['pycache_dirs_list', 'pyc_files_list', 'cache_files_list', 'cache_dirs_list']:
                    if field in cleanup_result:
                        aggregated[field].extend(cleanup_result[field])
            
            log(f"Successfully cleaned cache: {cache_name}")
        except Exception as e:
            warn(f"Error cleaning cache '{cache_name}': {e}")
            results[cache_name] = {'success': False, 'error': str(e)}
    
    # Add aggregated results
    results['_aggregated'] = aggregated
    
    successful = sum(1 for v in results.values() if isinstance(v, dict) and v.get('success', True))
    total = len([k for k in results.keys() if k != '_aggregated'])
    log(f"Cleaned {successful}/{total} caches successfully")
    trace_out()
    return results

def list_registered_caches() -> list[str]:
    """
    List all registered cache names.
    
    Returns:
        List of cache names
    """
    trace_in()
    discover_cache_cleanups()
    caches = list(_cleanup_registry.keys())
    log(f"Registered caches: {caches}")
    trace_out()
    return caches

def get_deployment_paths() -> list[Path]:
    """
    Get list of all deployment paths to clean (project root + /srv/{project_name} if exists).
    
    Returns:
        List of Path objects for all deployment locations
    """
    paths = []
    
    # Prefer central helper to detect project root and name
    try:
        project_name, project_root = detect_project_context()
        paths.append(project_root)
        srv_project = Path(f"/srv/{project_name}")
        if srv_project.exists():
            paths.append(srv_project)
            log(f"Found deployment path: {srv_project}")
    except Exception as e:
        warn(f"Failed to detect deployment path via helper: {e}")
    
    return paths

def get_cache_directories() -> list[str]:
    """
    Get list of all cache directories managed by registered cleanups.
    Used by deployment scripts to set permissions.
    
    Returns:
        List of cache directory paths relative to project root (e.g., 'hh/page/cache')
    """
    trace_in()
    
    # Discover all cleanups to populate the registry
    discover_cache_cleanups()
    
    # Build list from registry, filtering out None values
    cache_dirs = [cache_dir for cache_dir in _cache_dir_registry.values() if cache_dir is not None]
    
    log(f"Cache directories: {cache_dirs}")
    trace_out()
    return cache_dirs

