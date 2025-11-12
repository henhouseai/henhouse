from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data

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


def render_summary_section(source_data: Dict[str, Union[str, int]], lines: List[str]) -> None:
    trace_in()
    block = 'rows'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        pages_count = source_data.get('pages_count', 0)
        images_count = source_data.get('images_count', 0)
        log(f"Rendering count pages summary: pages={pages_count}, images={images_count}")
        # Create table data with header row
        table_data = TableData()
        # Add header row
        table_data.add_row(
            'table_count_header',
            table_name='table',
            row_count='count'
        )
        # Add data rows
        table_data.add_row(
            'table_count',
            table_name='pages',
            row_count=str(pages_count)
        )
        table_data.add_row(
            'table_count',
            table_name='images',
            row_count=str(images_count)
        )
        lines.append(render_block(
            table_data,
            FieldConfig()
                .add_header('table_count_header')
                .add_simple(['table_count']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


@register_http('count_pages')
@register_parser('count_pages')
def count_pages() -> bool:
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
    lines = []
    lines.append(render_header_block('l_count_pages_header'))
    source_data = get_data(json_data)
    log("Processing count pages data successfully")
    render_summary_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True