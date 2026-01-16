from __future__ import annotations
from typing import Dict, List, Union, Any, Optional
from hh.gateway.registry.registry import register_parser
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

@register_parser('deploy')
def render_deploy_hookified() -> bool:
    """
    Hookified deployment renderer - processes deploy_render hooks from modules.

    This is the new rendering architecture where each module provides its own
    rendering instructions via deploy_render hooks. The results can be either:
    - {"table_data": TableData, "field_config": FieldConfig} for aggregation into main summary
    - {"render_block": "pre-rendered HTML"} for direct inclusion as separate tables

    Pieces are aggregated into ONE summary table, full tables are inserted between pieces.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_deploy_hookified")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False

    lines = []
    lines.append(render_header_block('l_deploy_header'))
    log(f"Processing hookified deploy data")

    # Call deploy_render hooks from all modules
    from hh.gateway.registry.module_hooks import run_hooks
    render_instructions = run_hooks('deploy_render')

    # Separate pieces for summary table vs full tables
    summary_table_data = TableData()
    summary_field_config = FieldConfig()
    full_tables = []  # List of (instruction_index, render_block) tuples

    # Process each render instruction and collect pieces
    for i, instruction in enumerate(render_instructions):
        if 'render_block' in instruction:
            # Full table - collect for insertion at this position
            full_tables.append((i, instruction['render_block']))
        elif 'table_data' in instruction and 'field_config' in instruction:
            # Piece for summary table - aggregate it
            piece_table_data = instruction['table_data']
            piece_field_config = instruction['field_config']

            # Merge table data (add all rows)
            for row in piece_table_data.rows:
                summary_table_data.rows.append(row)

            # Merge field configs (add all simple fields - hooks should NOT define headers)
            summary_field_config.configs.extend(piece_field_config.configs)

    # Build output: summary table first, then full tables in order
    if summary_table_data.num_rows() > 0 and summary_field_config.configs:
        # Add summary header since we have content (hooks only provide simple fields)
        summary_field_config.add_header('deploy_summary')
        summary_block = render_block(summary_table_data, summary_field_config, block_type='deploy_summary')
        lines.append(summary_block)
        break_section(lines)

    # Add full tables in the order they appeared
    for _, full_table_html in full_tables:
        lines.append(full_table_html)
        break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
