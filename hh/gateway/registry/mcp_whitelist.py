"""
MCP Whitelist System - Decorator-based lazy-loading whitelist generator.

Replaces monolithic mcp_whitelist.py with decorator-based registration.
Generates tier-specific whitelists (guest, verified, admin, root) on demand.
"""
from __future__ import annotations
import json
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup, get_deployment_paths
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

# Global registry of tool registrations (populated by decorators)
_global_tool_registry: Dict[str, Dict[str, Any]] = {}

def register_mcp_tool(
    tool_name: str,
    description: str,
    inputSchema: Dict[str, Any],
    tiers: List[int] = None,
    requires_approval: bool = False,
    crud_type: str = 'read',
    display_color: Optional[str] = None
) -> Callable:
    """
    Decorator to register an MCP tool.
    
    Args:
        tool_name: Name of the MCP tool
        description: Tool description
        inputSchema: JSON Schema for tool arguments
        tiers: List of tier levels (1=guest, 2=verified, 3=admin, 4=root). Default: all tiers [1,2,3,4]
        requires_approval: Whether tool requires approval queue (admin tier only)
        crud_type: Operation type ('create', 'read', 'update', 'delete', 'mixed')
        display_color: Optional color for approval interface
    """
    def decorator(func: Callable) -> Callable:
        if tiers is None:
            # Default to all tiers: levels 1, 2, 3, 4
            tier_levels = [1, 2, 3, 4]
        else:
            tier_levels = tiers
        
        # Convert tier levels to tier names (level 1 = index 0, level 2 = index 1, etc.)
        # Handle both MCP tools (1-4) and app actions (5-8)
        tool_tiers = []
        for level in tier_levels:
            if 1 <= level <= len(HENHOUSE_TIERS):
                # MCP tools: levels 1-4 map to tier names
                tier_index = level - 1  # Convert 1-based level to 0-based index
                tool_tiers.append(HENHOUSE_TIERS[tier_index])
            elif 5 <= level <= 8:
                # App actions: levels 5-8 map to same tier names as 1-4
                # (5→guest, 6→verified, 7→admin, 8→root)
                tier_index = (level - 5)  # Convert 5-8 to 0-3 index
                tool_tiers.append(HENHOUSE_TIERS[tier_index])
            else:
                warn(f"Invalid tier level {level} for tool {tool_name}, skipping")
        
        _global_tool_registry[tool_name] = {
            'description': description,
            'inputSchema': inputSchema,
            'tiers': tool_tiers,  # Tier names for whitelist compatibility
            'tier_levels': tier_levels,  # Original tier levels (1-4 for MCP, 5-8 for app actions)
            'requires_approval': requires_approval,
            'crud_type': crud_type,
            'display_color': display_color,
            'module': func.__module__,
            'function': func.__name__
        }
        log(f"Registered MCP tool: {tool_name} -> {func.__module__}.{func.__name__} (tiers: {tool_tiers})")
        return func
    return decorator

def _scan_for_mcp_tools() -> List[str]:
    """Scan codebase for register_mcp_tool decorators."""
    trace_in()
    found_files = []
    decorator_name = "register_mcp_tool"
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
        warn(f"Error scanning for MCP tools: {e}")
    trace_out()
    return found_files

def _import_modules(module_paths: List[str]) -> Dict[str, Dict[str, str]]:
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
    trace_out()
    return import_results

def _rebuild_all_tier_whitelists() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Rebuild whitelists for all tiers by scanning decorators. Returns dict mapping tier -> whitelist."""
    trace_in()
    log("Rebuilding MCP whitelists for all tiers")
    
    # Scan for decorators
    tool_files = _scan_for_mcp_tools()
    import_results = _import_modules(tool_files)
    
    # Build whitelists for each tier
    all_tier_whitelists: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for tier in HENHOUSE_TIERS:
        all_tier_whitelists[tier] = {}
    
    # Filter tools for each tier
    for tool_name, tool_config in _global_tool_registry.items():
        # Build MCP format entry (only description and inputSchema - no tier metadata)
        mcp_entry = {
            'description': tool_config['description'],
            'inputSchema': tool_config['inputSchema']
        }
        
        # Add to whitelists for each tier that has access
        for tier in tool_config.get('tiers', []):
            if tier in all_tier_whitelists:
                all_tier_whitelists[tier][tool_name] = mcp_entry
                log(f"Added tool '{tool_name}' to {tier} whitelist")
    
    trace_out()
    return all_tier_whitelists

class MCPWhitelist:
    """MCP Whitelist manager with lazy loading per tier."""
    
    _tier_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    @classmethod
    def _get_cache_file(cls, tier: str) -> Path:
        """Get cache file path for a tier."""
        return CACHE_DIR / f"mcp-whitelist-{tier}.json"
    
    @classmethod
    def _load_tier_whitelist(cls, tier: str, force_rebuild: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load whitelist for a tier (from cache or rebuild)."""
        trace_in()
        
        # Check if already loaded in memory
        if tier in cls._tier_cache and not force_rebuild:
            log(f"Using cached whitelist for tier: {tier}")
            trace_out()
            return cls._tier_cache[tier]
        
        cache_file = cls._get_cache_file(tier)
        
        # Try to load from cold cache
        if cache_file.exists() and not force_rebuild:
            try:
                with open(cache_file, 'r') as f:
                    whitelist = json.load(f)
                    cls._tier_cache[tier] = whitelist
                    log(f"Loaded {tier} whitelist from cache: {len(whitelist)} tools")
                    trace_out()
                    return whitelist
            except Exception as e:
                warn(f"Error reading {tier} whitelist cache: {e}")
        
        # Rebuild all tier whitelists at once (since we're doing all the work anyway)
        log(f"Rebuilding all tier whitelists (triggered by {tier} miss)...")
        all_tier_whitelists = _rebuild_all_tier_whitelists()
        
        # Save all tier whitelists to cold cache
        for rebuild_tier, rebuild_whitelist in all_tier_whitelists.items():
            tier_cache_file = cls._get_cache_file(rebuild_tier)
            try:
                with open(tier_cache_file, 'w') as f:
                    json.dump(rebuild_whitelist, f, indent=2)
                log(f"Cached {rebuild_tier} whitelist: {len(rebuild_whitelist)} tools")
            except Exception as e:
                warn(f"Error caching {rebuild_tier} whitelist: {e}")
        
        # Update in-memory cache for all tiers
        cls._tier_cache.update(all_tier_whitelists)
        
        whitelist = all_tier_whitelists.get(tier, {})
        trace_out()
        return whitelist
    
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
        trace_out()
        return tool
    
    @classmethod
    def list_tools(cls, tier: str) -> List[Dict[str, Any]]:
        """List all tools available for a tier (for tools/list)."""
        trace_in()
        whitelist = cls._load_tier_whitelist(tier)
        tools = []
        for tool_name, tool_config in whitelist.items():
            tools.append({
                'name': tool_name,
                'description': tool_config['description'],
                'inputSchema': tool_config['inputSchema']
            })
        log(f"Listed {len(tools)} tools for tier: {tier}")
        trace_out()
        return tools
    
    @classmethod
    def validate_tool(cls, tier: str, tool_name: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """Validate tool exists for tier and arguments match schema."""
        trace_in()
        tool = cls.get_tool(tier, tool_name)
        if not tool:
            trace_out()
            return False, f"Tool '{tool_name}' not available for tier '{tier}'"
        
        # Validate arguments against schema
        schema = tool['inputSchema']
        required = schema.get('required', [])
        for field in required:
            if field not in args:
                trace_out()
                return False, f"Missing required field: {field}"
        
        # Type checking
        properties = schema.get('properties', {})
        for key, value in args.items():
            if key not in properties:
                continue  # Allow extra fields
            prop_schema = properties[key]
            expected_type = prop_schema.get('type')
            if expected_type == 'string' and not isinstance(value, str):
                trace_out()
                return False, f"Field '{key}' must be a string"
            elif expected_type == 'integer' and not isinstance(value, int):
                trace_out()
                return False, f"Field '{key}' must be an integer"
            elif expected_type == 'boolean' and not isinstance(value, bool):
                trace_out()
                return False, f"Field '{key}' must be a boolean"
            elif expected_type == 'array' and not isinstance(value, list):
                trace_out()
                return False, f"Field '{key}' must be an array"
            elif expected_type == 'object' and not isinstance(value, dict):
                trace_out()
                return False, f"Field '{key}' must be an object"
        
        trace_out()
        return True, ""
    
    @classmethod
    def tool_exists(cls, tier: str, tool_name: str) -> bool:
        """Check if tool exists for tier."""
        tool = cls.get_tool(tier, tool_name)
        return tool is not None
    
    @classmethod
    def get_app_actions(cls, user_tier_level: int) -> List[Dict[str, Any]]:
        """Get app actions available for a user tier level (1-4). Returns actions with tier levels 5-8."""
        trace_in()
        if user_tier_level < 1 or user_tier_level > 4:
            trace_out()
            return []
        
        # App action tier level = user tier level + 4 (1→5, 2→6, 3→7, 4→8)
        app_action_tier_level = user_tier_level + 4
        
        app_actions = []
        for tool_name, tool_config in _global_tool_registry.items():
            tier_levels = tool_config.get('tier_levels', [])
            # Check if this tool has the app action tier level (5-8)
            if app_action_tier_level in tier_levels:
                # Check if any tier level is 5-8 (it's an app action)
                if any(5 <= level <= 8 for level in tier_levels):
                    app_actions.append({
                        'id': tool_name,
                        'tool_name': tool_name,
                        'description': tool_config['description'],
                        'label': tool_config.get('app_action_label', tool_name),
                        'group': tool_config.get('app_action_group', 'default'),
                        'icon': tool_config.get('app_action_icon'),
                        'requires_fields': tool_config.get('requires_fields', [])
                    })
        
        log(f"Found {len(app_actions)} app actions for tier level {user_tier_level} (app action tier {app_action_tier_level})")
        trace_out()
        return app_actions

@register_cache_cleanup('mcp_whitelist', cache_dir='hh/gateway/registry/cache')
def cleanup_mcp_whitelist_cache():
    """Clean up MCP whitelist cache files."""
    trace_in()
    
    # Clear in-memory cache
    MCPWhitelist._tier_cache.clear()
    log("Cleared MCP whitelist in-memory cache")
    
    # Remove cold cache files
    removed_files = []
    candidate_files = []
    for tier in HENHOUSE_TIERS:
        candidate_files.append(CACHE_DIR / f"mcp-whitelist-{tier}.json")
    
    for root in get_deployment_paths():
        for tier in HENHOUSE_TIERS:
            candidate_files.append(root / 'hh' / 'gateway' / 'registry' / 'cache' / f"mcp-whitelist-{tier}.json")
    
    for cache_file in candidate_files:
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

