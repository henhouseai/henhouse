"""
Auto-generated Maintenance Wrapper Functions
This module dynamically generates boilerplate wrapper functions with @register_maintenance decorators
based on discovered maintenance tools from the backend cache.

The exec block contains @register_maintenance decorators that will be discovered by the registry system
when this module is imported.
"""
from __future__ import annotations
from pathlib import Path
import json
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.registry import register_maintenance
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

# Boilerplate wrapper function template
def _maintenance_wrapper_template(tool_name: str) -> bool:
    """Boilerplate maintenance wrapper - extracts data from MCP wrapper and flattens it."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway or response available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    # Extract flat data from MCP-wrapped action_response
    action_response = gateway.response.get_action_response()
    if action_response is not None and isinstance(action_response, dict) and "content" in action_response and action_response["content"]:
        content_item = action_response["content"][0]
        if content_item.get("type") == "text" and "text" in content_item:
            flat_data = content_item["text"]
            # Replace the MCP-wrapped response with flat data
            gateway.response.set_action_response(flat_data)
            log(f"Maintenance backend {tool_name} extracted flat data from MCP wrapper")
        else:
            log(f"Maintenance backend {tool_name} - unexpected content structure, using as-is")
    else:
        log(f"Maintenance backend {tool_name} - no content wrapper found, using as-is")
    
    trace_out()
    return True

# Dynamically generate wrapper functions with @register_maintenance decorators using exec
# This exec block will be discovered by the registry system when this module is imported
# Scan for register_maintenance_tool() calls to discover tools (same pattern as MCP scans for decorators)
_wrapper_code = ""
all_tools = set()

def _scan_for_maintenance_tools() -> set:
    """Scan hh/ and ext/ folders for register_maintenance_tool() calls."""
    trace_in()
    found_tools = set()
    try:
        import hh
        hh_path = Path(hh.__file__).parent
        project_root = hh_path.parent
        
        # Build list of paths to scan
        scan_paths: list[tuple[Path, Path]] = [(hh_path, hh_path)]
        
        # Check if ext/ exists and add it to scan paths
        ext_path = project_root / "ext"
        if ext_path.exists() and ext_path.is_dir():
            scan_paths.append((ext_path, hh_path))  # Use hh_path for relative path calculation
            log(f"Found ext/ folder, will scan for maintenance tools")
        
        # Scan each path
        for scan_path, base_path in scan_paths:
            for py_file in scan_path.rglob("*.py"):
                if py_file.name.startswith("cache_"):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for register_maintenance_tool("tool_name") calls
                        import re
                        matches = re.findall(r'register_maintenance_tool\(["\']([^"\']+)["\']\)', content)
                        for tool_name in matches:
                            found_tools.add(tool_name)
                            log(f"Found maintenance tool: {tool_name} in {py_file.relative_to(base_path)}")
                except Exception as e:
                    warn(f"Error reading {py_file}: {e}")
    except Exception as e:
        warn(f"Error scanning for maintenance tools: {e}")
    trace_out()
    return found_tools

# Scan for tools
all_tools = _scan_for_maintenance_tools()

for tool_name in all_tools:
    # Convert tool_name to valid Python function name (replace hyphens with underscores)
    func_name = tool_name.replace('-', '_')
    _wrapper_code += f"""
@register_maintenance('{tool_name}')
def {func_name}() -> bool:
    \"\"\"Maintenance wrapper for {tool_name}.\"\"\"
    return _maintenance_wrapper_template('{tool_name}')
"""

if _wrapper_code:
    exec(_wrapper_code)
    log(f"Generated {len(all_tools)} maintenance wrapper functions")


# Keep register_maintenance_tool for backwards compatibility - it just triggers cache discovery
_registered_tools: set = set()

def register_maintenance_tool(tool_name: str) -> None:
    """Register a maintenance tool - triggers cache discovery, wrappers generated via exec()."""
    # This function is called by action files to register tools
    # The actual wrapper generation happens via exec() above using cache data
    # This just ensures the tool is tracked for cache purposes
    if tool_name not in _registered_tools:
        _registered_tools.add(tool_name)
        log(f"Registered maintenance tool: {tool_name} (wrapper will be generated from cache)")

