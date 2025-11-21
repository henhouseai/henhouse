from __future__ import annotations
import os
import json
import importlib
import pkgutil
import re
from pathlib import Path
from typing import List, Dict, Set, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.backend import BACKEND_TYPES, BACKEND_DECORATORS
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
    trace_out()
    return found_files

def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, str]]:
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

def _validate_cached_module_path(module_path: str) -> bool:
    """Validate that a cached module path can still be imported"""
    if not module_path:
        return False
    try:
        importlib.import_module(module_path)
        return True
    except Exception:
        return False

def discover_base_registrations(force_regenerate: bool = False) -> tuple[List[str], List[str]]:
    trace_in()
    cache_file = CACHE_DIR / "base-reg.json"
    if cache_file.exists() and not force_regenerate:
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                log(f"Found base cache with {len(cache_data.get('backends', []))} backends and {len(cache_data.get('commands', []))} commands")
                trace_out()
                return cache_data.get('backends', []), cache_data.get('commands', [])
        except Exception as e:
            warn(f"Error reading base cache: {e}")
    log("Discovering base registrations...")
    command_files = _scan_for_decorator("register_command")
    import_results = _import_modules(command_files)
    from hh.gateway.registry.registry import backends, commands
    backend_list = list(backends.keys())
    command_data = {}
    
    # Process successfully loaded commands
    for command_name, command_info in commands.items():
        module_name = command_info.function.__module__
        command_data[command_name] = {
            "module": module_name,
            "action_args": command_info.action_args,
            "load_status": "success",
            "load_error": None
        }
    
    # Process failed imports - these are commands that were discovered but failed to load
    for module_path, result in import_results.items():
        if result["status"] == "failed":
            # Extract command name from module path (last part)
            command_name = module_path.split(".")[-1]
            if command_name not in command_data:  # Only add if not already registered
                command_data[command_name] = {
                    "module": module_path,
                    "action_args": [],
                    "load_status": "failed",
                    "load_error": result["error"]
                }
    cache_data = {
        "backends": backend_list,
        "commands": command_data
    }
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        log(f"Cached base registrations: {len(backend_list)} backends, {len(command_data)} commands")
    except Exception as e:
        warn(f"Error caching base registrations: {e}")
    trace_out()
    return backend_list, list(command_data.keys())

def discover_all_backends() -> List[str]:
    trace_in()
    backends, _ = discover_base_registrations()
    trace_out()
    return backends

def discover_all_commands() -> List[str]:
    trace_in()
    _, command_names = discover_base_registrations()
    trace_out()
    return command_names

def discover_backend_specific_registrations(backend_type: str, force_regenerate: bool = False) -> Dict[str, Any]:
    trace_in()
    log(f"Starting discovery for backend: {backend_type}")
    cache_file = CACHE_DIR / f"{backend_type}-reg.json"
    if cache_file.exists() and not force_regenerate:
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                log(f"Found {backend_type} cache with {len(cache_data.get('handlers', {}))} handlers")
                trace_out()
                return cache_data
        except Exception as e:
            warn(f"Error reading {backend_type} cache: {e}")
    
    discover_base_registrations(force_regenerate)  # Ensure commands are discovered first
    
    # Scan for handlers of this backend type
    decorator_name = BACKEND_DECORATORS.get(backend_type, f"register_{backend_type}")
    handler_files = _scan_for_decorator(decorator_name)
    import_results = _import_modules(handler_files)
    
    # Get the handlers dictionary for this backend type
    from hh.gateway.registry.registry import backend_handlers
    
    handlers = backend_handlers.get(backend_type, {})
    registrations = {
        "handlers": {},
        "error_handler": None
    }
    
    for handler_name, handler_info in handlers.items():
        if handler_info.function:
            module_name = handler_info.function.__module__
            function_name = handler_info.function.__name__
            action_args = getattr(handler_info, 'action_args', [])
            registrations["handlers"][handler_name] = {
                "module": module_name,
                "function": function_name,
                "action_args": action_args,
                "load_status": "success",
                "load_error": None
            }
            log(f"Found {backend_type} handler: {handler_name} -> {module_name} (action_args={action_args})")
    
    # Process failed imports for this backend type
    for module_path, result in import_results.items():
        if result["status"] == "failed":
            handler_name = module_path.split(".")[-1]
            if handler_name not in registrations["handlers"]:  # Only add if not already registered
                registrations["handlers"][handler_name] = {
                    "module": module_path,
                    "function": handler_name,
                    "action_args": [],
                    "load_status": "failed",
                    "load_error": result["error"]
                }
    
    # Discover error handler for this backend type
    error_handler_name = f"{backend_type}_error"
    try:
        # Check if error handler exists in the error module
        import hh.gateway.error.error as error_module
        if hasattr(error_module, error_handler_name):
            error_function = getattr(error_module, error_handler_name)
            registrations["error_handler"] = {
                "module": error_function.__module__,
                "function": error_function.__name__,
                "load_status": "success",
                "load_error": None
            }
            log(f"Found error handler: {error_handler_name} -> {error_function.__module__}.{error_function.__name__}")
        else:
            log(f"No error handler found for backend '{backend_type}': {error_handler_name}")
    except Exception as e:
        debug(f"Exception during error handler discovery: {e}")
        warn(f"Error discovering error handler for backend '{backend_type}': {e}")
        registrations["error_handler"] = {
            "module": None,
            "function": None,
            "load_status": "failed",
            "load_error": str(e)
        }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(registrations, f, indent=2)
        log(f"Cached {backend_type} registrations: {len(registrations['handlers'])} handlers")
    except Exception as e:
        warn(f"Error caching {backend_type} registrations: {e}")
    trace_out()
    return registrations

def discover_all_backend_handlers(force_regenerate: bool = False) -> Dict[str, List[str]]:
    trace_in()
    all_handlers = {}
    for backend_type in BACKEND_TYPES:
        registrations = discover_backend_specific_registrations(backend_type, force_regenerate)
        handlers = list(registrations.get('handlers', {}).keys())
        all_handlers[backend_type] = handlers
        log(f"Discovered {len(handlers)} {backend_type} handlers")
    trace_out()
    return all_handlers

def check_command_exists(command_name: str) -> bool:
    trace_in()
    commands = discover_all_commands()
    if command_name in commands:
        log(f"Command '{command_name}' exists: True")
        trace_out()
        return True
    
    # Command not found in cache, try forcing a rebuild
    log(f"Command '{command_name}' not found in cache, forcing rebuild...")
    _, fresh_commands = discover_base_registrations(force_regenerate=True)
    result = command_name in fresh_commands
    log(f"Command '{command_name}' exists after rebuild: {result}")
    trace_out()
    return result

def check_backend_exists(backend_name: str) -> bool:
    trace_in()
    backends = discover_all_backends()
    result = backend_name in backends
    log(f"Backend '{backend_name}' exists: {result}")
    trace_out()
    return result

def check_command_in_backend(command_name: str, backend_name: str) -> Dict[str, Any]:
    trace_in()
    
    # Generate command variations
    kebab_case = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', command_name).replace('_', '-').lower()
    snake_case = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', command_name).replace('-', '_').lower()
    command_variations = [command_name, kebab_case, snake_case]
    
    # First try: check if the specific backend cache file exists and has what we need
    cache_file = CACHE_DIR / f"{backend_name}-reg.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                handlers = cache_data.get("handlers", {})
                
                # Try all variations
                for variation in command_variations:
                    command_info = handlers.get(variation, {})
                    if command_info:
                        # Validate that the cached module path is still valid
                        if _validate_cached_module_path(command_info.get("module")):
                            log(f"Found command '{variation}' in backend '{backend_name}' cache")
                            trace_out()
                            return cache_data  # Return full backend registration data
                        else:
                            log(f"Cached module path for '{variation}' is invalid, will regenerate cache")
                            break
        except Exception as e:
            warn(f"Error reading {backend_name} cache: {e}")
    
    # Cache miss: trigger full cache regeneration
    log(f"Cache miss for command '{command_name}' in backend '{backend_name}', triggering full regeneration")
    
    # Force base cache regeneration first
    discover_base_registrations(True)
    discover_all_backend_handlers(True)
    
    # Try again after regeneration
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                handlers = cache_data.get("handlers", {})
                
                # Try all variations again
                for variation in command_variations:
                    command_info = handlers.get(variation, {})
                    if command_info:
                        log(f"Found command '{variation}' in backend '{backend_name}' after regeneration")
                        trace_out()
                        return cache_data  # Return full backend registration data
        except Exception as e:
            warn(f"Error reading {backend_name} cache after regeneration: {e}")
    
    log(f"Command '{command_name}' not found in backend '{backend_name}' (tried: {', '.join(command_variations)})")
    trace_out()
    return {"handlers": {}}  # Return proper structure even when no command found

@register_cache_cleanup('gateway_registry', cache_dir='hh/gateway/registry/cache')
def cleanup_gateway_registry_cache():
    """Clean up gateway registry cache files"""
    trace_in()
    
    # Remove all cache JSON files in both repo and deployment cache directories
    cache_files = ['base-reg.json'] + [f"{backend}-reg.json" for backend in BACKEND_TYPES]
    removed_files = []
    
    # Build candidate cache dirs: local and deployed
    candidate_dirs = [CACHE_DIR]
    for root in get_deployment_paths():
        candidate_dirs.append(root / 'hh' / 'gateway' / 'registry' / 'cache')
    
    for cache_dir in candidate_dirs:
        for cache_file_name in cache_files:
            cache_file = cache_dir / cache_file_name
            if cache_file.exists():
                cache_file.unlink()
                removed_files.append(str(cache_file))
                log(f"Removed cache file: {cache_file}")
            else:
                debug(f"Cache file does not exist: {cache_file}")
    
    trace_out()
    
    return {
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    }