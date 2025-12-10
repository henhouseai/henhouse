from __future__ import annotations
import inspect
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from hh.gateway.debug.debug_filters import FilterMixin, parse_list_arg
from hh.render.text.color import COLORS, COLOR_NAMES, RESET_COLOR, get_color, apply_color_code

def debug_print(message: str) -> None:
    """Debug print function that can be easily enabled/disabled"""
    # Uncomment the next line to enable debug prints
    # print(f"DEBUG: {message}")
    pass

def detect_document_root():
    current_file = Path(__file__).resolve()
    for parent in [current_file.parent] + list(current_file.parents):
        if (parent / 'hh' / '__init__.py').exists():
            return str(parent)
    return str(current_file.parent.parent)

def trim_document_root(path: str) -> str:
    if not DOCUMENT_ROOT:
        return path
    if path.startswith(DOCUMENT_ROOT):
        return path[len(DOCUMENT_ROOT):]
    return path

DOCUMENT_ROOT = detect_document_root()

class DebugEntry:
    def __init__(self, index, timestamp, level, message, function_name, filename, folder):
        self.index = index
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.function_name = function_name
        self.filename = filename
        self.folder = folder
        self.white_passed = False
        self.gray_passed = False
        self.black_passed = False
        self.limit_passed = False
        self.folder_count = 0
        self.file_count = 0
        self.function_count = 0

class Debug(FilterMixin):
    def __init__(self):
        super().__init__()
        self._shared_store = None
        self._module_colors: dict = {}
        self._filename_colors: dict = {}
        self._function_colors: dict = {}
        self._module_color_index: int = 0
        self.filtered_data: List[DebugEntry] = []
        self._next_index: int = 0

    def _get_shared_store(self):
        if self._shared_store is None:
            from hh.gateway.registry.debug import get_shared_debug_store
            self._shared_store = get_shared_debug_store()
        return self._shared_store

    def _process_debug_limit(self, debug_limit: str) -> None:
        limit = self._process_int_arg(debug_limit)
        if limit is not None:
            self.set_summary_limit(limit)
    
    def _process_int_arg(self, int_arg: str) -> Optional[int]:
        if not int_arg:
            return None
        try:
            return int(int_arg)
        except (ValueError, TypeError):
            return None
    
    def _process_debug_whitelist(self, white_list: str) -> None:
        parsed_list = parse_list_arg(white_list)
        if parsed_list:
            self.set_whitelist(parsed_list)
    
    def _process_debug_graylist(self, gray_list: str) -> None:
        parsed_list = parse_list_arg(gray_list)
        if parsed_list:
            self.set_graylist(parsed_list)
    
    def _process_debug_blacklist(self, black_list: str) -> None:
        parsed_list = parse_list_arg(black_list)
        if parsed_list:
            self.set_blacklist(parsed_list)
    
    def get_arg_overrides(self) -> None:
        try:
            shared_store = self._get_shared_store()
            self.whitelist = shared_store.whitelist
            self.graylist = shared_store.graylist
            self.blacklist = shared_store.blacklist
            self.summary_limit = shared_store.summary_limit
        except Exception:
            pass
    
    def get_module_color(self, module: str) -> int:
        if module not in self._module_colors:
            self._module_colors[module] = self._module_color_index
            self._module_color_index = (self._module_color_index + 1) % len(COLOR_NAMES)
        return self._module_colors[module]
    
    def get_filename_color(self, module: str, filename: str) -> int:
        key = (module, filename)
        if key not in self._filename_colors:
            module_color = self.get_module_color(module)
            module_filenames = [k[1] for k in self._filename_colors.keys() if k[0] == module]
            color_index = (module_color + len(module_filenames)) % len(COLOR_NAMES)
            self._filename_colors[key] = color_index
        return self._filename_colors[key]
    
    def get_function_color(self, module: str, filename: str, function: str) -> int:
        key = (module, filename, function)
        if key not in self._function_colors:
            filename_color = self.get_filename_color(module, filename)
            filename_functions = [k[2] for k in self._function_colors.keys() if k[0] == module and k[1] == filename]
            color_index = (filename_color + len(filename_functions)) % len(COLOR_NAMES)
            self._function_colors[key] = color_index
        return self._function_colors[key]
    
    def render_table_hook(self) -> str:
        return ""

    def process_extra_data(self) -> None:
        pass

    def render_extra_data(self) -> str:
        return ""

    def render(self) -> str:
        debug_print(f"debug_safe.render() - starting render")
        self.get_arg_overrides()
        self.filtered_data = []
        folder_counts = {}
        file_counts = {}
        function_counts = {}
        shared_data = self._get_shared_store().captured_data
        trace_enabled = False
        try:
            from hh.gateway.gateway import get_gateway
            gateway = get_gateway()
            if gateway and gateway.request and gateway.request.get_arg('trace'):
                trace_enabled = True
        except Exception:
            pass
        debug_print(f"debug_safe.render() - shared_data length: {len(shared_data)}")
        
        for entry in shared_data:
            filtered_entry = DebugEntry(
                entry.index,
                entry.timestamp,
                entry.level,
                entry.message,
                entry.function_name,
                entry.filename,
                entry.folder
            )
            filtered_entry.white_passed = self.is_whitelisted(entry.folder)
            filtered_entry.gray_passed = self.is_graylisted(entry.filename)
            filtered_entry.black_passed = not self.is_blacklisted(entry.function_name)
            will_be_shown = (filtered_entry.white_passed and filtered_entry.gray_passed and filtered_entry.black_passed)
            file_combination = f"{entry.folder} - {entry.filename}"
            function_combination = f"{entry.folder} - {entry.filename} - {entry.function_name}"
            if entry.level >= (1 if trace_enabled else 3):
                filtered_entry.limit_passed = self.should_show_message(function_combination, will_be_shown)
            else:
                filtered_entry.limit_passed = False
            folder_counts[entry.folder] = folder_counts.get(entry.folder, 0) + 1
            file_counts[file_combination] = file_counts.get(file_combination, 0) + 1
            function_counts[function_combination] = function_counts.get(function_combination, 0) + 1
            filtered_entry.folder_count = folder_counts.get(entry.folder, 0)
            filtered_entry.file_count = file_counts.get(file_combination, 0)
            filtered_entry.function_count = function_counts.get(function_combination, 0)
            if filtered_entry.limit_passed:
                self.filtered_data.append(filtered_entry)
        
        # Return text output (for HTTP/Parser backends)
        table_output = self.render_table_hook()
        if not self.filtered_data:
            self._get_shared_store().clear_processed_data()
            self.clear_combinations()
            self._module_colors.clear()
            self._filename_colors.clear()
            self._function_colors.clear()
            self._module_color_index = 0
            return table_output
        rendered_lines = []
        for entry in self.filtered_data:
            module_color_index = self.get_module_color(entry.folder)
            filename_color_index = self.get_filename_color(entry.folder, entry.filename)
            function_color_index = self.get_function_color(entry.folder, entry.filename, entry.function_name)
            module_color = COLORS[COLOR_NAMES[module_color_index]]
            filename_color = COLORS[COLOR_NAMES[filename_color_index]]
            function_color = COLORS[COLOR_NAMES[function_color_index]]
            display_module = trim_document_root(entry.folder)
            display_filename = trim_document_root(entry.filename)
            colored_message = f"{module_color}{display_module}{RESET_COLOR} - {filename_color}{display_filename}{RESET_COLOR} - {function_color}{entry.function_name}{RESET_COLOR} - {entry.message}"
            rendered_lines.append(colored_message)
        self._get_shared_store().clear_processed_data()
        self.clear_combinations()
        self._module_colors.clear()
        self._filename_colors.clear()
        self._function_colors.clear()
        self._module_color_index = 0
        safe_output = '\n'.join(rendered_lines)
        debug_print(f"debug_safe.render() - table_output length: {len(table_output) if table_output else 0}")
        debug_print(f"debug_safe.render() - safe_output length: {len(safe_output) if safe_output else 0}")
        if table_output and safe_output:
            result = table_output + '\n' + safe_output
            debug_print(f"debug_safe.render() - returning combined output, length: {len(result)}")
            return result
        elif table_output:
            debug_print(f"debug_safe.render() - returning table_output only, length: {len(table_output)}")
            return table_output
        else:
            debug_print(f"debug_safe.render() - returning safe_output only, length: {len(safe_output)}")
            return safe_output

_debug = Debug()

def get_debug() -> Debug:
    return _debug
