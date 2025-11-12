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


def render_summary_section(source_data: Dict[str, Union[str, int, list]], lines: List[str]) -> bool:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        summary_data = TableData()
        summary_data.add_row(
            'success',
            value='Operation completed successfully'
        )
        message = source_data.get('message', '')
        log(f"Rendering purge summary section with message: {message}")
        if message:
            summary_data.add_row(
                'info',
                value=safe_str(message)
            )
        agents_affected = source_data.get('agents_affected', 0)
        log(f"Purge affected {agents_affected} agents")
        summary_data.add_row(
            'count',
            value=f"{agents_affected} agent{'s' if agents_affected != 1 else ''}"
        )
        dry_run = source_data.get('dry_run', False)
        if dry_run:
            log("Purge was a dry run - no changes made")
            summary_data.add_row(
                'dry_run',
                value='DRY RUN - No changes made'
            )
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('purge_header')
                .add_group(['success'], 'result')
                .add_simple(['info', 'count', 'dry_run', 'operation', 'description', 'error']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()
    return True

def render_operations_section(source_data: Dict[str, Union[str, int, list]], lines: List[str]) -> bool:
    trace_in()
    block = 'rows'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        operations = source_data.get('operations', [])
        if not operations:
            log("No operations to render in purge section")
            trace_out()
            return True
        log(f"Rendering {len(operations)} purge operations")
        for i, operation in enumerate(operations):
            operation_data = TableData()
            operation_name = operation.get('operation', 'Unknown operation')
            log(f"Processing operation {i+1}: {operation_name}")
            operation_data.add_row(
                'operation',
                value=safe_str(operation_name)
            )
            description = operation.get('description', '')
            if description:
                operation_data.add_row(
                    'description',
                    value=safe_str(description)
                )
            lines.append(render_block(
                operation_data,
                FieldConfig()
                    .add_header('purge_header')
                    .add_group(['success'], 'result')
                    .add_simple(['info', 'count', 'dry_run', 'operation', 'description', 'error']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()
    return True


@register_http('agent_purge')
@register_parser('agent_purge')
def agent_purge() -> bool:
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
    lines.append(render_header_block('l_purge_header'))
    source_data = get_data(json_data)
    log("Processing agent purge data successfully")
    render_summary_section(source_data, lines)
    render_operations_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
