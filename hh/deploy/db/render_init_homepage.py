from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser
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


def render_success_section(source_data: Dict[str, Union[str, int]], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        log("Rendering success section for homepage creation")
        summary_data = TableData()
        summary_data.add_row(
            'success',
            value='Homepage created successfully'
        )
        homepage_id = source_data.get('homepage_id')
        if homepage_id:
            summary_data.add_row(
                'homepage_id',
                value=str(homepage_id)
            )
        project_name = source_data.get('project_name')
        if project_name:
            summary_data.add_row(
                'project_name',
                value=safe_str(project_name)
            )
        created_at = source_data.get('created_at')
        if created_at:
            summary_data.add_row(
                'created_at',
                value=safe_str(created_at)
            )
        text_content = source_data.get('text')
        if text_content:
            summary_data.add_row(
                'text_content',
                value=safe_str(text_content)
            )
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('init_homepage_header')
                .add_group(['success'], 'result')
                .add_simple(['homepage_id', 'project_name', 'created_at', 'text_content']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_error_section(source_data: Dict[str, Union[str, int]], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        error_message = source_data.get('error', 'Unknown error occurred')
        log(f"Rendering error section: {error_message}")
        summary_data = TableData()
        summary_data.add_row(
            'error',
            value='Homepage creation failed'
        )
        summary_data.add_row(
            'error',
            value=safe_str(error_message)
        )
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('init_homepage_header')
                .add_simple(['error']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


@register_parser('init_homepage')
def init_homepage() -> bool:
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
    lines.append(render_header_block('l_init_homepage_header'))
    source_data = get_data(json_data)
    log("Processing init homepage data successfully")
    # Check if response contains error
    if 'error' in source_data:
        log("Homepage creation failed, rendering error section")
        render_error_section(source_data, lines)
    else:
        log("Homepage creation succeeded, rendering success section")
        render_success_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
