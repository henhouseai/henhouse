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
            value='Answer recorded successfully'
        )
        
        if source_data.get('agent_id'):
            summary_data.add_row(
                'agent_id',
                value=str(source_data.get('agent_id'))
            )
        
        if source_data.get('role'):
            summary_data.add_row(
                'role',
                value=safe_str(source_data.get('role'))
            )
        
        if source_data.get('doc_path'):
            summary_data.add_row(
                'doc_path',
                value=safe_str(source_data.get('doc_path'))
            )
        
        if source_data.get('has_question') is not None:
            has_q = source_data.get('has_question')
            summary_data.add_row(
                'has_question',
                value='Yes' if has_q else 'No'
            )
        
        if source_data.get('response_recorded'):
            summary_data.add_row(
                'response_recorded',
                value='Yes'
            )
        
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('answer_header')
                .add_group(['success'], 'result')
                .add_simple(['agent_id', 'role', 'doc_path', 'has_question', 'response_recorded', 'coffees_done', 'coffees_total', 'exams_done', 'exams_total', 'training_complete', 'next_command']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_progress_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_progress_section")
        trace_out()
        return
    block = 'rows'
    if not gateway.is_no(block):
        progress_data = TableData()
        log(f"Rendering progress section for agent {source_data.get('agent_id')}")
        
        progress = source_data.get('progress', {})
        if progress:
            coffees = progress.get('coffees', [0, 0])
            exams = progress.get('exams', [0, 0])
            
            progress_data.add_row(
                'coffees_done',
                value=str(coffees[0])
            )
            
            progress_data.add_row(
                'coffees_total',
                value=str(coffees[1])
            )
            
            progress_data.add_row(
                'exams_done',
                value=str(exams[0])
            )
            
            progress_data.add_row(
                'exams_total',
                value=str(exams[1])
            )
        
        if source_data.get('training_complete') is not None:
            complete = source_data.get('training_complete')
            progress_data.add_row(
                'training_complete',
                value='Yes' if complete else 'No'
            )
        
        if progress_data.num_rows() > 0:
            lines.append(render_block(
                progress_data,
                FieldConfig()
                    .add_header('answer_header')
                    .add_group(['success'], 'result')
                    .add_simple(['agent_id', 'role', 'doc_path', 'has_question', 'response_recorded', 'coffees_done', 'coffees_total', 'exams_done', 'exams_total', 'training_complete', 'next_command']),
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
                    .add_header('answer_header')
                    .add_group(['success'], 'result')
                    .add_simple(['agent_id', 'role', 'doc_path', 'has_question', 'response_recorded', 'coffees_done', 'coffees_total', 'exams_done', 'exams_total', 'training_complete', 'next_command']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()

def _render_answer_parser() -> bool:
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
    lines.append(render_header_block('l_answer_header'))
    
    log(f"Processing answer data for agent {source_data.get('agent_id')}")
    render_summary_section(source_data, lines)
    render_progress_section(source_data, lines)
    render_next_steps(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Answer parser completed: {len(result)} characters")
    trace_out()
    return True

@register_http('answer')
@register_parser('answer')
def answer() -> bool:
    return _render_answer_parser()
