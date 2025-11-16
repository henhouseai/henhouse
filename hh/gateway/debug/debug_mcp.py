from __future__ import annotations
from typing import Dict, List
from hh.gateway.debug.debug_safe import Debug, DebugEntry, trim_document_root

def debug_print(message: str) -> None:
    """Debug print function that can be easily enabled/disabled"""
    # Uncomment the next line to enable debug prints
    # print(f"DEBUG: {message}")
    pass


class DebugMCP(Debug):
    """Debug module for MCP backend - outputs JSON structure instead of ANSI text."""
    
    def render(self) -> Dict[str, List[Dict]]:
        """Render debug output as JSON structure for MCP responses."""
        debug_print(f"debug_mcp.render() - starting render")
        self.get_arg_overrides()
        self.filtered_data = []
        folder_counts = {}
        file_counts = {}
        function_counts = {}
        shared_data = self._get_shared_store().captured_data
        debug_print(f"debug_mcp.render() - shared_data length: {len(shared_data)}")
        
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
            if entry.level >= 3:
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
        
        # Build JSON structure with shortened keys and normalized timestamps
        debug_entries = []
        base_timestamp = None
        
        for entry in self.filtered_data:
            display_module = trim_document_root(entry.folder)
            display_filename = trim_document_root(entry.filename)
            level_name = {1: "trace_in", 2: "trace_out", 3: "log", 4: "debug", 5: "warn"}.get(entry.level, "unknown")
            
            # Set base timestamp from first entry
            if base_timestamp is None:
                base_timestamp = entry.timestamp
            
            # Calculate delta in milliseconds (rounded)
            delta_ms = int((entry.timestamp - base_timestamp) * 1000)
            
            debug_entries.append({
                "L": level_name,  # level
                "F": display_module,  # folder
                "I": display_filename,  # file
                "U": entry.function_name,  # function
                "M": entry.message,  # message
                "T": delta_ms  # timestamp delta in milliseconds
            })
        
        self._get_shared_store().clear_processed_data()
        self.clear_combinations()
        self._module_colors.clear()
        self._filename_colors.clear()
        self._function_colors.clear()
        self._module_color_index = 0
        
        # Always return dict structure, even if entries array is empty
        return {"entries": debug_entries}

_debug = DebugMCP()

def get_debug() -> DebugMCP:
    return _debug

