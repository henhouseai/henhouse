"""
Export database action - hookified orchestrator.

Coordinates database export operations through module hooks.
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.module_hooks import run_hooks
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.error.error_store import is_error, report_error
from hh.render.render import render_header_block, finalize_output

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_action('export_db')
@register_command('export_db')
def export_db(args: Optional[List[str]] = None) -> bool:
    """Export databases using module hooks."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False

    hook_results: List[Dict[str, Any]] = []

    # Phase 00: Pre-validate
    if not is_error():
        log("Running pre-validation hooks")
        results = run_hooks('export_db_00_pre_validate')
        if results:
            hook_results.extend(results)

    # Phase 05: Export cache database
    if not is_error():
        log("Exporting cache database")
        results = run_hooks('export_db_05_export_cache')
        if results:
            hook_results.extend(results)

    # Phase 10: Export main database
    if not is_error():
        log("Exporting main database")
        results = run_hooks('export_db_10_export_main')
        if results:
            hook_results.extend(results)

    # Phase 90: Cleanup
    if not is_error():
        log("Running cleanup hooks")
        results = run_hooks('export_db_90_cleanup')
        if results:
            hook_results.extend(results)

    if not is_error():
        result_data = {
            "hook_results": hook_results
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Database export encountered problems")

    return trace_out(not is_error())


@register_parser('export_db')
def render_export_db() -> bool:
    """
    Hookified renderer for export_db action.

    Processes export_db_95_render hooks from modules to build summary table.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_export_db")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    lines = []
    lines.append(render_header_block('l_export_db_header'))
    log("Processing hookified export_db data")

    # Call export_db_95_render hooks from all modules
    from hh.render.render import render_block, FieldConfig, TableData
    from hh.render.config.config import break_section

    render_instructions = run_hooks('export_db_95_render')

    # Aggregate pieces for summary table
    summary_table_data = TableData()
    summary_field_config = FieldConfig()

    # Process each render instruction and collect pieces
    for instruction in render_instructions:
        if 'table_data' in instruction and 'field_config' in instruction:
            # Piece for summary table - aggregate it
            piece_table_data = instruction['table_data']
            piece_field_config = instruction['field_config']

            # Merge table data (add all rows)
            for row in piece_table_data.rows:
                summary_table_data.rows.append(row)

            # Merge field configs
            summary_field_config.configs.extend(piece_field_config.configs)

    # Build output: summary table
    if summary_table_data.num_rows() > 0:
        # Add summary header
        summary_field_config.add_header('export_db_summary')
        summary_block = render_block(summary_table_data, summary_field_config, table_overrides={'margin_l': 4}, block_type='export_db_summary')
        lines.append(summary_block)
        break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
