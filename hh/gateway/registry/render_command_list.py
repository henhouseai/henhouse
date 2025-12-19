from __future__ import annotations
from typing import List, TypedDict, Dict, Any
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from hh.render.config.config import safe_str
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.text.color import ColorManager

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

class CommandInfo(TypedDict, total=False):
    name: str
    module_path: str
    action_args: List[str]
    is_loaded: bool

class CommandListData(TypedDict, total=False):
    type: str
    count: int
    commands: List[CommandInfo]

_color_manager = ColorManager()

def _get_colored_module(module: str, is_loaded: bool) -> str:
    """Get module with rainbow color applied only if loaded."""
    return _color_manager.get_colored(module, module, is_loaded, pool='modules')

def _get_colored_name(name: str, is_loaded: bool) -> str:
    """Get name with rainbow color applied only if loaded."""
    return _color_manager.get_colored(name, name, is_loaded, pool='names')


def render_commands_section(source_data: CommandListData, lines: List[str]) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_commands_section")
        trace_out()
        return False
    block = 'rows'
    if not gateway.is_no(block): 
        commands = source_data.get('commands', [])
        count = len(commands)
        has_load_failures = source_data.get('has_load_failures', False)
        log(f"Rendering {count} commands (has_load_failures={has_load_failures})")
        if not commands:
            log("No commands to render")
            trace_out()
            return True
        table_data = TableData()
        if has_load_failures:
            table_data.add_row(
                'loaded', 
                label=f'{count} command{"s" if count != 1 else ""}',
                name='name',
                module='module',
                action_args='action_args',
                load_status='status'
            )
        else:
            table_data.add_row(
                'loaded',
                label=f'{count} command{"s" if count != 1 else ""}',
                name='name',
                module='module',
                action_args='action_args'
            )
        log(f"Added header row: {count} commands ({'4-column' if has_load_failures else '3-column'} format)")
        for command in commands:
            action_args = command.get('action_args', [])
            action_args_str = ', '.join(map(str, action_args)) if action_args else ''
            is_loaded = command.get('is_loaded', False)
            load_status = command.get('load_status', 'success')
            if is_loaded:
                field_type = 'loaded'
            elif load_status == 'failed':
                field_type = 'failed'
            else:
                field_type = 'found'
            if has_load_failures:
                load_error = command.get('load_error', '')
                load_error_str = str(load_error) if load_error is not None else ''
                if load_status == 'failed':
                    load_status_text = load_error_str[:50] + ('...' if len(load_error_str) > 50 else '')
                else:
                    load_status_text = ''
                table_data.add_row(
                    field_type,
                    name=_get_colored_name(command.get('name', 'Unknown'), is_loaded),
                    module=_get_colored_module(command.get('module_path', ''), is_loaded),
                    action_args=safe_str(action_args_str),
                    load_status=load_status_text
                )
            else:
                table_data.add_row(
                    field_type,
                    name=_get_colored_name(command.get('name', 'Unknown'), is_loaded),
                    module=_get_colored_module(command.get('module_path', ''), is_loaded),
                    action_args=safe_str(action_args_str)
                )
            log(f"Added {field_type} row: {command.get('name', 'Unknown')} -> {action_args_str}")
        separator_rows_raw = source_data.get('separator_after_rows', [])
        separator_rows = separator_rows_raw if isinstance(separator_rows_raw, list) else []
        table_overrides: Dict[str, Any] = {'margin_l': 4}
        if separator_rows:
            table_overrides['separator_after_rows'] = separator_rows
        rendered_block = render_block(
            table_data, 
            FieldConfig()
                .add_header('header')
                .add_simple(['count', 'found', 'action_args', 'function_name'])
                .add_simple_color('loaded', 'green')
                .add_simple_color('failed', 'red'),
            table_overrides=table_overrides, 
            block_type=block
        )
        lines.append(rendered_block)
        log(f"Rendered command table with {table_data.num_rows()} rows")
    else:
        log("Rows block disabled, skipping command rendering")
    trace_out()
    return True

def render_section(source_data: CommandListData, lines: List[str]) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_section")
        trace_out()
        return False
    block = 'rows'
    if not gateway.is_no(block): 
        from hh.gateway.registry.backend import BACKEND_TYPES
        sections: List[Any] = []
        if 'backends' in source_data:
            backend_data = source_data.get('backends')
            if isinstance(backend_data, list):
                sections = backend_data
        else:
            for backend_type in BACKEND_TYPES:
                key = f"{backend_type}s"
                if key in source_data:
                    backend_data = source_data.get(key)
                    if isinstance(backend_data, list):
                        sections = backend_data
                    break
        count = len(sections)
        log(f"Rendering {count} sections")
        if not sections:
            log("No sections to render")
            trace_out()
            return True
        table_data = TableData()
        table_data.add_row(
            'loaded',
            label=f'{count} command{"s" if count != 1 else ""}',
            name='name',
            module='module'
        )
        log(f"Added header row: {count} commands (3-column format)")
        for section in sections:
            action_args = section.get('action_args', [])
            action_args_str = ', '.join(map(str, action_args)) if action_args else ''
            is_loaded = section.get('is_loaded', False)
            field_type = 'loaded' if is_loaded else 'found'
            table_data.add_row(
                field_type,
                name=_get_colored_name(section.get('name', 'Unknown'), is_loaded),
                module=_get_colored_module(section.get('module_path', ''), is_loaded)
            )
            log(f"Added {field_type} row: {section.get('name', 'Unknown')} -> {action_args_str}")
        separator_rows_raw = source_data.get('separator_after_rows', [])
        separator_rows = separator_rows_raw if isinstance(separator_rows_raw, list) else []
        table_overrides: Dict[str, Any] = {'margin_l': 4}
        if separator_rows:
            table_overrides['separator_after_rows'] = separator_rows
        rendered_block = render_block(
            table_data, 
            FieldConfig()
                .add_header('header')
                .add_simple(['count', 'found', 'action_args', 'function_name'])
                .add_simple_color('loaded', 'green')
                .add_simple_color('failed', 'red'),
            table_overrides=table_overrides, 
            block_type=block
        )
        lines.append(rendered_block)
        log(f"Rendered command table with {table_data.num_rows()} rows")
    else:
        log("Rows block disabled, skipping command rendering")
    trace_out()
    return True

@register_parser('command_list')
def command_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway or response available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
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
            report_error("backend","Failed to render commands section")
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
        report_error("backend",f"Parser execution raised an exception: {e}")
        trace_out()
        return False

@register_parser('backend_list')
def parse_backend_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway or response available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False
    json_data = gateway.response.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_backend_list_header'))
        source_data = get_data(json_data) if json_data is not None else {}
        # Type cast to CommandListData for type checker
        command_list_data: CommandListData = source_data  # type: ignore[assignment]
        if not render_section(command_list_data, lines):
            warn("Failed to render backends section")
            report_error("backend","Failed to render backends section")
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
        report_error("backend",f"Parser execution raised an exception: {e}")
        trace_out()
        return False