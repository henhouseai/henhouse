"""Maintenance List - Lists all registered maintenance handlers"""
from __future__ import annotations
from typing import Any, Dict, List
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.registry import register_command, register_action, register_parser, backend_handlers
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.render import render_header_block, finalize_output
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.utils import render_section, CommandListData

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

@register_action("maintenance_list")
@register_command("maintenance_list")
def maintenance_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        return trace_out(False)
    try:
        from hh.gateway.registry.cache import CACHE_DIR
        import json
        backend_cache_file = CACHE_DIR / "maintenance-reg.json"
        if not backend_cache_file.exists():
            warn("Maintenance cache file not found")
            report_error("action", "Maintenance cache file not found")
            return trace_out(False)
        with open(backend_cache_file, 'r') as f:
            backend_cache = json.load(f)
        debug(f"Maintenance cache keys: {list(backend_cache.keys())}")
        available_maintenances_data = backend_cache.get("handlers", {})
        debug(f"Available maintenances data: {available_maintenances_data}")
        available_maintenances = list(available_maintenances_data.keys())
        log(f"Found {len(available_maintenances)} available maintenances in cache")
        backend_dict = backend_handlers["maintenance"]
        loaded_maintenances = {}
        for handler_name, handler_info in backend_dict.items():
            # Prefer original_module for display if available
            original_module = getattr(handler_info, 'original_module', None) if handler_info else None
            module = handler_info.function.__module__ if handler_info and handler_info.function else None
            loaded_maintenances[handler_name] = {
                "module": module,
                "original_module": original_module
            }
        log(f"Found {len(loaded_maintenances)} loaded maintenances in registry")
        data: Dict[str, Any] = {
            "type": "maintenance_list",
            "count": len(available_maintenances),
            "maintenances": []
        }
        maintenances_list: List[Dict[str, Any]] = data["maintenances"]  # type: ignore[assignment]
        handler_infos = []
        for handler_name in available_maintenances:
            is_loaded = handler_name in loaded_maintenances
            if is_loaded:
                loaded_info = loaded_maintenances.get(handler_name, {})
                # Prefer original_module for display if available
                module_path = loaded_info.get("original_module") or loaded_info.get("module")
            else:
                handler_data = available_maintenances_data.get(handler_name, {})
                # Prefer original_module for display if available
                module_path = handler_data.get("original_module") or handler_data.get("module", "Unknown")
            handler_info = {
                "name": handler_name,
                "module_path": module_path,
                "is_loaded": is_loaded
            }
            handler_infos.append(handler_info)
        def get_sort_key(handler):
            status_priority = 0 if handler["is_loaded"] else 1
            module_path = handler.get("module_path", "")
            module_parts = module_path.split('.')
            folder_path = '.'.join(module_parts[:-1]) if len(module_parts) > 1 else module_path
            module_file = module_parts[-1] if module_parts else ""
            return (status_priority, folder_path, module_file, handler["name"])
        handler_infos.sort(key=get_sort_key)
        for handler_info in handler_infos:
            maintenances_list.append(handler_info)
        log(f"Successfully created maintenance list with {len(maintenances_list)} entries ({len(loaded_maintenances)} loaded, {len(available_maintenances) - len(loaded_maintenances)} available)")
        gateway.response.set_action_response(success_payload(data))
        return trace_out(True)
    except Exception as e:
        warn("Maintenance list failed.")
        report_error("action", f"Failed to list maintenances: {str(e)}")
        return trace_out(False)

@register_parser('maintenance_list')
def parse_maintenance_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        return trace_out(False)
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        return trace_out(False)
    json_data = gateway.response.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_maintenance_list_header'))
        source_data = get_data(json_data) if json_data is not None else {}
        sections = source_data.get("maintenances", [])
        separator_rows = []
        current_folder = None
        for row_idx, section in enumerate(sections):
            module_path = section.get("module_path", "")
            module_parts = module_path.split('.')
            folder_path = '.'.join(module_parts[:-1]) if len(module_parts) > 1 else module_path
            if current_folder is not None and folder_path != current_folder:
                separator_rows.append(row_idx)
            current_folder = folder_path
        source_data["separator_after_rows"] = separator_rows
        command_list_data: CommandListData = source_data  # type: ignore[assignment]
        if not render_section(command_list_data, lines):
            warn("Failed to render maintenances section")
            report_error("backend", "Failed to render maintenances section")
            return trace_out(False)
        break_section(lines)
        result = finalize_output(lines)
        if len(result) == 0:
            warn("Maintenance response is empty")
        gateway.response.add_output(result)
        log(f"Parser execution completed successfully with {len(result)} lines.")
        return trace_out(True)
    except Exception as e:
        warn("Parser execution raised an exception.")
        report_error("backend", f"Parser execution raised an exception: {e}")
        return trace_out(False)
