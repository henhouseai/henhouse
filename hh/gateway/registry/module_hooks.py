"""
Module Hooks Registry

Provides decorator-based hook registration system for modules to extend
deployment, installation, and other lifecycle operations.

Hook Discovery:
- Hooks are discovered during module import (similar to commands)
- Module detected by walking up from function file to find __module__.py
- Hooks cached in module-hooks.json for fast access

Hook Execution:
- Alphabetical order by module name
- Stop immediately on first failure
- Undefined hooks = silent no-op (no warnings)
- Flexible namespace (any hook name allowed)

Example Usage:
    from hh.gateway.registry.module_hooks import register_module_hook

    @register_module_hook('deploy_before_schema')
    def setup_database_users(project_name: str, config: dict):
        # Custom deployment logic here
        pass
"""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.module_discovery import load_manifest
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup, get_deployment_paths
from hh.gateway.error.error_store import report_error

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

# Cache directory setup
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "module-hooks.json"


@dataclass
class HookInfo:
    """Information about a registered hook function."""
    module_name: str
    module_path: str
    function_module: str  # Python module path (e.g., 'users.deploy.deploy_hooks')
    function_name: str    # Function name (e.g., 'test_hook_log_to_database')
    function: Optional[Callable] = None  # Lazy-loaded callable


# Global hook registry: hook_name -> List[HookInfo]
hooks: Dict[str, List[HookInfo]] = {}


def _discover_module_from_function(func: Callable) -> Optional[tuple[str, str]]:
    """
    Discover which module a function belongs to by walking up directories.

    Walks up from func.__file__ until finding a folder with __module__.py,
    then loads the manifest to get the module name.

    Args:
        func: The function to discover module for

    Returns:
        Tuple of (module_name, module_path) if found, None otherwise

    Example:
        >>> func = some_function_from_users_module
        >>> name, path = _discover_module_from_function(func)
        >>> print(name)  # 'users'
        >>> print(path)  # '/path/to/users'
    """
    trace_in()

    if not hasattr(func, '__code__') or not func.__code__.co_filename:
        log(f"Function {func.__name__} has no __code__.co_filename attribute")
        return trace_out(None)

    # Normalize paths for cross-platform compatibility (especially Windows)
    current_dir = os.path.normcase(os.path.normpath(os.path.dirname(os.path.abspath(func.__code__.co_filename))))
    project_root = os.path.normcase(os.path.normpath(os.getcwd()))

    log(f"Looking for module for {func.__name__}: starting from {current_dir}, project_root={project_root}")

    # Walk up directories until we find __module__.py or hit project root
    while current_dir and current_dir != project_root:
        manifest_path = os.path.join(current_dir, '__module__.py')
        log(f"Checking for __module__.py at: {current_dir}")

        if os.path.exists(manifest_path):
            log(f"Found __module__.py at {manifest_path}")
            # Found a module! Load the manifest
            manifest = load_manifest(current_dir)
            if manifest and 'name' in manifest:
                module_name = manifest['name']
                log(f"Discovered module '{module_name}' for function {func.__name__} at {current_dir}")
                return trace_out((module_name, current_dir))
            else:
                warn(f"Found __module__.py at {current_dir} but failed to load manifest")
                return trace_out(None)
        else:
            log(f"No __module__.py at {current_dir}, moving up")

        # Move up one directory
        parent_dir = os.path.normcase(os.path.normpath(os.path.dirname(current_dir)))
        if parent_dir == current_dir:
            # Hit filesystem root
            break
        current_dir = parent_dir

    log(f"No module found for function {func.__name__} (searched up from {func.__code__.co_filename})")
    return trace_out(None)


def register_module_hook(hook_name: str) -> Callable[[Callable], Callable]:
    """
    Decorator to register a function as a module hook.

    The function's module is auto-detected by walking up directories
    to find __module__.py manifest file.

    Args:
        hook_name: Name of the hook (e.g., 'deploy_before_schema')

    Returns:
        Decorator function

    Example:
        @register_module_hook('deploy_before_schema')
        def my_hook(project_name: str):
            print(f"Running hook for {project_name}")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            return func(*args, **kwargs)

        trace_in()

        # Discover which module this function belongs to
        module_info = _discover_module_from_function(func)
        if not module_info:
            warn(f"Cannot register hook '{hook_name}' for {func.__name__} - no module found")
            return trace_out(wrapper)

        module_name, module_path = module_info

        # Create HookInfo instance with callable
        hook_info = HookInfo(
            module_name=module_name,
            module_path=module_path,
            function_module=func.__module__,
            function_name=func.__name__,
            function=wrapper
        )

        # Add to registry
        if hook_name not in hooks:
            hooks[hook_name] = []

        hooks[hook_name].append(hook_info)
        log(f"Registered hook '{hook_name}' from module '{module_name}' -> {func.__module__}.{func.__name__}")

        return trace_out(wrapper)

    return decorator


def get_hook_handlers(hook_name: str) -> List[Callable]:
    """
    Get callable handlers for a hook name, lazy-loading if needed.

    Checks hot cache for hook metadata. If callable not yet loaded,
    imports module on-demand to get callable.

    Args:
        hook_name: Name of hook to get handlers for

    Returns:
        List of callable functions for this hook (sorted alphabetically by module)

    Example:
        handlers = get_hook_handlers('deploy-test-start')
        for handler in handlers:
            handler()
    """
    trace_in()

    if hook_name not in hooks:
        debug(f"No hooks registered for '{hook_name}'")
        return trace_out([])

    hook_list = hooks[hook_name]
    debug(f"Found {len(hook_list)} hooks for '{hook_name}' in hot cache")

    # Sort alphabetically by module name
    sorted_hooks = sorted(hook_list, key=lambda h: h.module_name)

    handlers = []
    for hook_info in sorted_hooks:
        # Check if callable already loaded
        if hook_info.function is not None:
            debug(f"Using cached callable for {hook_info.module_name}.{hook_info.function_name}")
            handlers.append(hook_info.function)
        else:
            # Lazy-load the callable
            debug(f"Lazy-loading {hook_info.function_module}.{hook_info.function_name}")
            try:
                import importlib
                module = importlib.import_module(hook_info.function_module)
                func = getattr(module, hook_info.function_name)

                # Store callable in hot cache for next time
                hook_info.function = func

                log(f"Loaded hook handler: {hook_info.function_module}.{hook_info.function_name}")
                handlers.append(func)
            except Exception as e:
                warn(f"Failed to load hook {hook_info.function_module}.{hook_info.function_name}: {e}")
                # Continue with other hooks

    return trace_out(handlers)


def run_hooks(hook_name: str, *args, **kwargs) -> bool:
    """
    Execute all hooks registered for a given hook name.

    Hooks execute in alphabetical order by module name.
    Stops immediately on first failure (exception or False return).

    Args:
        hook_name: Name of hook to execute
        *args: Positional arguments to pass to hook functions
        **kwargs: Keyword arguments to pass to hook functions

    Returns:
        True if all hooks succeeded, False if any failed

    Example:
        success = run_hooks('deploy_before_schema', project_name='myproject')
        if not success:
            print("Hook execution failed")
    """
    trace_in()

    # Get callable handlers (lazy-loads if needed)
    handlers = get_hook_handlers(hook_name)

    if not handlers:
        debug(f"No hooks registered for '{hook_name}' - silent no-op")
        return trace_out(True)

    log(f"Running {len(handlers)} hooks for '{hook_name}'")

    # Handlers already sorted alphabetically by get_hook_handlers()
    hook_list = hooks.get(hook_name, [])
    sorted_hooks = sorted(hook_list, key=lambda h: h.module_name)

    for hook_info, func in zip(sorted_hooks, handlers):
        module_name = hook_info.module_name

        log(f"Executing hook '{hook_name}' from module '{module_name}'")

        try:
            result = func(*args, **kwargs)

            # Check for explicit False return (indicates failure)
            if result is False:
                warn(f"Hook '{hook_name}' from module '{module_name}' returned False - stopping")
                report_error("deployment", f"Hook '{hook_name}' from module '{module_name}' returned False")
                return trace_out(False)

            debug(f"Hook '{hook_name}' from module '{module_name}' succeeded")

        except Exception as e:
            warn(f"Hook '{hook_name}' from module '{module_name}' raised exception: {e}")
            report_error("deployment", f"Hook '{hook_name}' from module '{module_name}' raised exception: {e}")
            return trace_out(False)

    log(f"All hooks for '{hook_name}' completed successfully")
    return trace_out(True)


def get_all_hook_names() -> List[str]:
    """
    Get list of all registered hook names.

    Returns:
        Sorted list of hook names

    Example:
        >>> names = get_all_hook_names()
        >>> print(names)
        ['deploy_after_schema', 'deploy_before_schema', 'install_config']
    """
    trace_in()
    return trace_out(sorted(hooks.keys()))


def get_hooks_by_module() -> Dict[str, Dict[str, List[str]]]:
    """
    Get hooks organized by module name.

    Returns:
        Dict mapping module_name -> {hook_name -> [function_names]}

    Example:
        >>> by_module = get_hooks_by_module()
        >>> print(by_module['users'])
        {'deploy_before_schema': ['setup_db_users'], 'install_config': ['write_user_config']}
    """
    trace_in()

    result: Dict[str, Dict[str, List[str]]] = {}

    for hook_name, hook_list in hooks.items():
        for hook_info in hook_list:
            module_name = hook_info.module_name
            func_name = hook_info.function_name

            if module_name not in result:
                result[module_name] = {}

            if hook_name not in result[module_name]:
                result[module_name][hook_name] = []

            result[module_name][hook_name].append(func_name)

    return trace_out(result)


def get_hooks_by_name() -> Dict[str, List[tuple[str, str]]]:
    """
    Get hooks organized by hook name.

    Returns:
        Dict mapping hook_name -> [(module_name, function_name), ...]
        Tuples are sorted alphabetically by module_name.

    Example:
        >>> by_name = get_hooks_by_name()
        >>> print(by_name['deploy_before_schema'])
        [('history', 'create_history_tables'), ('users', 'setup_db_users')]
    """
    trace_in()

    result: Dict[str, List[tuple[str, str]]] = {}

    for hook_name, hook_list in hooks.items():
        result[hook_name] = []

        # Sort by module name
        sorted_hooks = sorted(hook_list, key=lambda h: h.module_name)

        for hook_info in sorted_hooks:
            module_name = hook_info.module_name
            func_name = hook_info.function_name
            result[hook_name].append((module_name, func_name))

    return trace_out(result)


# ============================================================
# Cache System
# ============================================================

def _build_hooks_cache() -> Dict[str, Any]:
    """
    Build cache data structure from current in-memory hooks registry.

    Returns:
        Cache dict with structure:
        {
            "hooks": {
                "hook_name": [
                    {
                        "module_name": "users",
                        "module_path": "/path/to/users",
                        "function_module": "users.deploy.deploy_hooks",
                        "function_name": "setup_db_users"
                    },
                    ...
                ],
                ...
            },
            "last_scan": "timestamp"
        }
    """
    trace_in()

    cache_data: Dict[str, Any] = {
        "hooks": {},
        "last_scan": str(time.time())
    }

    for hook_name, hook_list in hooks.items():
        cache_data["hooks"][hook_name] = []

        for hook_info in hook_list:
            cache_data["hooks"][hook_name].append({
                "module_name": hook_info.module_name,
                "module_path": hook_info.module_path,
                "function_module": hook_info.function_module,
                "function_name": hook_info.function_name
            })

    log(f"Built hooks cache with {len(cache_data['hooks'])} hook names")
    return trace_out(cache_data)


def _save_hooks_cache(cache_data: Dict[str, Any]) -> bool:
    """
    Save hooks cache to disk using atomic write pattern.

    Args:
        cache_data: Cache dict to save

    Returns:
        True if saved successfully, False otherwise
    """
    trace_in()

    try:
        # Atomic write: write to temp file, then rename
        temp_file = CACHE_FILE.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        temp_file.replace(CACHE_FILE)

        hook_count = len(cache_data.get('hooks', {}))
        log(f"Saved hooks cache with {hook_count} hook names to {CACHE_FILE}")
        return trace_out(True)

    except Exception as e:
        warn(f"Error saving hooks cache: {e}")

        # Clean up temp file if it exists
        temp_file = CACHE_FILE.with_suffix('.tmp')
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass

        return trace_out(False)


def _load_hooks_cache() -> Optional[Dict[str, Any]]:
    """
    Load hooks cache from disk.

    Returns:
        Cache dict if successful, None otherwise
    """
    trace_in()

    if not CACHE_FILE.exists():
        log("Hooks cache file does not exist")
        return trace_out(None)

    try:
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)

        hook_count = len(cache_data.get('hooks', {}))
        log(f"Loaded hooks cache with {hook_count} hook names from {CACHE_FILE}")
        return trace_out(cache_data)

    except json.JSONDecodeError as e:
        warn(f"JSON decode error reading hooks cache: {e}")
        return trace_out(None)
    except Exception as e:
        warn(f"Error loading hooks cache: {e}")
        return trace_out(None)


def discover_module_hooks(force_regenerate: bool = False) -> Dict[str, Any]:
    """
    Discover all module hooks by scanning for @register_module_hook decorators.

    Loads hook metadata from cache into hot cache (strings only, no callables).
    Actual imports happen lazily via get_hook_handlers().

    If hot cache already populated, no-ops. If cache exists, loads JSON into hot cache.
    Otherwise, scans and builds cache.

    Args:
        force_regenerate: If True, force rescan even if cache exists

    Returns:
        Cache dict with hooks structure

    Example:
        >>> cache = discover_module_hooks()
        >>> print(cache['hooks'].keys())
        dict_keys(['deploy_before_schema', 'deploy_after_schema', 'install_config'])
    """
    trace_in()

    # Check if hot cache already populated (avoid redundant work)
    if not force_regenerate and hooks:
        debug(f"Hot cache already populated with {len(hooks)} hook names - skipping discovery")
        # Return cached structure (rebuild from hot cache)
        cache_data = _build_hooks_cache()
        return trace_out(cache_data)

    # Check if cold cache exists and should be used
    if not force_regenerate and CACHE_FILE.exists():
        loaded_cache = _load_hooks_cache()
        if loaded_cache is not None:
            log("Using cached module hooks - populating hot cache with metadata")

            # Populate hot cache with metadata (no callables yet - lazy loaded)
            for hook_name, hook_list in loaded_cache.get('hooks', {}).items():
                if hook_name not in hooks:
                    hooks[hook_name] = []

                for hook_dict in hook_list:
                    hook_info = HookInfo(
                        module_name=hook_dict['module_name'],
                        module_path=hook_dict['module_path'],
                        function_module=hook_dict['function_module'],
                        function_name=hook_dict['function_name'],
                        function=None  # Lazy-loaded by get_hook_handlers()
                    )
                    hooks[hook_name].append(hook_info)

            log(f"Populated hot cache with {len(hooks)} hook names (callables will be lazy-loaded)")
            return trace_out(loaded_cache)

    # Cache doesn't exist or force_regenerate - scan for hooks
    log("Discovering module hooks by scanning for @register_module_hook decorators...")

    # Import all modules with hook decorators
    from hh.deploy.deploy_utils import scan_for_decorator
    hook_files = scan_for_decorator("register_module_hook", exclude_cache=True)

    log(f"Found {len(hook_files)} files with @register_module_hook decorators")

    # Import each module to trigger decorator registration
    import importlib
    for module_path in hook_files:
        try:
            importlib.import_module(module_path)
            debug(f"Imported module with hooks: {module_path}")
        except Exception as e:
            warn(f"Failed to import module {module_path}: {e}")

    # Build and save cache from in-memory registry
    cache_data = _build_hooks_cache()
    _save_hooks_cache(cache_data)

    return trace_out(cache_data)


@register_cache_cleanup('module_hooks', cache_dir='hh/gateway/registry/cache')
def cleanup_module_hooks_cache():
    """Clean up module hooks cache file (module-hooks.json)"""
    trace_in()

    removed_files = []

    # Build candidate cache dirs: local (repo) and deployed
    candidate_dirs = [CACHE_DIR]
    for root in get_deployment_paths():
        candidate_dirs.append(root / 'hh' / 'gateway' / 'registry' / 'cache')

    # Remove module-hooks.json from all candidate directories
    for cache_dir in candidate_dirs:
        cache_file = cache_dir / 'module-hooks.json'
        if cache_file.exists():
            cache_file.unlink()
            removed_files.append(str(cache_file))
            log(f"Removed cache file: {cache_file}")
        else:
            log(f"Cache file does not exist: {cache_file}")

    trace_out()

    return {
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    }
