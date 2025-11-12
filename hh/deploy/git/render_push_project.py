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


def render_push_project_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_push_project_section")
        trace_out()
        return
    
    block = 'project'
    if not gateway.is_no(block):
        push_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        project_path = source_data.get('project_path', 'Unknown')
        message = source_data.get('message', 'Unknown')
        branch = source_data.get('branch', 'Unknown')
        title = source_data.get('title', 'Unknown')
        has_changes = source_data.get('has_changes', False)
        stage_file_created = source_data.get('stage_file_created', False)
        
        log(f"Rendering push project section for: {project_name}")
        debug(f"Source data keys: {list(source_data.keys())}")
        
        # Project header
        push_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        
        # Message
        if not gateway.is_no('message'):
            push_data.add_row(
                'message',
                value=safe_str(message)
            )
        
        # Branch
        if not gateway.is_no('branch'):
            push_data.add_row(
                'branch',
                value=safe_str(branch)
            )
        
        # Has changes
        if not gateway.is_no('changes'):
            status = "Yes" if has_changes else "No (empty commit)"
            push_data.add_row(
                'has_changes',
                value=safe_str(status)
            )
        
        # Stage file created
        if not gateway.is_no('stage'):
            status = "Yes" if stage_file_created else "No"
            push_data.add_row(
                'stage_file_created',
                value=safe_str(status)
            )
        
        debug(f"Final push_data: {push_data.num_rows()} items")
        debug(f"Push data structure: {push_data}")
        
        lines.append(render_block(
            push_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['message', 'branch', 'has_changes', 'stage_file_created']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('push_project')
def push_project() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False
    
    json_data = gateway.response.get_action_response()
    lines = []
    lines.append(render_header_block('l_push_project_header'))
    source_data = get_data(json_data)
    log(f"Processing push project data successfully")
    
    render_push_project_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
