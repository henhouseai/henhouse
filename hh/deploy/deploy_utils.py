import os
import shutil
import subprocess
import importlib.util
import json
import time
from pathlib import Path
from typing import Tuple, List, Dict, Any, TypeVar, Optional, NamedTuple
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
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

def detect_project_context() -> Tuple[str, Path]:
    trace_in()
    log("Detecting project context")
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            log(f"Found project: {project_name} at {current_path}")
            trace_out()
            return project_name, current_path
        current_path = current_path.parent
    project_name = Path.cwd().name
    log(f"Using current directory as project: {project_name}")
    trace_out()
    return project_name, Path.cwd()


# ============ Whitelist loading functions ============

T = TypeVar('T')

def _load_list_from_file(file_path: Path, var_name: str) -> T | None:
    """
    Load a Python list variable from a file using importlib.
    
    Args:
        file_path: Path to the Python file
        var_name: Name of the variable to extract
        
    Returns:
        The variable value if found, None otherwise
    """
    if not file_path.exists():
        return None
    
    try:
        # Create a module spec from the file
        spec = importlib.util.spec_from_file_location("whitelist_module", file_path)
        if spec is None or spec.loader is None:
            warn(f"Failed to create module spec for {file_path}")
            return None
        
        # Load the module
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract the variable
        if hasattr(module, var_name):
            return getattr(module, var_name)
        else:
            warn(f"Variable {var_name} not found in {file_path}")
            return None
            
    except Exception as e:
        warn(f"Error loading {file_path}: {e}")
        return None


def load_whitelist_with_extensions(
    base_name: str,
    var_name: str
) -> List[str]:
    """
    Load a whitelist from all active modules with support for ext blacklists.

    Processing order:
    1. Load whitelists from all active modules (hh, ext, and regular modules)
    2. Load blacklist from ext/deploy/conf/{base_name}_blacklist.py (if exists)
    3. Subtract blacklist items from combined result
    4. Warn about duplicates across modules but keep first occurrence

    Args:
        base_name: Base filename without .py extension (e.g., 'css_whitelist')
        var_name: Variable name to load (e.g., 'CSS_WHITELIST')

    Returns:
        Final combined list of strings from all modules
    """
    trace_in()
    log(f"Loading whitelist: {base_name}.{var_name}")

    # Detect project context
    project_name, project_root = detect_project_context()

    # Determine paths
    ext_conf = project_root / "ext" / "deploy" / "conf"

    result: List[str] = []
    blacklisted_items: set[str] = set()  # Initialize before try block

    # Step 1: Load whitelists from all active modules equally
    try:
        modules = get_active_modules()
        log(f"Loading {base_name}.{var_name} from {len(modules)} active modules")

        for module in modules:
            module_conf = project_root / module.path / "deploy" / "conf"
            module_file = module_conf / f"{base_name}.py"
            module_list = _load_list_from_file(module_file, var_name)

            if module_list is not None:
                for item in module_list:
                    if item in result:
                        warn(f"Duplicate item '{item}' from {module.name} module (keeping first occurrence)")
                    else:
                        result.append(item)
                log(f"Loaded {len(module_list)} items from {module.name} module")
    except Exception as e:
        warn(f"Error loading module whitelists for {base_name}: {e}")

    # Step 2: Load and apply blacklist
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    blacklist_var_name = var_name

    blacklist = _load_list_from_file(blacklist_file, blacklist_var_name)
    if blacklist is not None:
        blacklisted_items = set(blacklist)
        # Remove blacklisted items from result
        original_count = len(result)
        result = [item for item in result if item not in blacklisted_items]
        removed_count = original_count - len(result)
        if removed_count > 0:
            log(f"Applied blacklist: removed {removed_count} blacklisted items, {len(result)} remaining")

    trace_out()
    return result


def load_tuple_whitelist_with_extensions(
    base_name: str,
    var_name: str
) -> List[tuple]:
    """
    Load a whitelist of tuples from all active modules with support for ext blacklists.

    Processing order:
    1. Load whitelists from all active modules (hh, ext, and regular modules)
    2. Load blacklist from ext/deploy/conf/{base_name}_blacklist.py (if exists)
    3. Subtract blacklist items from combined result
    4. Warn about duplicates across modules but keep first occurrence

    Args:
        base_name: Base filename without .py extension (e.g., 'deploy_whitelist')
        var_name: Variable name to load (e.g., 'APP_WHITELIST')

    Returns:
        Final combined list of tuples from all modules
    """
    trace_in()
    log(f"Loading tuple whitelist: {base_name}.{var_name}")

    # Detect project context
    project_name, project_root = detect_project_context()

    # Determine paths
    ext_conf = project_root / "ext" / "deploy" / "conf"

    result: List[tuple] = []
    blacklisted_items: set[tuple] = set()

    # Step 1: Load whitelists from all active modules equally
    try:
        modules = get_active_modules()
        log(f"Loading {base_name}.{var_name} from {len(modules)} active modules")

        for module in modules:
            module_conf = project_root / module.path / "deploy" / "conf"
            module_file = module_conf / f"{base_name}.py"
            module_list = _load_list_from_file(module_file, var_name)

            if module_list is not None:
                for item in module_list:
                    if item in result:
                        warn(f"Duplicate item '{item}' from {module.name} module (keeping first occurrence)")
                    else:
                        result.append(item)
                log(f"Loaded {len(module_list)} items from {module.name} module")
    except Exception as e:
        warn(f"Error loading module whitelists for {base_name}: {e}")

    # Step 2: Load and apply blacklist
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    blacklist_var_name = var_name

    blacklist = _load_list_from_file(blacklist_file, blacklist_var_name)
    if blacklist is not None:
        blacklisted_items = set(blacklist)
        # Remove blacklisted items from result
        original_count = len(result)
        result = [item for item in result if item not in blacklisted_items]
        removed_count = original_count - len(result)
        if removed_count > 0:
            log(f"Applied blacklist: removed {removed_count} blacklisted items, {len(result)} remaining")

    trace_out()
    return result


def load_dict_whitelist_with_extensions(
    base_name: str,
    var_name: str
) -> List[Dict[str, Any]]:
    """
    Load a whitelist of dictionaries from all active modules in alphabetical order, then apply blacklists.

    Processing includes:
    1. Load configurations from all active modules (sorted alphabetically by module name)
    2. Apply blacklist from ext/deploy/conf/{base_name}_blacklist.py to remove items
    Blacklist matching is done by comparing the entire dictionary structure.

    Args:
        base_name: Base filename without .py extension (e.g., 'site_links')
        var_name: Variable name to load (e.g., 'SITE_LINKS')

    Returns:
        Final combined list of dictionaries after blacklist filtering
    """

    def _hashable(val: Any):
        """Convert nested dict/list structures to hashable tuples for set membership checks."""
        if isinstance(val, dict):
            return tuple(sorted((k, _hashable(v)) for k, v in val.items()))
        if isinstance(val, list):
            return tuple(_hashable(v) for v in val)
        return val
    trace_in()
    log(f"Loading dict whitelist: {base_name}.{var_name}")
    debug(f"Starting load for {base_name}.{var_name}")

    # Detect project context
    project_name, project_root = detect_project_context()
    debug(f"Project: {project_name}, root: {project_root}")

    # Get all active modules and sort alphabetically
    modules = get_active_modules()
    modules_sorted = sorted(modules, key=lambda m: m.name.lower())
    debug(f"Processing {len(modules_sorted)} modules in alphabetical order: {[m.name for m in modules_sorted]}")

    result: List[Dict[str, Any]] = []

    # Step 1: Load all module configurations in alphabetical order
    for module in modules_sorted:
        module_conf = project_root / module.path / "deploy" / "conf"
        module_file = module_conf / f"{base_name}.py"
        module_list = _load_list_from_file(module_file, var_name)

        if module_list is not None and isinstance(module_list, list):
            debug(f"Module {module.name}: loaded {len(module_list)} items")
            for item in module_list:
                # Check for duplicates within this loading phase
                item_key = _hashable(item)
                existing_keys = {_hashable(r) for r in result}
                if item_key not in existing_keys:
                    result.append(item)
                    debug(f"Added item from {module.name}: {item}")
                else:
                    # Find which module this was originally from for warning
                    original_module = None
                    for existing_item in result:
                        if _hashable(existing_item) == item_key:
                            # Find the module that added this item
                            for m in modules_sorted:
                                if m.name < module.name:  # Only check modules that came before alphabetically
                                    m_conf = project_root / m.path / "deploy" / "conf"
                                    m_file = m_conf / f"{base_name}.py"
                                    m_list = _load_list_from_file(m_file, var_name)
                                    if m_list and item in m_list:
                                        original_module = m.name
                                        break
                            break
                    if original_module:
                        warn(f"Duplicate item in {module.name} (already in {original_module}): {item}")
                        debug(f"Duplicate skipped from {module.name}: {item}")

            log(f"Loaded {len(module_list)} items from {module.name} module")
        else:
            debug(f"Module {module.name}: no {base_name}.{var_name} found")

    log(f"Aggregate whitelist before blacklist: {len(result)} items")

    # Step 2: Apply blacklist to remove items
    ext_conf = project_root / "ext" / "deploy" / "conf"
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    debug(f"Checking blacklist file: {blacklist_file}")

    blacklist = _load_list_from_file(blacklist_file, var_name)
    if blacklist is None:
        debug(f"Blacklist file not found or empty: {blacklist_file}")
    elif len(blacklist) == 0:
        debug(f"Blacklist file exists but is empty: {blacklist_file}")
    elif len(blacklist) > 0:
        debug(f"Blacklist loaded: {len(blacklist)} items")
        for idx, item in enumerate(blacklist):
            debug(f"Blacklist item {idx}: {item}")

        # Check if blacklist contains strings (group names) or dicts (full dict matching)
        if isinstance(blacklist[0], str):
            # Blacklist contains strings - match by 'group' key for site_links, application_actions, etc.
            debug(f"Blacklist contains strings (group names)")
            blacklisted_groups = set(blacklist)
            debug(f"Blacklisted groups: {blacklisted_groups}")
            original_count = len(result)
            result = [
                item for item in result
                if isinstance(item, dict) and item.get('group') not in blacklisted_groups
            ]
            removed_count = original_count - len(result)
            log(f"Applied blacklist (by group name): removed {removed_count} items, {len(result)} remaining")
            debug(f"After blacklist: {len(result)} items, removed {removed_count}")
        else:
            # Blacklist contains dicts - match by full dictionary structure
            debug(f"Blacklist contains dicts (full dict matching)")
            blacklisted_dicts = {_hashable(d) if isinstance(d, dict) else d for d in blacklist}
            debug(f"Blacklisted dicts: {len(blacklisted_dicts)} items")
            original_count = len(result)
            result = [
                item for item in result
                if _hashable(item) not in blacklisted_dicts
            ]
            removed_count = original_count - len(result)
            log(f"Applied blacklist (by dict match): removed {removed_count} items, {len(result)} remaining")
            debug(f"After blacklist: {len(result)} items, removed {removed_count}")

    debug(f"Final result: {len(result)} items")
    for idx, item in enumerate(result):
        debug(f"Final item {idx}: {item}")

    trace_out()
    return result


# ============ Module discovery system ============

# Module cache setup
_MODULE_CACHE_DIR: Optional[Path] = None  # Will be initialized on first use
_module_last_scan_time: float = 0.0  # Legacy (no longer used - cache is trusted if it exists)

class ModuleInfo(NamedTuple):
    """Information about a discovered module."""
    name: str
    path: str
    description: Optional[str]
    version: Optional[str]

def _get_module_cache_dir() -> Path:
    """Get the module cache directory, creating it if needed."""
    global _MODULE_CACHE_DIR
    if _MODULE_CACHE_DIR is None:
        # Cache in hh/gateway/registry/cache/
        try:
            import hh
            hh_path = Path(hh.__file__).parent
            _MODULE_CACHE_DIR = hh_path / "gateway" / "registry" / "cache"
            _MODULE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            warn(f"Error creating module cache directory: {e}")
            # Fall back to current directory
            _MODULE_CACHE_DIR = Path.cwd() / ".cache"
            _MODULE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _MODULE_CACHE_DIR

def _read_module_cache_file_with_retry(cache_file: Path) -> Optional[Dict[str, Any]]:
    """Read module cache file with retry logic if file is empty (another process is writing)."""
    try:
        if not cache_file.exists():
            return None

        # Check if file is empty or very small (indicates write in progress)
        file_size = cache_file.stat().st_size
        if file_size == 0:
            log(f"Module cache file {cache_file} is empty, waiting 1 second for other process to finish...")
            time.sleep(1.0)

            # Retry after wait
            if not cache_file.exists():
                return None
            file_size = cache_file.stat().st_size
            if file_size == 0:
                warn(f"Module cache file {cache_file} still empty after retry, treating as invalid")
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
            warn(f"Error reading module cache file {cache_file} after retry: {e2}")
            return None
    except Exception as e:
        warn(f"Error reading module cache file {cache_file}: {e}")
        return None

def get_active_modules(force_regenerate: bool = False) -> List[ModuleInfo]:
    """
    Discover active modules in the project root.

    Scans the project root for folders containing a __module__.py manifest file.
    Uses cold cache (no throttle - trust cache if exists, only rescan if missing or force_regenerate=True).

    Args:
        force_regenerate: If True, force a new scan even if cache exists

    Returns:
        List of ModuleInfo objects for discovered modules
    """
    trace_in()

    cache_dir = _get_module_cache_dir()
    cache_file = cache_dir / "modules.json"
    current_time = time.time()

    # Check if cache exists and should be used (no throttle - trust cache if exists)
    if not force_regenerate and cache_file.exists():
        cache_data = _read_module_cache_file_with_retry(cache_file)
        if cache_data is not None:
            log(f"Using cached modules with {len(cache_data.get('modules', []))} modules")
            modules_data = cache_data.get('modules', [])
            result = [ModuleInfo(**m) for m in modules_data]
            trace_out()
            return result
        else:
            log("Cache file exists but failed to load, proceeding with scan")

    log("Discovering active modules...")

    # Get project root
    try:
        project_name, project_root = detect_project_context()
    except Exception as e:
        warn(f"Error detecting project context: {e}")
        report_error("deploy_utils", f"Error detecting project context: {e}")
        trace_out()
        return []

    # Load blacklist
    blacklist_file = project_root / "ext" / "deploy" / "conf" / "module_blacklist.py"
    blacklist = _load_list_from_file(blacklist_file, "MODULE_BLACKLIST")
    blacklisted_modules: set[str] = set(blacklist) if blacklist else set()
    if blacklisted_modules:
        log(f"Loaded module blacklist: {blacklisted_modules}")

    # Exclusion rules (always excluded, in addition to blacklist)
    always_excluded = {'.git', 'git', '__pycache__', 'venv', '.venv', 'node_modules'}

    modules: List[ModuleInfo] = []

    # Scan project root for folders
    try:
        for item in project_root.iterdir():
            # Skip if not a directory
            if not item.is_dir():
                continue

            folder_name = item.name

            # Skip if starts with . or _
            if folder_name.startswith('.') or folder_name.startswith('_'):
                continue

            # Skip if in always excluded list
            if folder_name in always_excluded:
                continue

            # Skip if blacklisted
            if folder_name in blacklisted_modules:
                log(f"Skipping blacklisted module: {folder_name}")
                continue

            # Check for __module__.py manifest
            manifest_file = item / "__module__.py"
            if not manifest_file.exists():
                continue

            # Load manifest
            try:
                manifest_data = _load_list_from_file(manifest_file, "MODULE")
                if manifest_data is None:
                    # Try loading as a dict directly
                    spec = importlib.util.spec_from_file_location("module_manifest", manifest_file)
                    if spec is None or spec.loader is None:
                        warn(f"Failed to load manifest from {manifest_file}")
                        continue

                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, 'MODULE'):
                        manifest_data = getattr(module, 'MODULE')
                    else:
                        warn(f"MODULE not found in {manifest_file}")
                        continue

                # Extract module info
                if isinstance(manifest_data, dict):
                    module_info = ModuleInfo(
                        name=manifest_data.get('name', folder_name),
                        path=folder_name,
                        description=manifest_data.get('description'),
                        version=manifest_data.get('version')
                    )
                    modules.append(module_info)
                    log(f"Discovered module: {folder_name} (name: {module_info.name})")
                else:
                    warn(f"MODULE in {manifest_file} is not a dict: {type(manifest_data)}")

            except Exception as e:
                warn(f"Error loading manifest from {manifest_file}: {e}")
                report_error("deploy_utils", f"Error loading manifest from {manifest_file}: {e}")
                continue

    except Exception as e:
        warn(f"Error scanning for modules: {e}")
        report_error("deploy_utils", f"Error scanning for modules: {e}")

    # Write cache
    modules_data = [
        {
            'name': m.name,
            'path': m.path,
            'description': m.description,
            'version': m.version
        }
        for m in modules
    ]

    cache_data = {
        "modules": modules_data,
        "last_scan": str(current_time)
    }

    try:
        # Atomic write using temp file
        temp_file = cache_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        temp_file.replace(cache_file)
        log(f"Cached modules: {len(modules)} modules")
    except Exception as e:
        warn(f"Error caching modules: {e}")

    trace_out()
    return modules


def get_all_modules(force_regenerate: bool = False) -> List[ModuleInfo]:
    """
    Discover ALL modules in the project root (including blacklisted ones).

    Scans the project root for folders containing a __module__.py manifest file.
    Unlike get_active_modules(), this returns ALL discovered modules regardless of blacklist.
    Uses cold cache (no throttle - trust cache if exists, only rescan if missing or force_regenerate=True).

    Args:
        force_regenerate: If True, force a new scan even if cache exists

    Returns:
        List of ModuleInfo objects for ALL discovered modules (enabled + blacklisted)
    """
    trace_in()

    cache_dir = _get_module_cache_dir()
    cache_file = cache_dir / "modules_all.json"
    current_time = time.time()

    # Check if cache exists and should be used (no throttle - trust cache if exists)
    if not force_regenerate and cache_file.exists():
        cache_data = _read_module_cache_file_with_retry(cache_file)
        if cache_data is not None:
            log(f"Using cached all-modules with {len(cache_data.get('modules', []))} modules")
            modules_data = cache_data.get('modules', [])
            result = [ModuleInfo(**m) for m in modules_data]
            trace_out()
            return result
        else:
            log("Cache file exists but failed to load, proceeding with scan")

    log("Discovering all modules (including blacklisted)...")

    # Get project root
    try:
        project_name, project_root = detect_project_context()
    except Exception as e:
        warn(f"Error detecting project context: {e}")
        report_error("deploy_utils", f"Error detecting project context: {e}")
        trace_out()
        return []

    # Exclusion rules (only the hard-coded ones, no MODULE_BLACKLIST)
    always_excluded = {'.git', 'git', '__pycache__', 'venv', '.venv', 'node_modules'}

    modules: List[ModuleInfo] = []

    # Scan project root for folders (same as get_active_modules but no blacklist check)
    try:
        for item in project_root.iterdir():
            if not item.is_dir():
                continue

            folder_name = item.name

            # Skip if starts with . or _
            if folder_name.startswith('.') or folder_name.startswith('_'):
                continue

            # Skip if in always excluded list
            if folder_name in always_excluded:
                continue

            # NOTE: No blacklist check here - that's the difference from get_active_modules()

            # Check for __module__.py manifest
            manifest_file = item / "__module__.py"
            if not manifest_file.exists():
                continue

            # Load manifest
            try:
                manifest_data = _load_list_from_file(manifest_file, "MODULE")
                if manifest_data is None:
                    spec = importlib.util.spec_from_file_location("module_manifest", manifest_file)
                    if spec is None or spec.loader is None:
                        warn(f"Failed to load manifest from {manifest_file}")
                        continue

                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, 'MODULE'):
                        manifest_data = getattr(module, 'MODULE')
                    else:
                        warn(f"MODULE not found in {manifest_file}")
                        continue

                # Extract module info
                if isinstance(manifest_data, dict):
                    module_info = ModuleInfo(
                        name=manifest_data.get('name', folder_name),
                        path=folder_name,
                        description=manifest_data.get('description'),
                        version=manifest_data.get('version')
                    )
                    modules.append(module_info)
                    debug(f"Discovered module (all): {folder_name} (name: {module_info.name})")
                else:
                    warn(f"MODULE in {manifest_file} is not a dict: {type(manifest_data)}")

            except Exception as e:
                warn(f"Error loading manifest from {manifest_file}: {e}")
                report_error("deploy_utils", f"Error loading manifest from {manifest_file}: {e}")
                continue

    except Exception as e:
        warn(f"Error scanning for modules: {e}")
        report_error("deploy_utils", f"Error scanning for modules: {e}")

    # Write cache
    modules_data = [
        {
            'name': m.name,
            'path': m.path,
            'description': m.description,
            'version': m.version
        }
        for m in modules
    ]

    cache_data = {
        "modules": modules_data,
        "last_scan": str(current_time)
    }

    try:
        # Atomic write using temp file
        temp_file = cache_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        temp_file.replace(cache_file)
        log(f"Cached all-modules: {len(modules)} modules")
    except Exception as e:
        warn(f"Error caching all-modules: {e}")

    log(f"All-modules discovery complete: {len(modules)} modules found")
    trace_out()
    return modules


def get_module_paths() -> List[str]:
    """
    Get list of module paths for scan_for_decorator().

    Returns:
        List of module path prefixes: ['hh', 'ext'] + discovered modules
        Note: 'ext' is always included for backward compatibility with legacy extension system
    """
    trace_in()
    # Always include 'hh' first, then 'ext' for backward compatibility
    paths = ['hh', 'ext']

    # Add discovered peer modules
    try:
        modules = get_active_modules()
        for module in modules:
            paths.append(module.path)
        log(f"Module paths: {paths}")
    except Exception as e:
        warn(f"Error getting module paths: {e}")
        log(f"Using fallback paths (hh + ext only): {paths}")

    trace_out()
    return paths

# Import cache cleanup registry
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup

@register_cache_cleanup('modules', cache_dir='hh/gateway/registry/cache')
def cleanup_module_cache():
    """Clean up module discovery cache (hot and cold)."""
    trace_in()
    global _module_last_scan_time

    # Clear in-memory scan time
    _module_last_scan_time = 0.0
    log("Cleared module discovery scan timestamp")

    # Remove cold cache files
    removed_files = []
    cache_dir = _get_module_cache_dir()
    candidate_files = [
        cache_dir / "modules.json",
        cache_dir / "modules_all.json"
    ]

    # Also check deployment paths
    try:
        from hh.deploy.cache.cache_cleanup_registry import get_deployment_paths
        for root in get_deployment_paths():
            candidate_files.append(root / 'hh' / 'gateway' / 'registry' / 'cache' / 'modules.json')
            candidate_files.append(root / 'hh' / 'gateway' / 'registry' / 'cache' / 'modules_all.json')
    except Exception as e:
        debug(f"Could not get deployment paths: {e}")

    for cache_file in candidate_files:
        if cache_file.exists():
            cache_file.unlink()
            removed_files.append(str(cache_file))
            log(f"Removed module cache file: {cache_file}")
        else:
            log(f"Module cache file does not exist: {cache_file}")

    trace_out()
    return {
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    }

# ============ Registry scanning functions ============

def get_scan_roots() -> List[Path]:
    """
    Get the folders that registry scanners should search: hh/, ext/ and every active module.

    Used by scanners that look for registration calls in source text (maintenance tools,
    download tools, dependencies) so they find code that lives in modules, not just hh/.
    """
    import hh
    project_root = Path(hh.__file__).parent.parent
    roots: List[Path] = []
    for prefix in get_module_paths():
        path = project_root / prefix
        if path.is_dir() and path not in roots:
            roots.append(path)
    return roots


def iter_scan_files(exclude_cache: bool = True):
    """Yield (py_file, scan_root) for every .py file under get_scan_roots(), skipping caches and VCS folders."""
    skip_dirs = {'.git', 'git', '__pycache__', 'node_modules', 'venv', '.venv'}
    for root in get_scan_roots():
        for py_file in root.rglob("*.py"):
            if exclude_cache and py_file.name.startswith("cache_"):
                continue
            if any(part in skip_dirs for part in py_file.relative_to(root).parts[:-1]):
                continue
            yield py_file, root


def scan_for_decorator(
    decorator_name: str,
    exclude_cache: bool = True
) -> List[str]:
    """
    Scan framework and module folders for Python files containing a decorator pattern.

    This function scans the framework (hh/) and all discovered modules
    for files containing the specified decorator pattern (e.g., "@register_action").
    Uses get_module_paths() to discover active modules automatically.

    Args:
        decorator_name: Name of the decorator to search for (e.g., "register_action")
                       The function will search for the pattern "@{decorator_name}"
        exclude_cache: If True, skip files starting with "cache_" (default: True)

    Returns:
        List of module paths found:
        - For hh/ files: "hh.subfolder.module"
        - For module files: "{module_name}.subfolder.module"
    """
    trace_in()
    found_files: List[str] = []
    pattern = f"@{decorator_name}"

    try:
        import hh
        hh_path = Path(hh.__file__).parent
        project_root = hh_path.parent

        # Build list of paths to scan using get_module_paths()
        scan_paths: List[Tuple[Path, str]] = []
        module_prefixes = get_module_paths()

        for module_prefix in module_prefixes:
            if module_prefix == 'hh':
                module_path = hh_path
            else:
                module_path = project_root / module_prefix

            # Only add if the path exists
            if module_path.exists() and module_path.is_dir():
                scan_paths.append((module_path, module_prefix))
                log(f"Will scan {module_prefix}/ for {decorator_name}")

        # Scan each path
        for scan_path, module_prefix in scan_paths:
            for py_file in scan_path.rglob("*.py"):
                # Skip cache files if requested
                if exclude_cache and py_file.name.startswith("cache_"):
                    continue

                # Skip any file inside .git or git directories
                skip_file = False
                for parent in py_file.parents:
                    if parent.name in ('.git', '__pycache__', 'node_modules', 'venv', '.venv'):
                        skip_file = True
                        break
                if skip_file:
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if pattern in content:
                            rel_path = py_file.relative_to(scan_path)
                            module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                            full_module_path = f"{module_prefix}." + ".".join(module_parts)
                            found_files.append(full_module_path)
                            log(f"Found {decorator_name} in {full_module_path}")
                except Exception as e:
                    warn(f"Error reading {py_file}: {e}")
                
    except Exception as e:
        warn(f"Error scanning for {decorator_name}: {e}")
    
    trace_out()
    return found_files


# ============ Certificate management functions ============
