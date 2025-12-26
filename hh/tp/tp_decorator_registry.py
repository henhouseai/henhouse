from __future__ import annotations
import os
import json
import importlib
import importlib.util
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup, get_deployment_paths

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

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Throttling: prevent repeated scans within 1 hour
_last_scan_time: float = 0.0
SCAN_THROTTLE_SECONDS = 3600.0

DecoratorFunction = Callable[..., Union[str, Dict[str, Any]]]
_global_registry: Dict[str, Optional[DecoratorFunction]] = {}

def _read_cache_file_with_retry(cache_file: Path) -> Optional[Dict[str, Any]]:
    """Read cache file with retry logic if file is empty (another process is writing)"""
    try:
        # First attempt
        if not cache_file.exists():
            return None
        
        # Check if file is empty or very small (indicates write in progress)
        file_size = cache_file.stat().st_size
        if file_size == 0:
            log(f"Cache file {cache_file} is empty, waiting 1 second for other process to finish...")
            time.sleep(1.0)
            
            # Retry after wait
            if not cache_file.exists():
                return None
            file_size = cache_file.stat().st_size
            if file_size == 0:
                warn(f"Cache file {cache_file} still empty after retry, treating as invalid")
                return None
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            return cache_data
    except json.JSONDecodeError as e:
        # If JSON decode fails, might be incomplete write - retry once
        log(f"JSON decode error reading {cache_file}: {e}, waiting 1 second and retrying...")
        time.sleep(1.0)
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                return cache_data
        except Exception as e2:
            warn(f"Error reading cache file {cache_file} after retry: {e2}")
            return None
    except Exception as e:
        warn(f"Error reading cache file {cache_file}: {e}")
        return None

def _scan_for_decorator(decorator_name: str) -> List[str]:
    trace_in()
    from hh.deploy.deploy_utils import scan_for_decorator
    found_files = scan_for_decorator(decorator_name, exclude_cache=True)
    trace_out()
    return found_files


def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, Any]]:
    trace_in()
    import_results = {}
    for module_path in module_paths:
        try:
            # Standard module import
            module = importlib.import_module(module_path)
            log(f"Successfully imported {module_path}")
            import_results[module_path] = {
                "status": "success",
                "error": None,
                "module": module
            }
        except Exception as e:
            error_msg = str(e)
            debug(f"Failed to import {module_path}: {error_msg}")
            import_results[module_path] = {
                "status": "failed",
                "error": error_msg
            }
    trace_out()
    return import_results


def _validate_cached_module_path(module_path: str) -> bool:
    if not module_path:
        return False
    try:
        importlib.import_module(module_path)
        return True
    except Exception:
        return False


def discover_tp_decorators(force_regenerate: bool = False) -> Dict[str, Dict[str, Any]]:
    trace_in()
    global _last_scan_time
    
    cache_file = CACHE_DIR / "tp-decorators.json"
    current_time = time.time()
    
    # Always check throttle first, even if force_regenerate is True
    if cache_file.exists():
        cache_data = _read_cache_file_with_retry(cache_file)
        if cache_data is not None:
            # Check if we've scanned recently (throttle to prevent repeated scans)
            last_scan_str = cache_data.get('last_scan', '0')
            try:
                last_scan_timestamp = float(last_scan_str)
            except (ValueError, TypeError):
                last_scan_timestamp = 0
            
            time_since_scan = current_time - last_scan_timestamp
            
            # Also check in-memory throttle
            time_since_memory_scan = current_time - _last_scan_time
            
            # If we've scanned recently, honor throttle and use cache (ignore force_regenerate)
            if time_since_scan < SCAN_THROTTLE_SECONDS or time_since_memory_scan < SCAN_THROTTLE_SECONDS:
                log(f"Throttling: using cached TP decorators (scanned {time_since_scan:.1f}s ago, throttle: {SCAN_THROTTLE_SECONDS}s, force_regenerate={force_regenerate} ignored)")
                trace_out()
                return cache_data.get('decorators', {})
            
            # Cache exists and is old enough - check if we should use it or regenerate
            if not force_regenerate:
                log(f"Found TP decorator cache with {len(cache_data.get('decorators', {}))} decorators (last scan: {time_since_scan:.1f}s ago)")
                trace_out()
                return cache_data.get('decorators', {})
            else:
                log(f"Force regenerate requested, but cache exists (last scan: {time_since_scan:.1f}s ago) - proceeding with scan")
    log("Discovering TP decorators...")
    # Scan for @register_tp_decorator decorators
    decorator_files = _scan_for_decorator("register_tp_decorator")
    import_results = _import_modules(decorator_files)
    # Import the TP registry module to get populated global arrays
    from hh.tp.tp_decorator_registry import _global_registry
    decorator_data: Dict[str, Dict[str, Any]] = {}
    
    # Process successfully loaded decorators
    for decorator_name, decorator_func in _global_registry.items():
        if decorator_func is not None:  # Only process loaded decorators
            module_name = decorator_func.__module__
            
            decorator_data[decorator_name] = {
                "module": module_name,
                "function": decorator_func.__name__,
                "load_status": "success",
                "load_error": ""
            }
            log(f"Found TP decorator: {decorator_name} -> {module_name}.{decorator_func.__name__}")
    # Process failed imports
    for module_path, result in import_results.items():
        if result["status"] == "failed":
            # Extract decorator name from module path (last part)
            decorator_name = module_path.split(".")[-1]
            if decorator_name not in decorator_data:  # Only add if not already registered
                decorator_data[decorator_name] = {
                    "module": module_path,
                    "function": decorator_name,
                    "load_status": "failed",
                    "load_error": result.get("error") or ""
                }
    # Write cache with current timestamp
    cache_data = {
        "decorators": decorator_data,
        "last_scan": str(current_time)
    }
    
    # Update in-memory scan time
    _last_scan_time = current_time
    
    # Atomic write: write to temp file, then rename
    try:
        temp_file = cache_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        temp_file.replace(cache_file)
        log(f"Cached TP decorators: {len(decorator_data)} decorators")
    except Exception as e:
        warn(f"Error caching TP decorators: {e}")
        # Clean up temp file if it exists
        temp_file = cache_file.with_suffix('.tmp')
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
    trace_out()
    return decorator_data


def register_tp_decorator(name: str) -> Callable[[DecoratorFunction], DecoratorFunction]:
    def decorator(func: DecoratorFunction) -> DecoratorFunction:
        # Check for duplicate registration
        if name in _global_registry:
            warn(f"Duplicate registration: '{name}' - overwriting previous")
        _global_registry[name] = func
        log(f"Registered TP decorator: {name} -> {func.__module__}.{func.__name__}")
        return func
    return decorator


def get_tp_decorator(name: str) -> Optional[DecoratorFunction]:
    trace_in()
    # 1. Check hot cache first
    if name in _global_registry:
        callable = _global_registry[name]
        if callable is not None:  # Already loaded
            log(f"Found decorator '{name}' in hot cache")
            trace_out()
            return callable
    # 2. Not in hot cache - check cold cache and load
    log(f"Decorator '{name}' not in hot cache, checking cold cache")
    decorator_data = discover_tp_decorators()
    decorator_info = decorator_data.get(name)
    if decorator_info and decorator_info.get("load_status") == "success":
        try:
            module_path = decorator_info["module"]
            module = importlib.import_module(module_path)
            log(f"Loaded decorator '{name}' from cold cache: {module_path}")
        except Exception as e:
            warn(f"Error loading decorator '{name}' from cold cache: {e}")
        if name in _global_registry:
            callable = _global_registry[name]
            if callable is not None:
                log(f"Found decorator '{name}' after rebuild")
                trace_out()
                return callable
    # 3. Not known - rebuild cold cache
    log(f"Decorator '{name}' not found, rebuilding cache...")
    discover_tp_decorators(force_regenerate=True)
    # 4. Check hot cache again
    if name in _global_registry:
        callable = _global_registry[name]
        if callable is not None:
            log(f"Found decorator '{name}' after rebuild")
            trace_out()
            return callable
    # 5. Bad decorator - not found anywhere
    log(f"Decorator '{name}' not found after full rebuild")
    trace_out()
    return None


def check_tp_decorator_exists(name: str) -> bool:
    trace_in()
    decorators = discover_tp_decorators()
    result = name in decorators
    log(f"TP decorator '{name}' exists: {result}")
    trace_out()
    return result


@register_cache_cleanup('tp_decorators', cache_dir='hh/tp/cache')
def cleanup_tp_decorator_cache():
    trace_in()
    # Clear hot cache
    _global_registry.clear()
    log("Cleared TP decorator hot cache")
    # Remove cold cache file
    removed_files = []
    candidate_files = [CACHE_DIR / "tp-decorators.json"]
    for root in get_deployment_paths():
        candidate_files.append(root / 'hh' / 'tp' / 'cache' / 'tp-decorators.json')
    for cache_file in candidate_files:
        if cache_file.exists():
            cache_file.unlink()
            removed_files.append(str(cache_file))
            log(f"Removed cold cache file: {cache_file}")
        else:
            debug(f"Cold cache file does not exist: {cache_file}")
    trace_out()
    return {
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    }
