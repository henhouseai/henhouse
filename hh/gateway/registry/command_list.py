"""Command List - Lists all registered commands"""
from __future__ import annotations
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.registry import register_command, register_action, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.render import render_header_block, finalize_output
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.utils import CommandListData, render_commands_section

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

@register_action("command_list")
@register_command("command_list")
def command_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        return trace_out(False)
    try:
        from hh.gateway.registry.cache import CACHE_DIR
        import json
        base_cache_file = CACHE_DIR / "base-reg.json"
        if not base_cache_file.exists():
            warn("Base cache file not found")
            report_error("action", "Base cache file not found")
            return trace_out(False)
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
        commands_list = data.get('commands', [])
        assert isinstance(commands_list, list), "commands should be a list"
        loaded_count = sum(1 for cmd in commands_list if isinstance(cmd, dict) and cmd.get('is_loaded'))
        commands_count = len(commands_list)
        log(f"Successfully created command list with {commands_count} commands ({loaded_count} loaded, {len(available_commands) - loaded_count} available)")
        gateway.response.set_action_response(success_payload(data))
        return trace_out(True)
    except Exception as e:
        warn("Command list failed.")
        report_error("action", f"Failed to list commands: {str(e)}")
        return trace_out(False)

@register_parser('command_list')
def parse_command_list() -> bool:
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
    json_data = gateway.response.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_command_list_header'))
        source_data = get_data(json_data) if json_data is not None else {}
        commands_raw = source_data.get('commands', [])
        commands = commands_raw if isinstance(commands_raw, list) else []
        separator_rows = []
        current_folder = None
        for row_idx, command in enumerate(commands):
            if not isinstance(command, dict):
                continue
            module_path_raw = command.get("module_path", "")
            module_path = str(module_path_raw) if module_path_raw is not None else ""
            module_parts = module_path.split('.')
            folder_path = '.'.join(module_parts[:-1]) if len(module_parts) > 1 else module_path
            if current_folder is not None and folder_path != current_folder:
                separator_rows.append(row_idx)
            current_folder = folder_path
        source_data["separator_after_rows"] = separator_rows
        # Type cast to CommandListData for type checker
        command_list_data: CommandListData = source_data  # type: ignore[assignment]
        if not render_commands_section(command_list_data, lines):
            warn("Failed to render commands section")
            report_error("backend", "Failed to render commands section")
            trace_out()
            return False
        break_section(lines)
        result = finalize_output(lines)
        if len(result) == 0:
            warn("Backend response is empty")
        gateway.response.add_output(result)
        log(f"Parser execution completed successfully with {len(result)} lines.")
        trace_out()
        return True
    except Exception as e:
        warn("Parser execution raised an exception.")
        report_error("backend", f"Parser execution raised an exception: {e}")
        trace_out()
        return False
