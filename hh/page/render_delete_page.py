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


def render_delete_section(source_data: Dict[str, Union[str, int]], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        log("Rendering delete page data section")
        delete_data = TableData()
        # Deleted Page ID
        deleted_page_id = source_data.get('deleted_page_id')
        if deleted_page_id:
            delete_data.add_row(
                'deleted_page_id',
                value=str(deleted_page_id)
            )
        # Delete Status
        status = source_data.get('status')
        if status:
            delete_data.add_row(
                'delete_status',
                value=safe_str(status)
            )
        lines.append(render_block(
            delete_data,
            FieldConfig()
                .add_header('delete_page_header')
                .add_simple(['deleted_page_id', 'delete_status']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


@register_parser('delete_page')
def delete_page() -> bool:
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
    lines.append(render_header_block('l_delete_page_header'))
    source_data = get_data(json_data)
    log("Processing delete page data successfully")
    # Render delete data section
    render_delete_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
