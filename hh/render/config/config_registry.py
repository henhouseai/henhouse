"""
Icon and Label registry system with hot/cold cache.

Provides decorator @register_label for registering icons and labels
in Python modules, replacing the need for .ini files.
Uses hot cache (in-memory) and cold cache (JSON) for fast lookups.
"""
from __future__ import annotations
import json
import importlib
import importlib.util
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
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

# Hot cache: in-memory registry
# Stores (value, module_path) tuples
_icon_registry: Dict[str, Optional[tuple[str, str]]] = {}
_label_registry: Dict[str, Optional[tuple[str, str]]] = {}

# Throttling: prevent repeated scans within 1 hour
_last_scan_time: float = 0.0
SCAN_THROTTLE_SECONDS = 3600.0

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

def _scan_for_config_registrations() -> List[str]:
    """Scan hh/ and ext/ folders for files containing @register_label decorators"""
    trace_in()
    from hh.deploy.deploy_utils import scan_for_decorator
    found_files = scan_for_decorator("register_label", exclude_cache=True)
    trace_out()
    return found_files

def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, str | None]]:
    """Import modules and return import results"""
    trace_in()
    import_results = {}
    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)
            import_results[module_path] = {
                "status": "success",
                "error": None
            }
            log(f"Successfully imported {module_path}")
        except Exception as e:
            import_results[module_path] = {
                "status": "failed",
                "error": str(e)
            }
            warn(f"Failed to import {module_path}: {e}")
    trace_out()
    return import_results

def discover_config_registrations(force_regenerate: bool = False) -> Dict[str, Dict[str, Any]]:
    """Discover all icon and label registrations and build cache"""
    trace_in()
    import time
    
    global _last_scan_time
    
    cache_file = CACHE_DIR / "config-registry.json"
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
                log(f"Throttling: using cached config registry (scanned {time_since_scan:.1f}s ago, throttle: {SCAN_THROTTLE_SECONDS}s, force_regenerate={force_regenerate} ignored)")
                trace_out()
                return cache_data
            
            # Cache exists and is old enough - check if we should use it or regenerate
            if not force_regenerate:
                log(f"Found config registry cache with {len(cache_data.get('icons', {}))} icons and {len(cache_data.get('labels', {}))} labels (last scan: {time_since_scan:.1f}s ago)")
                trace_out()
                return cache_data
            else:
                log(f"Force regenerate requested, but cache exists (last scan: {time_since_scan:.1f}s ago) - proceeding with scan")
    
    log("Discovering config registrations...")
    # Clear hot cache registries before importing (prevents duplicates if modules re-execute)
    _icon_registry.clear()
    _label_registry.clear()
    # Scan for @register_label decorators
    config_files = _scan_for_config_registrations()
    import_results = _import_modules(config_files)
    
    # Build cache data
    # Note: _icon_registry and _label_registry are populated during module imports above
    cache_data = {
        "icons": {},
        "labels": {},
        "last_scan": str(Path(__file__).stat().st_mtime)
    }
    
    # Track seen registrations to detect duplicates during discovery
    seen_icons: Dict[str, str] = {}
    seen_labels: Dict[str, str] = {}
    
    # Process successfully loaded icons
    for icon_name, icon_data in _icon_registry.items():
        if icon_data is not None:
            icon_value, icon_module = icon_data
            # Check for duplicates
            if icon_name in seen_icons:
                warn(f"Duplicate icon '{icon_name}' detected during cache discovery: first seen in {seen_icons[icon_name]}, now also in {icon_module}")
            else:
                seen_icons[icon_name] = icon_module
            
            cache_data["icons"][icon_name] = {
                "value": icon_value,
                "module": icon_module
            }
            log(f"Found icon: {icon_name} = {icon_value} from {icon_module}")
    
    # Process successfully loaded labels (stored without l_ prefix)
    for label_name, label_data in _label_registry.items():
        if label_data is not None:
            label_value, label_module = label_data
            # Check for duplicates
            if label_name in seen_labels:
                warn(f"Duplicate label '{label_name}' detected during cache discovery: first seen in {seen_labels[label_name]}, now also in {label_module}")
            else:
                seen_labels[label_name] = label_module
            
            # Store in cache without l_ prefix
            cache_data["labels"][label_name] = {
                "value": label_value,
                "module": label_module
            }
            log(f"Found label: {label_name} = {label_value} from {label_module}")
    
    # Write cache with current timestamp
    cache_data['last_scan'] = str(current_time)
    _last_scan_time = current_time
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        log(f"Cached config registrations: {len(cache_data['icons'])} icons, {len(cache_data['labels'])} labels")
    except Exception as e:
        warn(f"Error caching config registrations: {e}")
    
    trace_out()
    return cache_data

def register_label(name: str, label_value: str, icon_value: Optional[str] = None):
    """Decorator for registering a label and optionally an icon
    
    Args:
        name: Label/icon name (with or without l_ prefix for labels, will be stored without prefix)
        label_value: Label text value
        icon_value: Optional icon emoji/value (if provided, registers icon with same name)
    """
    def decorator(func):
        # Store without l_ prefix for consistency
        reg_name = name.lower()
        if reg_name.startswith('l_'):
            reg_name = reg_name[2:]
        
        # Register label
        if reg_name in _label_registry and _label_registry[reg_name] is not None:
            existing_value, existing_module = _label_registry[reg_name]
            warn(f"Duplicate label registration detected: '{reg_name}' already registered in {existing_module} with value '{existing_value}', now being registered in {func.__module__} with value '{label_value}'")
        
        _label_registry[reg_name] = (label_value, func.__module__)
        log(f"Registered label: {name} = {label_value} -> {func.__module__}.{func.__name__}")
        
        # Register icon if provided
        if icon_value:
            if reg_name in _icon_registry and _icon_registry[reg_name] is not None:
                existing_value, existing_module = _icon_registry[reg_name]
                warn(f"Duplicate icon registration detected: '{reg_name}' already registered in {existing_module} with value '{existing_value}', now being registered in {func.__module__} with value '{icon_value}'")
            
            _icon_registry[reg_name] = (icon_value, func.__module__)
            log(f"Registered icon: {name} = {icon_value} -> {func.__module__}.{func.__name__}")
        
        return func
    return decorator

def get_label(name: str) -> Optional[str]:
    """Get label from registry (checks hot cache, then cold cache, then rebuilds)"""
    trace_in()
    # Labels in registry are stored without l_ prefix
    k = name.lower()
    if k.startswith('l_'):
        k = k[2:]  # Remove l_ prefix for lookup
    
    # 1. Check hot cache first
    if k in _label_registry:
        label_data = _label_registry[k]
        if label_data is not None:
            label_value, _ = label_data
            log(f"Found label '{name}' in hot cache")
            trace_out()
            return label_value
    
    # 2. Not in hot cache - check cold cache and load
    log(f"Label '{name}' not in hot cache, checking cold cache")
    cache_data = discover_config_registrations()
    label_info = cache_data.get('labels', {}).get(k)
    if label_info:
        # Handle both old format (string) and new format (dict with value/module)
        if isinstance(label_info, dict):
            label_value_raw = label_info.get('value')
            label_value = str(label_value_raw) if label_value_raw is not None else ''
            module_val = label_info.get('module', 'unknown')
            label_module = str(module_val) if module_val is not None else 'unknown'
        else:
            # Old format - just a string
            label_value = str(label_info) if label_info is not None else ''
            label_module = 'unknown'
        
        if label_value:
            # Update hot cache
            _label_registry[k] = (label_value, label_module)
            log(f"Found label '{name}' in cold cache from {label_module}, updated hot cache")
            trace_out()
            return label_value
    
    # Also try with l_ prefix in cache (for backwards compatibility)
    label_info_alt = cache_data.get('labels', {}).get(f'l_{k}')
    if label_info_alt:
        if isinstance(label_info_alt, dict):
            label_value_raw = label_info_alt.get('value')
            label_value = str(label_value_raw) if label_value_raw is not None else ''
            module_val = label_info_alt.get('module', 'unknown')
            label_module = str(module_val) if module_val is not None else 'unknown'
        else:
            label_value = str(label_info_alt) if label_info_alt is not None else ''
            label_module = 'unknown'
        
        if label_value:
            _label_registry[k] = (label_value, label_module)
            log(f"Found label '{name}' in cold cache (with l_ prefix) from {label_module}, updated hot cache")
            trace_out()
            return label_value
    
    # 3. Not known - rebuild cold cache
    log(f"Label '{name}' not found, rebuilding cache...")
    discover_config_registrations(force_regenerate=True)
    
    # 4. Check hot cache again
    if k in _label_registry:
        label_data = _label_registry[k]
        if label_data is not None:
            label_value, _ = label_data
            log(f"Found label '{name}' after rebuild")
            trace_out()
            return label_value
    
    # 5. Not found - return None (will fall back to old method)
    log(f"Label '{name}' not found after full rebuild")
    trace_out()
    return None

def get_icon(name: str) -> Optional[str]:
    """Get icon from registry (checks hot cache, then cold cache, then rebuilds)"""
    trace_in()
    k = name.lower()
    
    # 1. Check hot cache first
    if k in _icon_registry:
        icon_data = _icon_registry[k]
        if icon_data is not None:
            icon_value, _ = icon_data
            log(f"Found icon '{name}' in hot cache")
            trace_out()
            return icon_value
    
    # 2. Not in hot cache - check cold cache and load
    log(f"Icon '{name}' not in hot cache, checking cold cache")
    cache_data = discover_config_registrations()
    icon_info = cache_data.get('icons', {}).get(k)
    if icon_info:
        # Handle both old format (string) and new format (dict with value/module)
        if isinstance(icon_info, dict):
            icon_value_raw = icon_info.get('value')
            icon_value = str(icon_value_raw) if icon_value_raw is not None else ''
            module_val = icon_info.get('module', 'unknown')
            icon_module = str(module_val) if module_val is not None else 'unknown'
        else:
            # Old format - just a string
            icon_value = str(icon_info) if icon_info is not None else ''
            icon_module = 'unknown'
        
        if icon_value:
            # Update hot cache
            _icon_registry[k] = (icon_value, icon_module)
            log(f"Found icon '{name}' in cold cache from {icon_module}, updated hot cache")
            trace_out()
            return icon_value
    
    # 3. Not known - rebuild cold cache
    log(f"Icon '{name}' not found, rebuilding cache...")
    discover_config_registrations(force_regenerate=True)
    
    # 4. Check hot cache again
    if k in _icon_registry:
        icon_data = _icon_registry[k]
        if icon_data is not None:
            icon_value, _ = icon_data
            log(f"Found icon '{name}' after rebuild")
            trace_out()
            return icon_value
    
    # 5. Not found - return None (will fall back to old method)
    log(f"Icon '{name}' not found after full rebuild")
    trace_out()
    return None

@register_cache_cleanup('config_registry', cache_dir='hh/render/config/cache')
def cleanup_config_registry_cache():
    """Clean up config registry cache files (persistent cache - needs post-parser cleanup)"""
    trace_in()
    # Clear hot cache
    _icon_registry.clear()
    _label_registry.clear()
    log("Cleared config registry hot cache")
    
    # Remove cold cache file
    removed_files = []
    candidate_files = [CACHE_DIR / "config-registry.json"]
    for root in get_deployment_paths():
        candidate_files.append(root / 'hh' / 'render' / 'config' / 'cache' / 'config-registry.json')
    
    for cache_file in candidate_files:
        if cache_file.exists():
            cache_file.unlink()
            removed_files.append(str(cache_file))
            log(f"Removed cold cache file: {cache_file}")
        else:
            log(f"Cold cache file does not exist: {cache_file}")
    
    trace_out()
    return {
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    }

