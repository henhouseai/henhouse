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


def render_pull_project_section(source_data: Dict[str, Union[str, int, bool]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_pull_project_section")
        trace_out()
        return
    
    block = 'project'
    if not gateway.is_no(block):
        pull_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        project_path = source_data.get('project_path', 'Unknown')
        current_branch = source_data.get('current_branch', 'Unknown')
        branch_switched = source_data.get('branch_switched', False)
        short_hash = source_data.get('short_hash', 'Unknown')
        commit_message = source_data.get('commit_message', 'Unknown')
        time_ago = source_data.get('time_ago', 'Unknown')
        cache_cleared = source_data.get('cache_cleared', [])
        
        log(f"Rendering pull project section for: {project_name}")
        debug(f"Source data keys: {list(source_data.keys())}")
        
        # Project header
        pull_data.add_row(
            'project_header',
            value=safe_str(project_name)
        )
        
        # Current branch
        if not gateway.is_no('branch'):
            pull_data.add_row(
                'current_branch',
                value=safe_str(current_branch)
            )
        
        # Branch switched
        if not gateway.is_no('switch'):
            status = "Yes" if branch_switched else f"No (already on {project_name})"
            pull_data.add_row(
                'branch_switched',
                value=safe_str(status)
            )
        
        # Short hash
        if not gateway.is_no('hash'):
            pull_data.add_row(
                'short_hash',
                value=safe_str(short_hash)
            )
        
        # Commit message
        if not gateway.is_no('message'):
            pull_data.add_row(
                'commit_message',
                value=safe_str(commit_message)
            )
        
        # Time ago
        if not gateway.is_no('time'):
            pull_data.add_row(
                'time_ago',
                value=safe_str(time_ago)
            )
        
        # Cache cleared - show each cache separately
        if not gateway.is_no('cache'):
            if cache_cleared:
                for cache_path in cache_cleared:
                    pull_data.add_row(
                        'cache_cleared',
                        value=safe_str(cache_path)
                    )
            else:
                pull_data.add_row(
                    'cache_cleared',
                    value=safe_str("No cache folders found")
                )
        
        debug(f"Final pull_data: {pull_data.num_rows()} items")
        debug(f"Pull data structure: {pull_data}")
        
        lines.append(render_block(
            pull_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['current_branch', 'branch_switched', 'short_hash', 'commit_message', 'time_ago', 'cache_cleared']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

@register_parser('pull_project')
def pull_project() -> bool:
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
    lines.append(render_header_block('l_pull_project_header'))
    source_data = get_data(json_data)
    log(f"Processing pull project data successfully")
    
    render_pull_project_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
