from __future__ import annotations
from typing import Dict, List, Union
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.gateway.response.json_standard import get_data
from hh.render.config.config import dc, ic
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


@register_parser('gulp')
def gulp(data: Dict[str, Union[str, int, List[str], Dict[str, Union[str, int, List[Dict[str, Union[str, int]]]]]]]) -> bool:
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
    lines.append(render_header_block('l_gulp_header'))
    
    log("Processing action response data")
    summary_data = TableData()
    summary_data.add_row(
        'agent_id',
        value=source_data.get('agent_id', 'N/A')
    )
    summary_data.add_row(
        'channels',
        value=', '.join(source_data.get('channels', []))
    )
    summary_data.add_row(
        'message_count',
        value=source_data.get('message_count', 0)
    )
    summary_data.add_row(
        'output_file',
        value=source_data.get('output_file', 'N/A')
    )
    summary_data.add_row(
        'export_timestamp',
        value=source_data.get('export_timestamp', 'N/A')
    )
    lines.append(render_block(
        summary_data, 
        FieldConfig()
            .add_simple(['agent_id', 'channels', 'message_count', 'output_file', 'export_timestamp']),
        block_type='summary'
    ))
    toc = source_data.get('table_of_contents', [])
    log(f"Processing table of contents: {len(toc)} entries")
    if not toc:
        lines.append(f"  {ic('info')} {dc('l_no_messages')}")
        log("No messages found in table of contents")
    else:
        lines.append(f"  {ic('info')} {dc('l_messages_preview')}:")
        lines.append("")
        toc_data = TableData()
        for toc_entry in toc:
            toc_data.add_row(
                'message_preview',
                message_index=toc_entry.get('message_index', ''),
                kind=toc_entry.get('kind', ''),
                direction=toc_entry.get('direction', ''),
                content_preview=toc_entry.get('content_preview', '')
            )
        lines.append(render_block(
            toc_data, 
            FieldConfig()
                .add_simple(['message_preview']),
            table_overrides={'margin_l': 4},
            block_type='rows'
        ))
        log(f"Rendered table of contents with {len(toc)} entries")
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Gulp parser completed: {len(lines)} lines generated")
    trace_out()
    return True
