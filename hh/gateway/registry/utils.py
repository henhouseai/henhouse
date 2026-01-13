"""
Registry Utilities - Helper functions for list rendering

This module provides shared rendering utilities for command/backend list operations.
All helper functions, TypedDicts, and rendering logic are centralized here.
"""
from __future__ import annotations
from typing import List, TypedDict, Dict, Any
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.render.render import render_block, FieldConfig, TableData
from hh.render.config.config import safe_str
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.text.color import ColorManager

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

# TypedDicts for type hints
class CommandInfo(TypedDict, total=False):
    name: str
    module_path: str
    action_args: List[str]
    is_loaded: bool

class CommandListData(TypedDict, total=False):
    type: str
    count: int
    commands: List[CommandInfo]

# Color manager for rainbow coloring
_color_manager = ColorManager()

def get_colored_module(module: str, is_loaded: bool) -> str:
    """Get module with rainbow color applied only if loaded."""
    return _color_manager.get_colored(module, module, is_loaded, pool='modules')

def get_colored_name(name: str, is_loaded: bool) -> str:
    """Get name with rainbow color applied only if loaded."""
    return _color_manager.get_colored(name, name, is_loaded, pool='names')

def render_commands_section(source_data: CommandListData, lines: List[str]) -> bool:
    """Render commands section with action_args column (used by command_list)."""
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
                    name=get_colored_name(command.get('name', 'Unknown'), is_loaded),
                    module=get_colored_module(command.get('module_path', ''), is_loaded),
                    action_args=safe_str(action_args_str),
                    load_status=load_status_text
                )
            else:
                table_data.add_row(
                    field_type,
                    name=get_colored_name(command.get('name', 'Unknown'), is_loaded),
                    module=get_colored_module(command.get('module_path', ''), is_loaded),
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
    """Render generic section without action_args column (used by backend/handler lists)."""
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
                name=get_colored_name(section.get('name', 'Unknown'), is_loaded),
                module=get_colored_module(section.get('module_path', ''), is_loaded)
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
