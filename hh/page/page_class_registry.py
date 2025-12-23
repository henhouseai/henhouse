from __future__ import annotations
import os
import json
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
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

_page_class_registry: Dict[str, Optional[Type]] = {}

def _scan_for_page_classes() -> List[str]:
    trace_in()
    from hh.deploy.deploy_utils import scan_for_decorator
    found_files = scan_for_decorator("register_page_class", exclude_cache=True)
    trace_out()
    return found_files


def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, Any]]:
    trace_in()
    import_results = {}
    for module_path in module_paths:
        try:
            importlib.import_module(module_path)
            log(f"Successfully imported {module_path}")
            import_results[module_path] = {
                "status": "success",
                "error": None
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


def discover_page_classes(force_regenerate: bool = False) -> Dict[str, Dict[str, Any]]:
    trace_in()
    cache_file = CACHE_DIR / "page-classes.json"
    # Check if cache exists and is valid
    if cache_file.exists() and not force_regenerate:
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                log(f"Found page class cache with {len(cache_data.get('classes', {}))} classes")
                trace_out()
                return cache_data.get('classes', {})
        except Exception as e:
            warn(f"Error reading page class cache: {e}")
    log("Discovering page classes...")
    # Scan for @register_page_class decorators
    class_files = _scan_for_page_classes()
    import_results = _import_modules(class_files)
    # Get the populated global registry
    class_data: Dict[str, Dict[str, Any]] = {}
    # Process successfully loaded classes
    for class_name, page_class in _page_class_registry.items():
        if page_class is not None:  # Only process loaded classes
            module_name = page_class.__module__
            class_data[class_name] = {
                "module": module_name,
                "class": page_class.__name__,
                "load_status": "success",
                "load_error": None
            }
            log(f"Found page class: {class_name} -> {module_name}.{page_class.__name__}")
    # Process failed imports
    for module_path, result in import_results.items():
        if result["status"] == "failed":
            # Extract class name from module path (last part)
            class_name = module_path.split(".")[-1]
            if class_name not in class_data:  # Only add if not already registered
                class_data[class_name] = {
                    "module": module_path,
                    "class": class_name,
                    "load_status": "failed",
                    "load_error": result["error"]
                }
    # Write cache
    cache_data = {
        "classes": class_data,
        "last_scan": str(Path(__file__).stat().st_mtime)
    }
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        log(f"Cached page classes: {len(class_data)} classes")
    except Exception as e:
        warn(f"Error caching page classes: {e}")
    trace_out()
    return class_data


def register_page_class(class_name: str):
    def decorator(cls: Type) -> Type:
        # Check for duplicate registration
        if class_name in _page_class_registry:
            warn(f"Duplicate registration: '{class_name}' - overwriting previous")
        _page_class_registry[class_name] = cls
        log(f"Registered page class: {class_name} -> {cls.__module__}.{cls.__name__}")
        return cls
    return decorator


def get_page_class(class_name: str) -> Optional[Type]:
    trace_in()
    # 1. Check hot cache first
    if class_name in _page_class_registry:
        page_class = _page_class_registry[class_name]
        if page_class is not None:  # Already loaded
            log(f"Found page class '{class_name}' in hot cache")
            trace_out()
            return page_class
    # 2. Not in hot cache - check cold cache and load
    log(f"Page class '{class_name}' not in hot cache, checking cold cache")
    class_data = discover_page_classes()
    class_info = class_data.get(class_name)
    if class_info and class_info.get("load_status") == "success":
        try:
            module = importlib.import_module(class_info["module"])
            log(f"Loaded page class '{class_name}' from cold cache: {class_info['module']}")
        except Exception as e:
            warn(f"Error loading page class '{class_name}' from cold cache: {e}")
        if class_name in _page_class_registry:
            page_class = _page_class_registry[class_name]
            if page_class is not None:
                log(f"Found page class '{class_name}' after load")
                trace_out()
                return page_class
    # 3. Not known - rebuild cold cache
    log(f"Page class '{class_name}' not found, rebuilding cache...")
    discover_page_classes(force_regenerate=True)
    # 4. Check hot cache again
    if class_name in _page_class_registry:
        page_class = _page_class_registry[class_name]
        if page_class is not None:
            log(f"Found page class '{class_name}' after rebuild")
            trace_out()
            return page_class
    # 5. Not found - return None (will fall back to base Page class)
    warn(f"Page class '{class_name}' not found after full rebuild")
    trace_out()
    return None


def get_all_page_classes() -> Dict[str, Type]:
    trace_in()
    # Get cold cache data (contains all registered classes)
    class_data = discover_page_classes()
    # Import all modules from cold cache to populate hot cache
    for class_name, class_info in class_data.items():
        if class_info.get("load_status") == "success" and class_name not in _page_class_registry:
            # Module not in hot cache yet - import it
            module_path = class_info.get("module")
            if module_path:
                try:
                    importlib.import_module(module_path)
                    log(f"Imported module {module_path} for class {class_name}")
                except Exception as e:
                    warn(f"Failed to import module {module_path} for class {class_name}: {e}")
    # Now return all classes from hot cache
    result = {k: v for k, v in _page_class_registry.items() if v is not None}
    log(f"Retrieved {len(result)} page classes")
    trace_out()
    return result


def check_page_class_exists(class_name: str) -> bool:
    trace_in()
    classes = discover_page_classes()
    result = class_name in classes
    log(f"Page class '{class_name}' exists: {result}")
    trace_out()
    return result


@register_cache_cleanup('page_classes', cache_dir='hh/page/cache')
def cleanup_page_class_cache():
    trace_in()
    # Clear hot cache
    _page_class_registry.clear()
    log("Cleared page class hot cache")
    # Remove cold cache file
    removed_files = []
    candidate_files = [CACHE_DIR / "page-classes.json"]
    for root in get_deployment_paths():
        candidate_files.append(root / 'hh' / 'page' / 'cache' / 'page-classes.json')
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

