from __future__ import annotations
import os
import json
import importlib
import importlib.util
import re
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

DecoratorFunction = Callable[..., Union[str, Dict[str, Any]]]
_global_registry: Dict[str, Optional[DecoratorFunction]] = {}

def _scan_for_decorator(decorator_name: str) -> List[str]:
    trace_in()
    found_files = []
    try:
        import hh
        hh_path = Path(hh.__file__).parent
        for py_file in hh_path.rglob("*.py"):
            if py_file.name.startswith("cache_"):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f"@{decorator_name}" in content:
                        rel_path = py_file.relative_to(hh_path)
                        module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                        module_path = "hh." + ".".join(module_parts)
                        found_files.append(module_path)
                        log(f"Found {decorator_name} in {module_path}")
            except Exception as e:
                warn(f"Error reading {py_file}: {e}")
    except Exception as e:
        warn(f"Error scanning for {decorator_name}: {e}")
    
    # Also scan /srv/{project_name}/site/py for deployed decorator files
    try:
        # Detect project name by finding hh/ directory
        current_path = Path.cwd()
        project_name = None
        while current_path != current_path.parent:
            hh_dir = current_path / 'hh'
            if hh_dir.exists() and hh_dir.is_dir():
                project_name = current_path.name
                break
            current_path = current_path.parent
        
        if project_name:
            site_py_path = Path(f'/srv/{project_name}/site/py')
            if site_py_path.exists() and site_py_path.is_dir():
                log(f"Scanning deployed decorators in {site_py_path}")
                for py_file in site_py_path.glob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if f"@{decorator_name}" in content:
                                # Use absolute path for site/py files
                                module_path = f"file://{py_file.absolute()}"
                                found_files.append(module_path)
                                log(f"Found {decorator_name} in deployed file {py_file.name}")
                    except Exception as e:
                        warn(f"Error reading deployed file {py_file}: {e}")
    except Exception as e:
        warn(f"Error scanning deployed decorators: {e}")
    
    trace_out()
    return found_files


def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, str]]:
    trace_in()
    import_results = {}
    for module_path in module_paths:
        try:
            # Handle file:// paths for deployed site/py files
            if module_path.startswith("file://"):
                file_path = Path(module_path[7:])  # Remove "file://" prefix
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Store the file:// path on the module for later reference
                    module.__file_path__ = module_path  # type: ignore[attr-defined]
                    spec.loader.exec_module(module)
                    log(f"Successfully imported deployed module {file_path.name}")
                    import_results[module_path] = {
                        "status": "success",
                        "error": None,
                        "module": module
                    }
                else:
                    raise ImportError(f"Could not create module spec from {file_path}")
            else:
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
    cache_file = CACHE_DIR / "tp-decorators.json"
    # Check if cache exists and is valid
    if cache_file.exists() and not force_regenerate:
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                log(f"Found TP decorator cache with {len(cache_data.get('decorators', {}))} decorators")
                trace_out()
                return cache_data.get('decorators', {})
        except Exception as e:
            warn(f"Error reading TP decorator cache: {e}")
    log("Discovering TP decorators...")
    # Scan for @register_tp_decorator decorators
    decorator_files = _scan_for_decorator("register_tp_decorator")
    import_results = _import_modules(decorator_files)
    # Import the TP registry module to get populated global arrays
    from hh.tp.tp_decorator_registry import _global_registry
    decorator_data: Dict[str, Dict[str, str]] = {}
    
    # Process successfully loaded decorators
    for decorator_name, decorator_func in _global_registry.items():
        if decorator_func is not None:  # Only process loaded decorators
            module_name = decorator_func.__module__
            
            # Try to find the file:// path if this decorator came from a file:// import
            stored_module_path = module_name
            # Get the module object to check for __file_path__ attribute
            try:
                # Try to get module from sys.modules
                import sys
                if module_name in sys.modules:
                    module_obj = sys.modules[module_name]
                    if hasattr(module_obj, '__file_path__'):
                        stored_module_path = module_obj.__file_path__
            except Exception:
                pass
            
            # Also check import_results for file:// paths
            if stored_module_path == module_name:
                for module_path, result in import_results.items():
                    if result.get("status") == "success" and module_path.startswith("file://"):
                        module_obj = result.get("module")
                        if module_obj and hasattr(decorator_func, '__module__'):
                            # Check if decorator's module matches
                            if module_name == module_obj.__name__:
                                stored_module_path = module_path
                                break
            
            decorator_data[decorator_name] = {
                "module": stored_module_path,
                "function": decorator_func.__name__,
                "load_status": "success",
                "load_error": ""
            }
            log(f"Found TP decorator: {decorator_name} -> {stored_module_path}.{decorator_func.__name__}")
    # Process failed imports
    for module_path, result in import_results.items():
        if result["status"] == "failed":
            # Extract decorator name from module path (last part)
            if module_path.startswith("file://"):
                decorator_name = Path(module_path[7:]).stem
            else:
                decorator_name = module_path.split(".")[-1]
            if decorator_name not in decorator_data:  # Only add if not already registered
                decorator_data[decorator_name] = {
                    "module": module_path,
                    "function": decorator_name,
                    "load_status": "failed",
                    "load_error": result["error"] or ""
                }
    # Write cache
    cache_data = {
        "decorators": decorator_data,
        "last_scan": str(Path(__file__).stat().st_mtime)
    }
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        log(f"Cached TP decorators: {len(decorator_data)} decorators")
    except Exception as e:
        warn(f"Error caching TP decorators: {e}")
    trace_out()
    return decorator_data


def register_tp_decorator(name: str) -> Callable[[DecoratorFunction], DecoratorFunction]:
    def decorator(func: DecoratorFunction) -> DecoratorFunction:
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
            # Handle file:// paths
            if module_path.startswith("file://"):
                file_path = Path(module_path[7:])
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    log(f"Loaded decorator '{name}' from cold cache: {file_path.name}")
                else:
                    raise ImportError(f"Could not create module spec from {file_path}")
            else:
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
    warn(f"Decorator '{name}' not found after full rebuild")
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
