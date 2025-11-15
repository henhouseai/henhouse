from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
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



def render_agent_info_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    """Render agent information section"""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_agent_info_section")
        trace_out()
        return
    
    block = 'agent_info'
    if not gateway.is_no(block):
        agent_info = source_data.get('agent_info', {})
        log(f"Rendering agent info for agent {agent_info.get('agent_id')}")
        
        info_data = TableData()
        info_data.add_row(
            'agent_info',
            value=str(agent_info.get('agent_id', 'N/A'))
        )
        info_data.add_row(
            'agent_info',
            value=safe_str(agent_info.get('badge_ts', 'N/A'))
        )
        info_data.add_row(
            'agent_info',
            value=safe_str(agent_info.get('persona_name', 'N/A'))
        )
        info_data.add_row(
            'agent_info',
            value=safe_str(agent_info.get('role', 'N/A'))
        )
        info_data.add_row(
            'agent_info',
            value='Active' if agent_info.get('is_active') else 'Inactive'
        )
        
        created_at = agent_info.get('created_at')
        terminated = agent_info.get('terminated')
        
        if created_at:
            info_data.add_row(
                'agent_info',
                value=safe_str(created_at)
            )
        if terminated is not None:
            info_data.add_row(
                'agent_info',
                value='Yes' if terminated else 'No'
            )
        
        lines.append(render_block(
            info_data,
            FieldConfig()
                .add_header('status_header')
                .add_simple(['agent_info', 'training_progress', 'answers']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_training_progress_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    """Render training progress section"""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_training_progress_section")
        trace_out()
        return
    
    block = 'training_progress'
    if not gateway.is_no(block):
        training_progress = source_data.get('training_progress', {})
        is_complete = source_data.get('is_training_complete', False)
        is_role_complete = source_data.get('is_role_training_complete', False)
        
        log(f"Rendering training progress for {len(training_progress)} roles")
        
        progress_data = TableData()
        
        # Status summary
        if is_complete:
            status_text = "✅ Training Complete!"
        elif is_role_complete:
            status_text = "✅ Role Training Complete!"
        else:
            status_text = "🔄 Training In Progress"
        
        progress_data.add_row(
            'training_progress',
            value=status_text
        )
        
        # Show progress by role
        for role, progress in training_progress.items():
            progress_data.add_row(
                'training_progress',
                value=f"{progress['completed']}/{progress['total']} ({progress['percentage']:.1f}%)"
            )
        
        lines.append(render_block(
            progress_data,
            FieldConfig()
                .add_header('status_header')
                .add_simple(['agent_info', 'training_progress', 'answers']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_answers_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    """Render answered questions section"""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_answers_section")
        trace_out()
        return
    
    block = 'answers'
    if not gateway.is_no(block):
        answers = source_data.get('answers', [])
        
        log(f"Rendering {len(answers)} answered questions")
        
        if not answers:
            answers_data = TableData()
            answers_data.add_row(
                'answers',
                value='No questions answered yet.'
            )
        else:
            answers_data = TableData()
            
            # Group answers by gate
            gate_answers = {}
            for answer in answers:
                gate_num = answer.get('gate_number', 0)
                if gate_num not in gate_answers:
                    gate_answers[gate_num] = []
                gate_answers[gate_num].append(answer)
            
            # Render each gate's answers
            for gate_num in sorted(gate_answers.keys()):
                gate_answers_list = gate_answers[gate_num]
                
                for i, answer in enumerate(gate_answers_list, 1):
                    answers_data.add_row(
                        'answers',
                        value=f"File: {answer.get('filename', 'N/A')} | Asked: {answer.get('created_at', 'N/A')}"
                    )
                    answers_data.add_row(
                        'answers',
                        value=safe_str(answer.get('question', 'N/A'))
                    )
                    answers_data.add_row(
                        'answers',
                        value=safe_str(answer.get('response', 'N/A'))
                    )
                    answers_data.add_row(
                        'answers',
                        value='---'
                    )
        
        lines.append(render_block(
            answers_data,
            FieldConfig()
                .add_header('status_header')
                .add_simple(['agent_info', 'training_progress', 'answers']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_available_roles_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    """Render available roles section"""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_available_roles_section")
        trace_out()
        return
    
    block = 'available_roles'
    if not gateway.is_no(block):
        available_roles = source_data.get('available_roles', [])
        
        log(f"Rendering {len(available_roles)} available roles")
        
        roles_data = TableData()
        if available_roles:
            for role in available_roles:
                roles_data.add_row(
                    'available_roles',
                    value=safe_str(role)
                )
        else:
            roles_data.add_row(
                'available_roles',
                value='No roles available.'
            )
        
        lines.append(render_block(
            roles_data,
            FieldConfig()
                .add_header('status_header')
                .add_simple(['agent_info', 'training_progress', 'answers']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_summary_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    """Render summary section"""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_summary_section")
        trace_out()
        return
    
    block = 'summary'
    if not gateway.is_no(block):
        agent_info = source_data.get('agent_info', {})
        answers = source_data.get('answers', [])
        is_complete = source_data.get('is_training_complete', False)
        timestamp = source_data.get('timestamp', 'N/A')
        
        log(f"Rendering summary for agent {agent_info.get('agent_id')}")
        
        summary_data = TableData()
        summary_data.add_row(
            'summary',
            value=f"{agent_info.get('persona_name', 'N/A')} (ID: {agent_info.get('agent_id', 'N/A')})"
        )
        summary_data.add_row(
            'summary',
            value=safe_str(agent_info.get('role', 'N/A'))
        )
        summary_data.add_row(
            'summary',
            value=str(len(answers))
        )
        summary_data.add_row(
            'summary',
            value='Complete' if is_complete else 'In Progress'
        )
        summary_data.add_row(
            'summary',
            value=safe_str(timestamp)
        )
        
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('status_header')
                .add_simple(['agent_info', 'training_progress', 'answers']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def _render_status_parser() -> bool:
    """Render status parser output"""
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
    lines.append(render_header_block('l_status_header'))
    
    log(f"Processing status data for agent {source_data.get('agent_info', {}).get('agent_id')}")
    render_agent_info_section(source_data, lines)
    render_training_progress_section(source_data, lines)
    render_answers_section(source_data, lines)
    render_available_roles_section(source_data, lines)
    render_summary_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Status parser completed: {len(result)} characters")
    trace_out()
    return True


@register_parser('status')
def status() -> bool:
    """Parse and format status output"""
    return _render_status_parser()


if __name__ == "__main__":
    status()
