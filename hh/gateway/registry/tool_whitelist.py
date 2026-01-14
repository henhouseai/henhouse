"""
MCP Whitelist System - Decorator-based lazy-loading whitelist generator.

Replaces monolithic mcp_whitelist.py with decorator-based registration.
Generates tier-specific whitelists (guest, verified, admin, root) on demand.
"""
from __future__ import annotations
import json
import importlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup, get_deployment_paths
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Throttling: prevent repeated scans within 1 hour
_last_whitelist_scan_time: float = 0.0
SCAN_THROTTLE_SECONDS = 3600.0

# Global registry of tool registrations (populated by decorators)
_global_tool_registry: Dict[str, Dict[str, Any]] = {}

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

def register_tool(
    tool_name: str,
    description: str = '',
    inputSchema: Optional[Dict[str, Any]] = None,
    mcp_tiers: Optional[List[int]] = None,
    api_tiers: Optional[List[int]] = None,
    app_action_tiers: Optional[List[int]] = None,
    role_whitelist: Optional[List[str]] = None,
    requires_approval: Optional[bool] = None,
    crud_type: Optional[str] = None,
    display_color: Optional[str] = None,
    app_action_group: Optional[str] = None,
    app_action_label: Optional[str] = None
) -> Callable:
    """
    Decorator to register a tool across MCP, API, and app action backends.

    Args:
        tool_name: Name of the tool (REQUIRED)
        description: Tool description (required only for MCP tools)
        inputSchema: JSON Schema for tool arguments (required only for MCP tools)
        mcp_tiers: List of MCP tier levels (1-4). Requires description and inputSchema.
        api_tiers: List of API tier levels (1-4). Only needs tool_name and api_tiers.
        app_action_tiers: List of app action tier levels (1-4). Requires app_action_group.
        role_whitelist: List of MCP role names. Defaults to [] for MCP tools.
        requires_approval: Whether tool requires approval queue (optional, stored in MCP registry)
        crud_type: Operation type (optional, stored in MCP registry)
        display_color: Optional color for approval interface
        app_action_group: Menu group for app actions (required if app_action_tiers specified)
        app_action_label: Display label for app actions (defaults to tool_name if not specified)
    """
    def decorator(func: Callable) -> Callable:
        # Check if tool is assigned to any tier
        has_mcp = mcp_tiers and len(mcp_tiers) > 0
        has_api = api_tiers and len(api_tiers) > 0
        has_app_action = app_action_tiers and len(app_action_tiers) > 0

        # If no tiers specified, just reserve the name (no-op)
        if not has_mcp and not has_api and not has_app_action:
            log(f"Registered tool (name reservation only): {tool_name}")
            _global_tool_registry[tool_name] = {
                'description': '',
                'inputSchema': {},
                'mcp_tiers': [],
                'api_tiers': [],
                'app_action_tiers': [],
                'role_whitelist': [],
                'module': func.__module__,
                'function': func.__name__
            }
            return func

        # Validate MCP tools
        if has_mcp:
            if not description:
                raise ValueError(f"Tool '{tool_name}' has mcp_tiers but missing description")
            if not inputSchema:
                raise ValueError(f"Tool '{tool_name}' has mcp_tiers but missing inputSchema")

        # Validate app action tools
        final_app_action_label = app_action_label
        if has_app_action:
            if not app_action_group:
                raise ValueError(f"Tool '{tool_name}' has app_action_tiers but missing app_action_group")
            # Default label to tool_name if not specified
            if final_app_action_label is None or final_app_action_label == '':
                final_app_action_label = tool_name

        # Store in registry
        _global_tool_registry[tool_name] = {
            'description': description,
            'inputSchema': inputSchema or {},
            'mcp_tiers': mcp_tiers or [],
            'api_tiers': api_tiers or [],
            'app_action_tiers': app_action_tiers or [],
            'role_whitelist': role_whitelist if role_whitelist is not None else [],
            'requires_approval': requires_approval,
            'crud_type': crud_type,
            'display_color': display_color,
            'app_action_group': app_action_group,
            'app_action_label': final_app_action_label,
            'module': func.__module__,
            'function': func.__name__
        }
        log(f"Registered tool: {tool_name} -> {func.__module__}.{func.__name__} (mcp_tiers: {mcp_tiers}, api_tiers: {api_tiers}, app_action_tiers: {app_action_tiers}, role_whitelist: {role_whitelist if role_whitelist is not None else []})")
        return func
    return decorator

def _scan_for_mcp_tools() -> List[str]:
    """Scan hh/ and ext/ folders for files containing @register_tool decorators."""
    trace_in()
    from hh.deploy.deploy_utils import scan_for_decorator
    found_files = scan_for_decorator("register_tool", exclude_cache=True)
    return trace_out(found_files)

def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, Optional[str]]]:
    """Import modules and return import results."""
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
    return trace_out(import_results)

def _rebuild_all_tier_whitelists() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Rebuild MCP whitelists for all tiers by scanning decorators. Returns dict mapping tier -> whitelist."""
    trace_in()
    log("Rebuilding MCP whitelists for all tiers")

    # Scan for decorators
    tool_files = _scan_for_mcp_tools()
    import_results = _import_modules(tool_files)

    # Build whitelists for each tier
    all_tier_whitelists: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for tier in HENHOUSE_TIERS:
        all_tier_whitelists[tier] = {}

    # Filter tools for each tier - only process MCP tools
    for tool_name, tool_config in _global_tool_registry.items():
        mcp_tier_levels = tool_config.get('mcp_tiers', [])

        if not mcp_tier_levels:
            # This tool has no MCP access, skip
            continue

        # Build MCP format entry (description, inputSchema, role_whitelist, module info, and optional fields)
        mcp_entry = {
            'description': tool_config['description'],
            'inputSchema': tool_config['inputSchema'],
            'role_whitelist': tool_config.get('role_whitelist', []),
            'module': tool_config.get('module'),
            'function': tool_config.get('function')
        }

        # Add optional fields if present
        if tool_config.get('requires_approval') is not None:
            mcp_entry['requires_approval'] = tool_config['requires_approval']
        if tool_config.get('crud_type') is not None:
            mcp_entry['crud_type'] = tool_config['crud_type']

        # Add to whitelists for MCP tier levels (1-4)
        # Convert tier levels 1-4 to tier names
        for tier_level in mcp_tier_levels:
            if 1 <= tier_level <= 4:
                tier_index = tier_level - 1  # Convert 1-based level to 0-based index
                if 0 <= tier_index < len(HENHOUSE_TIERS):
                    tier_name = HENHOUSE_TIERS[tier_index]
                    if tier_name in all_tier_whitelists:
                        all_tier_whitelists[tier_name][tool_name] = mcp_entry
                        log(f"Added tool '{tool_name}' to {tier_name} MCP whitelist")

    return trace_out(all_tier_whitelists)
def _rebuild_all_api_whitelists() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Rebuild API whitelists for all tiers. Returns dict mapping tier -> dict of tool entries with module info."""
    trace_in()
    log("Rebuilding API whitelists for all tiers")

    # Build whitelists for each tier - dict with tool entries including module info
    all_tier_whitelists: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for tier in HENHOUSE_TIERS:
        all_tier_whitelists[tier] = {}

    # Filter tools for each tier - only process API tools
    for tool_name, tool_config in _global_tool_registry.items():
        api_tier_levels = tool_config.get('api_tiers', [])

        if not api_tier_levels:
            # This tool has no API access, skip
            continue

        # Build API entry with module info
        api_entry = {
            'module': tool_config.get('module'),
            'function': tool_config.get('function')
        }

        # Add to appropriate tier whitelists
        for tier_level in api_tier_levels:
            if 1 <= tier_level <= 4:
                tier_index = tier_level - 1  # Convert 1-based level to 0-based index
                if 0 <= tier_index < len(HENHOUSE_TIERS):
                    tier_name = HENHOUSE_TIERS[tier_index]
                    all_tier_whitelists[tier_name][tool_name] = api_entry
                    log(f"Added '{tool_name}' to {tier_name} API whitelist")

    return trace_out(all_tier_whitelists)

class MCPWhitelist:
    """MCP Whitelist manager with lazy loading per tier."""
    
    _tier_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    @classmethod
    def _get_cache_file(cls, tier: str) -> Path:
        """Get MCP whitelist cache file path for a tier."""
        return CACHE_DIR / f"mcp-whitelist-{tier}.json"

    @classmethod
    def _get_api_cache_file(cls, tier: str) -> Path:
        """Get API whitelist cache file path for a tier."""
        return CACHE_DIR / f"api-whitelist-{tier}.json"

    @classmethod
    def _load_tier_whitelist(cls, tier: str, force_rebuild: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load whitelist for a tier (from cache or rebuild)."""
        trace_in()
        import time
        
        global _last_whitelist_scan_time
        
        # Check if already loaded in memory
        if tier in cls._tier_cache and not force_rebuild:
            log(f"Using cached whitelist for tier: {tier}")
            return trace_out(cls._tier_cache[tier])
        
        cache_file = cls._get_cache_file(tier)
        current_time = time.time()
        
        # Always check throttle first, even if force_rebuild is True
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
                time_since_memory_scan = current_time - _last_whitelist_scan_time
                
                # If we've scanned recently, honor throttle and use cache (ignore force_rebuild)
                if time_since_scan < SCAN_THROTTLE_SECONDS or time_since_memory_scan < SCAN_THROTTLE_SECONDS:
                    log(f"Throttling: using cached {tier} whitelist (scanned {time_since_scan:.1f}s ago, throttle: {SCAN_THROTTLE_SECONDS}s, force_rebuild={force_rebuild} ignored)")
                    cls._tier_cache[tier] = cache_data.get('whitelist', cache_data)  # Support both formats
                    return trace_out(cls._tier_cache[tier])
                
                # Cache exists and is old enough - check if we should use it or regenerate
                if not force_rebuild:
                    whitelist = cache_data.get('whitelist', cache_data)  # Support both formats
                    cls._tier_cache[tier] = whitelist
                    log(f"Loaded {tier} whitelist from cache: {len(whitelist)} tools (last scan: {time_since_scan:.1f}s ago)")
                    return trace_out(whitelist)
                else:
                    log(f"Force rebuild requested, but cache exists (last scan: {time_since_scan:.1f}s ago) - proceeding with rebuild")
        
        # Rebuild all tier whitelists at once (since we're doing all the work anyway)
        log(f"Rebuilding all tier whitelists (triggered by {tier} miss)...")
        all_tier_whitelists = _rebuild_all_tier_whitelists()
        all_api_whitelists: Dict[str, Dict[str, Dict[str, Any]]] = _rebuild_all_api_whitelists()
        # Note: app actions use hot cache only (get_app_actions reads from _global_tool_registry)

        # Update in-memory scan time
        _last_whitelist_scan_time = current_time

        # Save all MCP tier whitelists to cold cache
        for rebuild_tier, rebuild_whitelist in all_tier_whitelists.items():
            tier_cache_file = cls._get_cache_file(rebuild_tier)
            try:
                # Include last_scan timestamp in cache
                cache_data = {
                    'whitelist': rebuild_whitelist,
                    'last_scan': str(current_time)
                }

                with open(tier_cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                log(f"Cached {rebuild_tier} MCP whitelist: {len(rebuild_whitelist)} tools")
            except Exception as e:
                warn(f"Error caching {rebuild_tier} MCP whitelist: {e}")

        # Save all API tier whitelists to cold cache
        for rebuild_tier, api_tool_dict in all_api_whitelists.items():
            tier_cache_file = cls._get_api_cache_file(rebuild_tier)
            try:
                # Include last_scan timestamp in cache
                cache_data = {
                    'whitelist': api_tool_dict,
                    'last_scan': str(current_time)
                }

                with open(tier_cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                log(f"Cached {rebuild_tier} API whitelist: {len(api_tool_dict)} tools")
            except Exception as e:
                warn(f"Error caching {rebuild_tier} API whitelist: {e}")

        # Update in-memory cache for all tiers
        cls._tier_cache.update(all_tier_whitelists)

        whitelist = all_tier_whitelists.get(tier, {})
        return trace_out(whitelist)
    
    @classmethod
    def get_tool(cls, tier: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool metadata for a specific tier and tool name."""
        trace_in()
        whitelist = cls._load_tier_whitelist(tier)
        tool = whitelist.get(tool_name)
        if tool:
            log(f"Found tool '{tool_name}' in {tier} whitelist")
        else:
            # Tool not found - try rebuilding
            log(f"Tool '{tool_name}' not found in {tier} whitelist, rebuilding...")
            whitelist = cls._load_tier_whitelist(tier, force_rebuild=True)
            tool = whitelist.get(tool_name)
            if tool:
                log(f"Found tool '{tool_name}' after rebuild")
            else:
                warn(f"Tool '{tool_name}' not found in {tier} whitelist after rebuild")
        return trace_out(tool)
    
    @classmethod
    def list_tools(cls, tier: str, roles: List[str]) -> List[Dict[str, Any]]:
        """List all tools available for a tier and role list (for tools/list).

        Args:
            tier: User tier (guest, verified, admin, root)
            roles: List of roles (e.g., ["general", "worker", "auditor"])

        Returns:
            List of tools where ANY role in user's list matches ANY role in tool's role_whitelist.
            This creates an inheritance pattern where multiple roles accumulate tool access.
        """
        trace_in()
        whitelist = cls._load_tier_whitelist(tier)
        tools = []
        user_role_set = set(roles)

        for tool_name, tool_config in whitelist.items():
            # Filter by role_whitelist - empty list means no roles see this tool
            role_whitelist = tool_config.get('role_whitelist', [])
            tool_role_set = set(role_whitelist)

            # Include tool if ANY user role matches ANY tool role (set intersection)
            if user_role_set & tool_role_set:
                tools.append({
                    'name': tool_name,
                    'description': tool_config['description'],
                    'inputSchema': tool_config['inputSchema']
                })

        log(f"Listed {len(tools)} tools for tier: {tier}, roles: {roles}")
        return trace_out(tools)
    
    @classmethod
    def validate_tool(cls, tier: str, tool_name: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """Validate tool exists for tier and arguments match schema."""
        trace_in()
        tool = cls.get_tool(tier, tool_name)
        if not tool:
            return trace_out((False, f"Tool '{tool_name}' not available for tier '{tier}'"))
        
        # Validate arguments against schema
        schema = tool['inputSchema']
        required = schema.get('required', [])
        for field in required:
            if field not in args:
                return trace_out((False, f"Missing required field: {field}"))
        
        # Type checking with automatic coercion
        properties = schema.get('properties', {})
        for key, value in args.items():
            if key not in properties:
                continue  # Allow extra fields
            prop_schema = properties[key]
            expected_type = prop_schema.get('type')
            
            # Try automatic type coercion for common cases
            if expected_type == 'integer' and not isinstance(value, int):
                # Try to coerce string numbers to integers
                if isinstance(value, str) and value.isdigit():
                    args[key] = int(value)
                    value = args[key]  # Update value for remaining checks
                elif isinstance(value, str) and (value.startswith('-') and value[1:].isdigit()):
                    args[key] = int(value)
                    value = args[key]
                elif not isinstance(value, int):
                    return trace_out((False, f"Field '{key}' must be an integer"))
            elif expected_type == 'string' and not isinstance(value, str):
                return trace_out((False, f"Field '{key}' must be a string"))
            elif expected_type == 'boolean' and not isinstance(value, bool):
                return trace_out((False, f"Field '{key}' must be a boolean"))
            elif expected_type == 'array' and not isinstance(value, list):
                return trace_out((False, f"Field '{key}' must be an array"))
            elif expected_type == 'object' and not isinstance(value, dict):
                return trace_out((False, f"Field '{key}' must be an object"))

        return trace_out((True, ""))
    
    @classmethod
    def tool_exists(cls, tier: str, tool_name: str) -> bool:
        """Check if tool exists for tier."""
        tool = cls.get_tool(tier, tool_name)
        return tool is not None
    
    @classmethod
    def get_app_actions(cls, user_tier_level: int) -> List[Dict[str, Any]]:
        """Get app actions available for a user tier level (1-4). Returns actions with app_action_tiers.

        Only returns fields actually consumed by TypeScript:
        - id: tool name (used as element id and handler method name)
        - tool_name: tool name (backup for label)
        - label: display label from app_action_label
        - group: menu group from app_action_group
        """
        trace_in()
        if user_tier_level < 1 or user_tier_level > 4:
            return trace_out([])

        app_actions = []
        # Iterate in reverse order to match file definition order
        for tool_name, tool_config in reversed(list(_global_tool_registry.items())):
            app_action_tiers = tool_config.get('app_action_tiers', [])
            # Check if this tool has app action access at the user's tier level
            if user_tier_level in app_action_tiers:
                app_actions.append({
                    'id': tool_name,
                    'tool_name': tool_name,
                    'label': tool_config.get('app_action_label', tool_name),
                    'group': tool_config.get('app_action_group', 'default')
                })

        log(f"Found {len(app_actions)} app actions for tier level {user_tier_level}")
        return trace_out(app_actions)

class APIWhitelist:
    """API Whitelist manager - dict of allowed tools with module info per tier."""

    _tier_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

    @classmethod
    def _get_cache_file(cls, tier: str) -> Path:
        """Get API whitelist cache file path for a tier."""
        return CACHE_DIR / f"api-whitelist-{tier}.json"

    @classmethod
    def _load_tier_whitelist(cls, tier: str, force_rebuild: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load API whitelist for a tier (from cache or rebuild via MCPWhitelist)."""
        trace_in()

        # Check if already loaded in memory
        if tier in cls._tier_cache and not force_rebuild:
            log(f"Using cached API whitelist for tier: {tier}")
            return trace_out(cls._tier_cache[tier])

        cache_file = cls._get_cache_file(tier)

        # Try to load from cache
        if cache_file.exists():
            cache_data = _read_cache_file_with_retry(cache_file)
            if cache_data is not None:
                whitelist = cache_data.get('whitelist', {})
                cls._tier_cache[tier] = whitelist
                log(f"Loaded {tier} API whitelist from cache: {len(whitelist)} tools")
                return trace_out(whitelist)

        # Cache miss - trigger rebuild via MCPWhitelist (which rebuilds all whitelists)
        log(f"API whitelist cache miss for {tier}, triggering rebuild via MCPWhitelist")
        MCPWhitelist._load_tier_whitelist(tier, force_rebuild=True)

        # Now try loading again
        if cache_file.exists():
            cache_data = _read_cache_file_with_retry(cache_file)
            if cache_data is not None:
                whitelist = cache_data.get('whitelist', {})
                cls._tier_cache[tier] = whitelist
                log(f"Loaded {tier} API whitelist after rebuild: {len(whitelist)} tools")
                return trace_out(whitelist)

        # Still nothing - return empty
        warn(f"Could not load API whitelist for tier {tier}")
        return trace_out({})

    @classmethod
    def tool_exists(cls, tier: str, tool_name: str) -> bool:
        """Check if tool is allowed for this tier."""
        trace_in()
        whitelist = cls._load_tier_whitelist(tier)
        exists = tool_name in whitelist
        if exists:
            log(f"Tool '{tool_name}' found in {tier} API whitelist")
        else:
            log(f"Tool '{tool_name}' not found in {tier} API whitelist")
        return trace_out(exists)

@register_cache_cleanup('tool_whitelist', cache_dir='hh/gateway/registry/cache')
def cleanup_tool_whitelist_cache():
    """Clean up MCP and API whitelist cache files (8 files total)."""
    trace_in()

    # Clear in-memory caches
    MCPWhitelist._tier_cache.clear()
    APIWhitelist._tier_cache.clear()
    log("Cleared tool whitelist in-memory caches")

    # Remove cold cache files (8 files: 4 MCP + 4 API)
    # Note: App-action whitelists are hot-cache only, no files to clean
    removed_files = []
    candidate_files = []

    # Add 8 whitelist files for local cache directory
    for tier in HENHOUSE_TIERS:
        candidate_files.append(CACHE_DIR / f"mcp-whitelist-{tier}.json")
        candidate_files.append(CACHE_DIR / f"api-whitelist-{tier}.json")
        # NOT app-action-whitelist - those don't exist anymore

    # Add 8 whitelist files for deployment cache directories
    for root in get_deployment_paths():
        for tier in HENHOUSE_TIERS:
            candidate_files.append(root / 'hh' / 'gateway' / 'registry' / 'cache' / f"mcp-whitelist-{tier}.json")
            candidate_files.append(root / 'hh' / 'gateway' / 'registry' / 'cache' / f"api-whitelist-{tier}.json")
            # NOT app-action-whitelist - those don't exist anymore

    for cache_file in candidate_files:
        if cache_file.exists():
            cache_file.unlink()
            removed_files.append(str(cache_file))
            log(f"Removed cache file: {cache_file}")
        else:
            debug(f"Cache file does not exist: {cache_file}")

    return trace_out({
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    })

