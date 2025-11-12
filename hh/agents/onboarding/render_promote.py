from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
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


def render_summary_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_summary_section")
        trace_out()
        return
    block = 'summary'
    if not gateway.is_no(block):
        summary_data = TableData()
        log(f"Rendering summary section for agent {source_data.get('agent_id')}")
        
        summary_data.add_row(
            'success',
            value='Promotion successful'
        )
        
        if source_data.get('agent_id'):
            summary_data.add_row(
                'agent_id',
                value=str(source_data.get('agent_id'))
            )
        
        if source_data.get('old_role'):
            summary_data.add_row(
                'old_role',
                value=safe_str(source_data.get('old_role'))
            )
        
        if source_data.get('new_role'):
            summary_data.add_row(
                'new_role',
                value=safe_str(source_data.get('new_role'))
            )
        
        if source_data.get('promotion_successful') is not None:
            successful = source_data.get('promotion_successful')
            summary_data.add_row(
                'promotion_successful',
                value='Yes' if successful else 'No'
            )
        
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('promote_header')
                .add_group(['success'], 'result')
                .add_simple(['agent_id', 'old_role', 'new_role', 'promotion_successful', 'role_training_complete', 'message', 'next_command']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_status_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_status_section")
        trace_out()
        return
    block = 'rows'
    if not gateway.is_no(block):
        status_data = TableData()
        log(f"Rendering status section for agent {source_data.get('agent_id')}")
        
        if source_data.get('role_training_complete') is not None:
            complete = source_data.get('role_training_complete')
            status_data.add_row(
                'role_training_complete',
                value='Yes' if complete else 'No'
            )
        
        if source_data.get('message'):
            status_data.add_row(
                'message',
                value=safe_str(source_data.get('message'))
            )
        
        if status_data.num_rows() > 0:
            lines.append(render_block(
                status_data,
                FieldConfig()
                    .add_header('promote_header')
                    .add_group(['success'], 'result')
                    .add_simple(['agent_id', 'old_role', 'new_role', 'promotion_successful', 'role_training_complete', 'message', 'next_command']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()

def render_next_steps(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_next_steps")
        trace_out()
        return
    block = 'rows'
    if not gateway.is_no(block):
        steps_data = TableData()
        log(f"Rendering next steps for agent {source_data.get('agent_id')}")
        
        if source_data.get('next_command'):
            steps_data.add_row(
                'next_command',
                value=safe_str(source_data.get('next_command'))
            )
        
        if steps_data.num_rows() > 0:
            lines.append(render_block(
                steps_data,
                FieldConfig()
                    .add_header('promote_header')
                    .add_group(['success'], 'result')
                    .add_simple(['agent_id', 'old_role', 'new_role', 'promotion_successful', 'role_training_complete', 'message', 'next_command']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()

def _render_promote_parser() -> bool:
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
    source_data = get_data(json_data)
    
    lines = []
    lines.append(render_header_block('l_promote_header'))
    
    log(f"Processing promote data for agent {source_data.get('agent_id')}")
    render_summary_section(source_data, lines)
    render_status_section(source_data, lines)
    render_next_steps(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Promote parser completed: {len(result)} characters")
    trace_out()
    return True

@register_http('promote')
@register_parser('promote')
def promote() -> bool:
    return _render_promote_parser()
