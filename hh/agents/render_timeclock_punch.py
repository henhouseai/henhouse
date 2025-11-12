from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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


def render_summary_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str], operation: str) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_summary_section")
        trace_out()
        return
    block = 'summary'
    if not gateway.is_no(block):
        summary_data = TableData()
        operation_text = f"Punch {operation}" if operation in ['in', 'out'] else operation
        log(f"Rendering summary section for operation: {operation_text}")
        summary_data.add_row(
            'operation',
            value=operation_text
        )
        summary_data.add_row(
            'success',
            value='Operation completed successfully'
        )
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('punch_header')
                .add_group(['success'], 'result')
                .add_simple(['operation', 'agent_name', 'agent_id'])
                .add_group(['agent_status_active', 'agent_status_inactive'], 'agent_status')
                .add_simple(['timestamp']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_agent_details(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_agent_details")
        trace_out()
        return
    block = 'rows'
    if not gateway.is_no(block):
        agent_data = TableData()
        agent_name = source_data.get('full_name') or source_data.get('agent_key', 'Unknown')
        log(f"Rendering agent details for: {agent_name}")
        agent_data.add_row(
            'agent_name',
            value=safe_str(agent_name)
        )
        if source_data.get('agent_id'):
            agent_data.add_row(
                'agent_id',
                value=str(source_data.get('agent_id'))
            )
        if source_data.get('status'):
            status_value = source_data.get('status')
            status_field_type = f"agent_status_{status_value}" if status_value in ['active', 'inactive'] else 'agent_status_active'
            agent_data.add_row(
                status_field_type,
                value=safe_str(status_value)
            )
        lines.append(render_block(
            agent_data,
            FieldConfig()
                .add_header('punch_header')
                .add_group(['success'], 'result')
                .add_simple(['operation', 'agent_name', 'agent_id'])
                .add_group(['agent_status_active', 'agent_status_inactive'], 'agent_status')
                .add_simple(['timestamp']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def _render_punch_parser(operation: str) -> bool:
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
    lines.append(render_header_block('l_timeclock_header'))
    source_data = get_data(json_data)
    log(f"Processing punch {operation} data successfully")
    render_summary_section(source_data, lines, operation)
    render_agent_details(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

@register_http('punch_in')
@register_parser('punch_in')
def punch_in() -> bool:
    return _render_punch_parser("in")

@register_http('punch_out')
@register_parser('punch_out')
def punch_out() -> bool:
    return _render_punch_parser("out")
