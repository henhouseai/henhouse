from __future__ import annotations
from typing import List, Dict
from hh.gateway.debug.debug_safe import Debug, DebugEntry, DOCUMENT_ROOT, trim_document_root
from hh.render.text.color import COLORS, COLOR_NAMES, RESET_COLOR, apply_color_to_multiline, get_color
from hh.render.render import FieldConfig, TableData

def debug_print(message: str) -> None:
    """Debug print function that can be easily enabled/disabled"""
    # Uncomment the next line to enable debug prints
    # print(f"DEBUG: {message}")
    pass


class DebugTable(Debug):
    def render_table_hook(self) -> str:
        debug_print(f"debug_debug.render_table_hook() - starting")
        self.process_extra_data()
        table_entries = []
        for entry in self.filtered_data:
            table_entries.append(entry)
        debug_print(f"debug_debug.render_table_hook() - table_entries count: {len(table_entries)}")
        if not table_entries:
            debug_print(f"debug_debug.render_table_hook() - no table entries, returning empty")
            return ""
        from hh.gateway.registry.debug import safe_mode, get_safe_debug_output
        safe_debug_output = ""
        with safe_mode():
            debug_print(f"debug_debug.render_table_hook() - inside safe_mode context")
            from hh.gateway.registry.debug import get_shared_debug_store
            shared_data = get_shared_debug_store().captured_data
            debug_print(f"debug_debug.render_table_hook() - shared_data length at start of safe_mode: {len(shared_data)}")
            table_output = self._render_table_from_entries(table_entries)
            extra_output = self.render_extra_data()
            debug_print(f"debug_debug.render_table_hook() - after table rendering, table_output length: {len(table_output) if table_output else 0}")
            shared_data_after = get_shared_debug_store().captured_data
            debug_print(f"debug_debug.render_table_hook() - shared_data length after table rendering: {len(shared_data_after)}")
            safe_debug_output = get_safe_debug_output()
        debug_print(f"debug_debug.render_table_hook() - safe_debug_output length: {len(safe_debug_output) if safe_debug_output else 0}")
        output = table_output
        if extra_output:
            output += "\n\n" + extra_output
        try:
            from hh.gateway.gateway import get_gateway
            gateway = get_gateway()
            if gateway and gateway.get_arg("deep-debug") and safe_debug_output.strip():
                output += "\n--- Safe Debug Output ---\n\n" + safe_debug_output + "\n"
        except Exception:
            if safe_debug_output.strip():
                output += "\n--- Safe Debug Output ---\n\n" + safe_debug_output + "\n"
        self.filtered_data.clear()
        return output

    def _render_table_from_entries(self, entries: List[DebugEntry]) -> str:
        if not entries:
            return ""
        from hh.render.render import render_block
        table_data = TableData()
        table_data.add_row(
            'debug_header',
            label='label',
            folder='folder',
            file='file',
            function='function',
            message='message'
        )
        for entry in entries:
            module_color_index = self.get_module_color(entry.folder)
            filename_color_index = self.get_filename_color(entry.folder, entry.filename)
            function_color_index = self.get_function_color(entry.folder, entry.filename, entry.function_name)
            module_color = COLORS[COLOR_NAMES[module_color_index]]
            filename_color = COLORS[COLOR_NAMES[filename_color_index]]
            function_color = COLORS[COLOR_NAMES[function_color_index]]
            display_module = trim_document_root(entry.folder)
            display_filename = trim_document_root(entry.filename)
            colored_module = f"{module_color}{display_module}{RESET_COLOR}"
            colored_filename = f"{filename_color}{display_filename}{RESET_COLOR}"
            colored_function = f"{function_color}{entry.function_name}{RESET_COLOR}"
            if entry.level == 1:
                field_type = 'trace_in'
            elif entry.level == 2:
                field_type = 'trace_out'
            elif entry.level == 3:
                field_type = 'log'
            elif entry.level == 4:
                field_type = 'debug'
            else:
                field_type = 'warn'
            message_color = ""
            field_config = FieldConfig()
            field_config.add_header('debug_header')
            field_config.add_simple(['trace_in', 'trace_out', 'log'])
            field_config.add_simple_color('debug', 'yellow')
            field_config.add_simple_color('warn', 'orange')
            for config in field_config.get_configs():
                if config['field_type'] == field_type and 'color_key' in config:
                    color_key = config['color_key']
                    message_color = get_color(color_key)
                    if message_color:
                        break
            colored_message = entry.message
            if message_color:
                colored_message = apply_color_to_multiline(entry.message, message_color)
            table_data.add_row(
                field_type,
                folder=colored_module,
                file=colored_filename,
                function=colored_function,
                message=colored_message
            )
        overrides: Dict[str, object] = {
            'margin_l': 2,
            'margin_r': 2,
            'margin_t': 1,
            'margin_b': 1,
            'padl': 2,
            'padr': 2,
            'rule_header': 1,
            'column_widths': {'message': 120},
            'column_overflow': {'message': 'wrap'},
            'column_align': {'file': 'center', 'function': 'right'},
        }
        return render_block(
            table_data,
            FieldConfig()
                .add_header('debug_header')
                .add_simple(['trace_in', 'trace_out', 'log'])
                .add_simple_color('debug', 'yellow')
                .add_simple_color('warn', 'orange'),
            table_class='standard',
            table_overrides=overrides,
            block_type='debug',
        )

_debug = DebugTable()

def get_debug() -> DebugTable:
    return _debug