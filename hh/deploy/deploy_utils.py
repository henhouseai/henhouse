import os
import shutil
import importlib.util
from pathlib import Path
from typing import Tuple, List, Dict, Any, TypeVar, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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
    Load a whitelist from hh/deploy/conf/ with support for ext/deploy/conf/ blacklists and extensions.
    
    Processing order:
    1. Load base whitelist from hh/deploy/conf/{base_name}.py
    2. Load blacklist from ext/deploy/conf/{base_name}_blacklist.py (if exists)
    3. Subtract blacklist items from base
    4. Load extension whitelist from ext/deploy/conf/{base_name}.py (if exists)
    5. For each item in extension:
       - If item already exists in result AND was not blacklisted: WARN
       - Add item to result
    
    Args:
        base_name: Base filename without .py extension (e.g., 'css_whitelist')
        var_name: Variable name to load (e.g., 'CSS_WHITELIST')
        
    Returns:
        Final combined list of strings
    """
    trace_in()
    log(f"Loading whitelist: {base_name}.{var_name}")
    
    # Detect project context
    project_name, project_root = detect_project_context()
    
    # Determine paths
    hh_conf = project_root / "hh" / "deploy" / "conf"
    ext_conf = project_root / "ext" / "deploy" / "conf"
    
    # Step 1: Load base whitelist
    base_file = hh_conf / f"{base_name}.py"
    loaded_result = _load_list_from_file(base_file, var_name)
    
    if loaded_result is None:
        warn(f"Base whitelist {base_name}.{var_name} not found in {base_file}")
        result: List[str] = []
    else:
        # Make a copy to avoid modifying the original
        result = list(loaded_result)
        log(f"Loaded base whitelist: {len(result)} items")
    
    # Track blacklisted items (for warning purposes)
    blacklisted_items: set[str] = set()
    
    # Step 2: Load and apply blacklist
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    # Use same variable name - the file name already indicates it's a blacklist
    blacklist_var_name = var_name
    
    blacklist = _load_list_from_file(blacklist_file, blacklist_var_name)
    if blacklist is not None:
        blacklisted_items = set(blacklist)
        # Remove blacklisted items from result
        result = [item for item in result if item not in blacklisted_items]
        log(f"Applied blacklist: removed {len(blacklisted_items)} items, {len(result)} remaining")
    
    # Step 3: Load and apply extension
    ext_file = ext_conf / f"{base_name}.py"
    ext_list = _load_list_from_file(ext_file, var_name)
    
    if ext_list is not None:
        for item in ext_list:
            if item in result and item not in blacklisted_items:
                warn(f"Duplicate item in extension (not blacklisted): {item} in {ext_file}")
            if item not in result:
                result.append(item)
        log(f"Applied extension: added {len(ext_list)} items, final count: {len(result)}")
    
    trace_out()
    return result


def load_dict_whitelist_with_extensions(
    base_name: str,
    var_name: str
) -> List[Dict[str, Any]]:
    """
    Load a whitelist of dictionaries from hh/deploy/conf/ with support for ext/deploy/conf/ blacklists and extensions.
    
    Same processing order as load_whitelist_with_extensions, but for lists of dictionaries.
    Blacklist matching is done by comparing the entire dictionary structure.
    
    Args:
        base_name: Base filename without .py extension (e.g., 'application_actions')
        var_name: Variable name to load (e.g., 'APPLICATION_ACTIONS')
        
    Returns:
        Final combined list of dictionaries
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
    
    # Determine paths
    hh_conf = project_root / "hh" / "deploy" / "conf"
    ext_conf = project_root / "ext" / "deploy" / "conf"
    debug(f"HH conf path: {hh_conf}")
    debug(f"EXT conf path: {ext_conf}")
    
    # Step 1: Load base whitelist
    base_file = hh_conf / f"{base_name}.py"
    debug(f"Loading base file: {base_file}")
    loaded_result = _load_list_from_file(base_file, var_name)
    
    result: List[Dict[str, Any]] = []
    if loaded_result is None:
        warn(f"Base whitelist {base_name}.{var_name} not found in {base_file}")
        debug(f"Base whitelist NOT FOUND at {base_file}")
    else:
        # Make a copy to avoid modifying the original
        if not isinstance(loaded_result, list):
            warn(f"Base whitelist {base_name}.{var_name} is not a list, got {type(loaded_result)}")
            debug(f"Base whitelist wrong type: {type(loaded_result)}")
        else:
            result = list(loaded_result)
            log(f"Loaded base whitelist: {len(result)} items")
            debug(f"Base whitelist loaded: {len(result)} items")
            for idx, item in enumerate(result):
                debug(f"Base item {idx}: {item}")
    
    # Track blacklisted items (for warning purposes)
    # For dicts, we'll compare by converting to a normalized form (sorted tuple of items)
    blacklisted_items: set[tuple[tuple[str, Any], ...]] = set()
    
    # Step 2: Load and apply blacklist
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    debug(f"Checking blacklist file: {blacklist_file}")
    # Use same variable name - the file name already indicates it's a blacklist
    blacklist_var_name = var_name
    
    blacklist = _load_list_from_file(blacklist_file, blacklist_var_name)
    if blacklist is None:
        debug(f"Blacklist file not found or empty: {blacklist_file}")
    elif len(blacklist) == 0:
        debug(f"Blacklist file exists but is empty: {blacklist_file}")
    if blacklist is not None and len(blacklist) > 0:
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
            debug(f"Before blacklist: {original_count} items")
            result = [
                item for item in result
                if isinstance(item, dict) and item.get('group') not in blacklisted_groups
            ]
            removed_count = original_count - len(result)
            log(f"Applied blacklist (by group name): removed {removed_count} items, {len(result)} remaining")
            debug(f"After blacklist: {len(result)} items, removed {removed_count}")
            for idx, item in enumerate(result):
                debug(f"Remaining item {idx}: {item}")
        else:
            # Blacklist contains dicts - match by full dictionary structure
            debug(f"Blacklist contains dicts (full dict matching)")
            blacklisted_dicts = {tuple(sorted(d.items())) if isinstance(d, dict) else d for d in blacklist}
            blacklisted_items = blacklisted_dicts
            debug(f"Blacklisted dicts: {len(blacklisted_dicts)} items")
            original_count = len(result)
            debug(f"Before blacklist: {original_count} items")
            
            # Remove blacklisted items from result
            result = [
                item for item in result
                if (tuple(sorted(item.items())) if isinstance(item, dict) else item) not in blacklisted_items
            ]
            removed_count = original_count - len(result)
            log(f"Applied blacklist (by dict match): removed {removed_count} items, {len(result)} remaining")
            debug(f"After blacklist: {len(result)} items, removed {removed_count}")
    
    # Step 3: Load and apply extension
    ext_file = ext_conf / f"{base_name}.py"
    debug(f"Checking extension file: {ext_file}")
    ext_list = _load_list_from_file(ext_file, var_name)
    
    if ext_list is None:
        debug(f"Extension file not found or empty: {ext_file}")
    elif len(ext_list) == 0:
        debug(f"Extension file exists but is empty: {ext_file}")
    if ext_list is not None:
        debug(f"Extension loaded: {len(ext_list)} items")
        for idx, item in enumerate(ext_list):
            debug(f"Extension item {idx}: {item}")
        # Convert result items to comparable form for duplicate checking
        result_keys = {_hashable(r) for r in result}
        debug(f"Before extension: {len(result)} items, result_keys: {len(result_keys)}")
        
        added_count = 0
        for item in ext_list:
            item_key = _hashable(item)
            if item_key in result_keys and item_key not in blacklisted_items:
                warn(f"Duplicate item in extension (not blacklisted): {item} in {ext_file}")
                debug(f"Duplicate detected (not blacklisted): {item}")
            if item_key not in result_keys:
                result.append(item)
                result_keys.add(item_key)
                added_count += 1
                debug(f"Added extension item: {item}")
        log(f"Applied extension: added {added_count} items, final count: {len(result)}")
        debug(f"After extension: {len(result)} items, added {added_count}")
        for idx, item in enumerate(result):
            debug(f"Final item {idx}: {item}")
    
    debug(f"Final result: {len(result)} items")
    trace_out()
    return result


# ============ Registry scanning functions ============

def scan_for_decorator(
    decorator_name: str,
    exclude_cache: bool = True
) -> List[str]:
    """
    Scan hh/ and ext/ folders for Python files containing a decorator pattern.
    
    This function scans both the framework (hh/) and user extension (ext/) folders
    for files containing the specified decorator pattern (e.g., "@register_action").
    
    Args:
        decorator_name: Name of the decorator to search for (e.g., "register_action")
                       The function will search for the pattern "@{decorator_name}"
        exclude_cache: If True, skip files starting with "cache_" (default: True)
    
    Returns:
        List of module paths found:
        - For hh/ files: "hh.subfolder.module"
        - For ext/ files: "ext.subfolder.module"
    """
    trace_in()
    found_files: List[str] = []
    pattern = f"@{decorator_name}"
    
    try:
        import hh
        hh_path = Path(hh.__file__).parent
        project_root = hh_path.parent
        
        # Build list of paths to scan
        scan_paths: List[Tuple[Path, str]] = [(hh_path, "hh")]
        
        # Check if ext/ exists and add it to scan paths
        ext_path = project_root / "ext"
        if ext_path.exists() and ext_path.is_dir():
            scan_paths.append((ext_path, "ext"))
            log(f"Found ext/ folder, will scan for {decorator_name}")
        
        # Scan each path
        for scan_path, module_prefix in scan_paths:
            for py_file in scan_path.rglob("*.py"):
                # Skip cache files if requested
                if exclude_cache and py_file.name.startswith("cache_"):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if pattern in content:
                            rel_path = py_file.relative_to(scan_path)
                            module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                            module_path = f"{module_prefix}." + ".".join(module_parts)
                            found_files.append(module_path)
                            log(f"Found {decorator_name} in {module_path}")
                except Exception as e:
                    warn(f"Error reading {py_file}: {e}")
                
    except Exception as e:
        warn(f"Error scanning for {decorator_name}: {e}")
    
    trace_out()
    return found_files
