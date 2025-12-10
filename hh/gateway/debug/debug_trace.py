from __future__ import annotations
from typing import Dict, Any
from hh.gateway.debug.debug_table import DebugTable

def debug_print(message: str) -> None:
    """Debug print function that can be easily enabled/disabled"""
    # Uncomment the next line to enable debug prints
    print(f"DEBUG: {message}")
    pass

class DebugTrace(DebugTable):


    def process_extra_data_disabled(self) -> None:
        debug_print(f"debug_trace.process_extra_data() - starting")
        
        # INDEPENDENT COUNTING LOGIC - BEFORE TREE BUILDING
        max_depth = 0
        call_count_by_depth = {}
        leaf_count_by_depth = {}
        call_stack = []

        shared_data = self._get_shared_store().captured_data
        debug_print(f"debug_trace.process_extra_data() - shared_data length: {len(shared_data)}")
        
        # Process raw trace data for independent counting
        for entry in shared_data:
            if entry.level == 1:  # Function entry
                call_stack.append(entry.function_name)
                current_depth = len(call_stack)
                max_depth = max(max_depth, current_depth)
                call_count_by_depth[current_depth] = call_count_by_depth.get(current_depth, 0) + 1
                
            elif entry.level == 2:  # Function exit
                if call_stack:
                    popped = call_stack.pop()
                    # Check if this was a leaf call (no children in stack)
                    if len(call_stack) == 0 or not any(entry.level == 1 for entry in shared_data[shared_data.index(entry)+1:]):
                        leaf_count_by_depth[len(call_stack)] = leaf_count_by_depth.get(len(call_stack), 0) + 1
        
        # Debug printouts for independent counting
        debug_print(f"debug_trace.process_extra_data() - MAX DEPTH: {max_depth}")
        debug_print(f"debug_trace.process_extra_data() - CALL COUNT BY DEPTH:")
        for depth in sorted(call_count_by_depth.keys()):
            debug_print(f"debug_trace.process_extra_data() -   Depth {depth}: {call_count_by_depth[depth]} calls")
        debug_print(f"debug_trace.process_extra_data() - LEAF COUNT BY DEPTH:")
        for depth in sorted(leaf_count_by_depth.keys()):
            debug_print(f"debug_trace.process_extra_data() -   Depth {depth}: {leaf_count_by_depth[depth]} leaf calls")
        
        # NOW do the tree building (existing logic)
        trace_structure = {}
        call_stack = []
        
        # Count and validate trace entries
        level_1_count = 0
        level_2_count = 0
        for entry in shared_data:
            if entry.level == 1:
                level_1_count += 1
            elif entry.level == 2:
                level_2_count += 1
        
        debug_print(f"debug_trace.process_extra_data() - level 1 count: {level_1_count}, level 2 count: {level_2_count}")
        if level_1_count != level_2_count:
            debug_print(f"debug_trace.process_extra_data() - WARNING: Level 1 and Level 2 counts don't match!")
        
        for entry in shared_data:
            if entry.level == 1:  # Function entry
                function_name = entry.function_name
                call_stack.append(function_name)
                current_depth = len(call_stack)
                max_depth = max(max_depth, current_depth)
                # debug_print(f"debug_trace.process_extra_data() - ENTER: {function_name}, stack depth: {current_depth}")

                # Navigate to the correct position in the tree
                current = trace_structure
                for func in call_stack[:-1]:  # All but the current function
                    if func not in current:
                        current[func] = {}
                    if 'children' not in current[func]:
                        current[func]['children'] = {}
                    current = current[func]['children']

                # Add current function - don't add children yet
                if function_name not in current:
                    current[function_name] = {}

            elif entry.level == 2:  # Function exit
                if call_stack:
                    popped = call_stack.pop()
                    # debug_print(f"debug_trace.process_extra_data() - EXIT: {popped}, stack depth: {len(call_stack)}")
                else:
                    debug_print(f"debug_trace.process_extra_data() - ERROR: EXIT without matching ENTER for {entry.function_name}")
        
        # Validate nesting - check for unmatched calls
        if call_stack:
            debug_print(f"debug_trace.process_extra_data() - ERROR: Unmatched ENTER calls remaining: {call_stack}")
        else:
            debug_print(f"debug_trace.process_extra_data() - Nesting validation passed")

        # Second pass: mark all functions with no children as "leaf" and clean up structure
        def mark_leaves_and_cleanup(node):
            for func_name, func_data in node.items():
                if isinstance(func_data, dict):
                    if 'children' in func_data and func_data['children']:
                        # Has children, recurse and clean up
                        mark_leaves_and_cleanup(func_data['children'])
                    else:
                        # No children = leaf, remove empty children dict
                        func_data['is_leaf'] = True
                        if 'children' in func_data:
                            del func_data['children']

        mark_leaves_and_cleanup(trace_structure)
        self.trace_structure = trace_structure

    def render_extra_data_disabled(self) -> str:
        debug_print(f"debug_trace.render_extra_data() - has trace_structure: {hasattr(self, 'trace_structure')}")
        if hasattr(self, 'trace_structure'):
            result = self.render_trace_table(self.trace_structure)
            debug_print(f"debug_trace.render_extra_data() - trace table length: {len(result) if result else 0}")
            return result
        return ""

    def render_trace_table(self, trace_structure: Dict[str, Any]) -> str:
        if not trace_structure:
            return ""

        from hh.render.render_parser import render_meta_table
        # Show the raw trace structure as formatted JSON for debugging
        import json
        json_dump = f"TRACE STRUCTURE DEBUG OUTPUT:\n{json.dumps(trace_structure, indent=2)}"
        meta_table = render_meta_table(
            trace_structure,
            field_configs=[],
            table_class='div',
            table_overrides={'margin_l': 2, 'margin_r': 2, 'margin_t': 1, 'margin_b': 1},
            block_type='meta'
        )
        return f"{json_dump}\n{meta_table}"

_debug_trace = DebugTrace()

def get_debug() -> DebugTrace:
    return _debug_trace
