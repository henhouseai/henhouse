from __future__ import annotations
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.registry import register_action, register_command, register_parser, register_http, backend_handlers, commands, BACKEND_TYPES
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from hh.render.config.config import safe_str
from hh.gateway.registry.render_command_list import CommandInfo, CommandListData, render_commands_section, render_section

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

@register_action("command_list")
@register_command("command_list")
def command_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    try:
        from hh.gateway.registry.cache import CACHE_DIR
        import json
        base_cache_file = CACHE_DIR / "base-reg.json"
        if not base_cache_file.exists():
            warn("Base cache file not found")
            report_error("action", "Base cache file not found")
            trace_out()
            return False
        with open(base_cache_file, 'r') as f:
            base_cache = json.load(f)
        available_commands_data = base_cache.get("commands", {})
        available_commands = list(available_commands_data.keys())
        log(f"Found {len(available_commands)} available commands in cache")
        has_load_failures = any(
            cmd_data.get("load_status") == "failed" 
            for cmd_data in available_commands_data.values()
        )
        data = {
            "type": "command_list",
            "count": len(available_commands),
            "commands": [],
            "has_load_failures": has_load_failures
        }
        command_infos = []
        for command_name in available_commands:
            command_data = available_commands_data.get(command_name, {})
            module_path = command_data.get("module", "")
            action_args = command_data.get("action_args", [])
            load_status = command_data.get("load_status", "success")
            load_error = command_data.get("load_error")
            from hh.gateway.registry.registry import commands
            is_loaded = command_name in commands and load_status == "success"
            command_info = {
                "name": command_name,
                "module_path": module_path,
                "action_args": action_args,
                "is_loaded": is_loaded
            }
            if has_load_failures:
                command_info["load_status"] = load_status
                if load_error:
                    command_info["load_error"] = load_error
            command_infos.append(command_info)

        def get_sort_key(cmd):
            if cmd["is_loaded"]:
                status_priority = 0
            elif cmd.get("load_status", "success") == "failed":
                status_priority = 2
            else:
                status_priority = 1
            module_path = cmd.get("module_path", "")
            module_parts = module_path.split('.')
            folder_path = '.'.join(module_parts[:-1]) if len(module_parts) > 1 else module_path
            module_file = module_parts[-1] if module_parts else ""
            return (status_priority, folder_path, module_file, cmd["name"])
        
        command_infos.sort(key=get_sort_key)
        data["commands"] = command_infos
        loaded_count = sum(1 for cmd in data['commands'] if cmd['is_loaded'])
        log(f"Successfully created command list with {len(data['commands'])} commands ({loaded_count} loaded, {len(available_commands) - loaded_count} available)")
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return True
    except Exception as e:
        warn("Command list failed.")
        report_error("action", f"Failed to list commands: {str(e)}")
        trace_out()
        return False

@register_action("backend_list")
@register_command("backend_list")
def backend_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    try:
        current_backend = gateway.backend
        backend_list = list(BACKEND_TYPES)
        log(f"Listing {len(backend_list)} registered backends")
        data = {
            "type": "backend_list",
            "count": len(backend_list),
            "backends": []
        }
        for backend_name in sorted(backend_list):
            is_loaded = backend_name == current_backend
            data["backends"].append({
                "name": backend_name,
                "module_path": f"hh.gateway.registry.{backend_name}",
                "is_loaded": is_loaded
            })
        log(f"Successfully created backend list with {len(data['backends'])} backends (current: {current_backend})")
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return True
    except Exception as e:
        warn("Backend list failed.")
        report_error("action", f"Failed to list backends: {str(e)}")
        trace_out()
        return False

for backend_type in BACKEND_TYPES:
    dict_name = f"{backend_type}s"
    list_name = f"{backend_type}_list"
    exec(f"""
@register_action("{list_name}")
@register_command("{list_name}")
def {list_name}() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    try:
        from hh.gateway.registry.cache import CACHE_DIR
        import json
        backend_cache_file = CACHE_DIR / "{backend_type}-reg.json"
        if not backend_cache_file.exists():
            warn(f"{backend_type.title()} cache file not found")
            report_error("action", f"{backend_type.title()} cache file not found")
            trace_out()
            return False
        with open(backend_cache_file, 'r') as f:
            backend_cache = json.load(f)
        debug(f"{backend_type.title()} cache keys: {{list(backend_cache.keys())}}")
        available_{backend_type}s_data = backend_cache.get("handlers", {{}})
        debug(f"Available {backend_type}s data: {{available_{backend_type}s_data}}")
        available_{backend_type}s = list(available_{backend_type}s_data.keys())
        log(f"Found {{len(available_{backend_type}s)}} available {backend_type}s in cache")
        backend_dict = backend_handlers["{backend_type}"]
        loaded_{backend_type}s = {{}}
        for handler_name, handler_info in backend_dict.items():
            loaded_{backend_type}s[handler_name] = {{
                "module": handler_info.function.__module__ if handler_info and handler_info.function else None
            }}
        log(f"Found {{len(loaded_{backend_type}s)}} loaded {backend_type}s in registry")
        data = {{
            "type": "{list_name}",
            "count": len(available_{backend_type}s),
            "{backend_type}s": []
        }}
        handler_infos = []
        for handler_name in available_{backend_type}s:
            is_loaded = handler_name in loaded_{backend_type}s
            if is_loaded:
                loaded_info = loaded_{backend_type}s.get(handler_name, {{}})
                module_path = loaded_info.get("module")
            else:
                handler_data = available_{backend_type}s_data.get(handler_name, {{}})
                module_path = handler_data.get("module", "Unknown")
            handler_info = {{
                "name": handler_name,
                "module_path": module_path,
                "is_loaded": is_loaded
            }}
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
            data["{backend_type}s"].append(handler_info)
        log(f"Successfully created {backend_type} list with {{len(data['{backend_type}s'])}} entries ({{len(loaded_{backend_type}s)}} loaded, {{len(available_{backend_type}s) - len(loaded_{backend_type}s)}} available)")
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return True
    except Exception as e:
        warn(f"{backend_type.title()} list failed.")
        report_error("action", f"Failed to list {backend_type}s: {{str(e)}}")
        trace_out()
        return False
""")

for backend_type in BACKEND_TYPES:
    list_name = f"{backend_type}_list"
    parser_name = f"parse_{backend_type}_list"
    exec(f"""
@register_http('{list_name}')
@register_parser('{list_name}')
def {parser_name}() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    json_data = gateway.response.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_{backend_type}_list_header'))
        source_data = get_data(json_data)
        sections = source_data.get("{backend_type}s", [])
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
        if not render_section(source_data, lines):
            warn("Failed to render {backend_type}s section")
            report_error("backend", "Failed to render {backend_type}s section")
            trace_out()
            return False
        break_section(lines)
        result = finalize_output(lines)
        if len(result) == 0:
            warn("{backend_type.title()} response is empty")
        gateway.response.add_output(result)
        log(f"Parser execution completed successfully with {{len(result)}} lines.")
        trace_out()
        return True
    except Exception as e:
        warn("Parser execution raised an exception.")
        report_error("backend", f"Parser execution raised an exception: {{e}}")
        trace_out()
        return False
""")
