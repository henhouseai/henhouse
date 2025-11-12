from __future__ import annotations
import os
import shutil
from pathlib import Path
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.deploy.cache.cache_cleanup_registry import clean_all_caches, register_cache_cleanup, get_deployment_paths

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

@register_cache_cleanup('python_bytecode', cache_dir=None)
def cleanup_python_bytecode():
    """Clean up Python bytecode files (__pycache__ and .pyc files)"""
    trace_in()
    
    # Get all roots to clean: repo and deployment
    roots = get_deployment_paths()
    
    pycache_dirs = []
    pyc_files = []
    
    for root in roots:
        # Delete all __pycache__ directories
        for pycache_dir in root.rglob("__pycache__"):
            try:
                shutil.rmtree(pycache_dir)
                try:
                    rel_path = pycache_dir.relative_to(root)
                except Exception:
                    rel_path = pycache_dir
                pycache_dirs.append(str(rel_path))
                log(f"Deleted __pycache__: {pycache_dir}")
            except Exception as e:
                warn(f"Failed to delete {pycache_dir}: {e}")
        
        # Delete all .pyc files
        for pyc_file in root.rglob("*.pyc"):
            try:
                pyc_file.unlink()
                try:
                    rel_path = pyc_file.relative_to(root)
                except Exception:
                    rel_path = pyc_file
                pyc_files.append(str(rel_path))
                log(f"Deleted .pyc: {pyc_file}")
            except Exception as e:
                warn(f"Failed to delete {pyc_file}: {e}")
    
    log("Python bytecode cleanup completed")
    trace_out()
    
    return {
        'success': True,
        'pycache_dirs': len(pycache_dirs),
        'pyc_files': len(pyc_files),
        'pycache_dirs_list': pycache_dirs,
        'pyc_files_list': pyc_files
    }

@register_action("clear_cache")
@register_command("clear_cache")
def clear_cache() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    try:
        # Call all registered cache cleanup functions
        log("Calling all registered cache cleanup functions...")
        cleanup_results = clean_all_caches()
        
        # Extract aggregated results
        aggregated = cleanup_results.get('_aggregated', {})
        
        # Calculate success/failure counts (excluding aggregated data)
        cache_results = {k: v for k, v in cleanup_results.items() if k != '_aggregated'}
        successful = sum(1 for v in cache_results.values() if isinstance(v, dict) and v.get('success', True))
        failed = len(cache_results) - successful
        
        # Calculate total items cleared
        total_items = (aggregated.get('pycache_dirs', 0) + 
                      aggregated.get('pyc_files', 0) + 
                      aggregated.get('cache_files', 0) + 
                      aggregated.get('cache_dirs', 0))
        
        # Prepare response data
        data = {
            "type": "clear_cache",
            "success": failed == 0,
            "caches_cleaned": successful,
            "caches_failed": failed,
            "total_caches": len(cache_results),
            "total_items_cleared": total_items,
            "details": {
                "results": cache_results,
                "cache_files": aggregated.get('cache_files_list', []),
                "pycache_dirs": aggregated.get('pycache_dirs_list', []),
                "pyc_files": aggregated.get('pyc_files_list', [])
            }
        }
        
        log(f"Cache clear completed: {successful}/{len(cache_results)} caches cleared successfully, {total_items} total items")
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Cache clear failed: {str(e)}")
        report_error("backend", f"Failed to clear cache: {str(e)}")
        trace_out()
        return False
