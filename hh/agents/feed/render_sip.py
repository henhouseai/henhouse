from __future__ import annotations
from typing import Any, Dict, List
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, ic, out, break_section
from hh.gateway.response.json_standard import get_data
from hh.render.config.config import safe_str
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



def render_summary_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    if not gateway.is_no(block):
        log(f"Rendering summary section for agent {source_data.get('agent_id')}")
        table_data = TableData()
        if source_data.get('agent_id'):
            table_data.add_row(
                'summary_agent',
                value=str(source_data.get('agent_id'))
            )
        channels = source_data.get('channels', [])
        if channels:
            channels_str = ', '.join(safe_str(ch) for ch in channels)
            table_data.add_row(
                'summary_channels',
                value=channels_str
            )
        if source_data.get('message_count') is not None:
            table_data.add_row(
                'summary_messages',
                value=str(source_data.get('message_count'))
            )
        if source_data.get('timestamp'):
            table_data.add_row(
                'summary_timestamp',
                value=safe_str(source_data.get('timestamp'))
            )
        if table_data.num_rows() > 0:
            lines.append(render_block(
                table_data, 
                FieldConfig()
                    .add_simple(['summary_agent', 'summary_channels', 'summary_messages', 'summary_timestamp']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            log(f"Summary section rendered with {table_data.num_rows()} fields")
    trace_out()

def render_message_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    if not gateway.is_no('rows') and not (gateway.is_no('message_summary') and gateway.is_no('meta')):
        messages = source_data.get('messages', [])
        log(f"Rendering message section with {len(messages)} messages")
        if not messages:
            lines.append(out(dc('l_no_messages')))
            log("No messages found, rendering no messages message")
            trace_out()
            return
        for message in messages:
            render_single_message(message, lines)
    trace_out()

def render_single_message(message: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    table_data = TableData()
    if not gateway.is_no('rows') and not gateway.is_no('message_summary'):
        log(f"Rendering single message: {message.get('message_id')} from {message.get('from_agent_id')}")
        if message.get('message_id'):
            table_data.add_row(
                'message_id',
                value=str(message.get('message_id'))
            )
        if message.get('channel_name'):
            table_data.add_row(
                'channel_name',
                value=safe_str(message.get('channel_name'))
            )
        if message.get('queued_ts'):
            table_data.add_row(
                'queued_ts',
                value=safe_str(message.get('queued_ts'))
            )
        if message.get('occurred_ts'):
            table_data.add_row(
                'occurred_ts',
                value=safe_str(message.get('occurred_ts'))
            )
        from_agent_data = {
            'from_name': message.get('from_display_name') or f"agent {message.get('from_agent_id')}",
            'from_id': message.get('from_agent_id')
        }
        if from_agent_data.get('from_name') or from_agent_data.get('from_id'):
            from_value = f"{safe_str(from_agent_data.get('from_name'))} (ID: {safe_str(from_agent_data.get('from_id'))})" if from_agent_data.get('from_id') else safe_str(from_agent_data.get('from_name'))
            table_data.add_row(
                'from_agent',
                value=from_value
            )
        to_agent_data = {
            'to_name': f"agent {message.get('to_agent_id')}" if message.get('to_agent_id') else None,
            'to_id': message.get('to_agent_id')
        }
        if to_agent_data.get('to_id'):
            to_value = f"{safe_str(to_agent_data.get('to_name'))} (ID: {safe_str(to_agent_data.get('to_id'))})" if to_agent_data.get('to_id') else safe_str(to_agent_data.get('to_name'))
            table_data.add_row(
                'to_agent',
                value=to_value
            )
        if message.get('kind'):
            kind_field_type = f"kind_{message.get('kind')}"
            table_data.add_row(
                kind_field_type,
                value=safe_str(message.get('kind'))
            )
        if table_data.num_rows() > 0:
            lines.append(render_block(
                table_data, 
                FieldConfig()
                    .add_simple(['message_id', 'channel_name', 'queued_ts', 'occurred_ts', 'from_agent', 'to_agent', 'kind_operator', 'kind_microlog', 'kind_message', 'kind_pointer']),
                table_overrides={'margin_l': 4},
                block_type='rows'
            ))
            break_section(lines)
    if not gateway.is_no('meta'):
        meta_data = message.get('meta')
        if meta_data:
            log(f"Rendering meta data for message {message.get('message_id')}")
            lines.append(render_block(
                meta_data,
                block_type='meta'
            ))
            break_section(lines)
    if not gateway.is_no('content'):
        content_text = message.get('content', '')
        if content_text:
            log(f"Rendering content for message {message.get('message_id')}: {len(content_text)} characters")
            content_table_data = TableData()
            content_table_data.add_row(
                '',
                contents=content_text
            )
            lines.append(render_block(
                content_table_data,
                FieldConfig(),
                table_class='minimal',
                table_overrides={
                    'margin_l': 4,
                    'has_header': False,
                    'padl': 0,
                    'padr': 0
                },
                block_type='content'
            ))
            break_section(lines)
    trace_out()

def get_subheader_from_envelope(data: Dict[str, Any]) -> str:
    trace_in()
    # TODO: RID feature was removed - this logic needs to be fixed properly
    # Previously used 'rid' field from envelope to determine header type
    # if isinstance(data, dict) and 'rid' in data:
    #     rid = data['rid']
    #     if 'peek' in rid:
    #         log("Detected peek header from RID")
    #         trace_out()
    #         return 'l_peek_header'
    #     elif 'sip' in rid:
    #         log("Detected sip header from RID")
    #         trace_out()
    #         return 'l_sip_header'
    #     elif 'gossip' in rid:
    #         log("Detected gossip header from RID")
    #         trace_out()
    #         return 'l_gossip_header'
    if isinstance(data, dict):
        if 'messages' in data and 'channels' in data:
            if data.get('channels') == ['dm'] and data.get('message_count') == 1:
                log("Detected gossip header from data structure")
                trace_out()
                return 'l_gossip_header'
            elif 'agent_id' in data:
                log("Detected sip header from data structure")
                trace_out()
                return 'l_sip_header'
            else:
                log("Detected peek header from data structure")
                trace_out()
                return 'l_peek_header'
    log("Using default peek header")
    trace_out()
    return 'l_peek_header'

def _render_watercooler_parser() -> bool:
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
    if json_data is None:
        warn("No action response data available")
        trace_out()
        return False
    
    source_data = get_data(json_data)
    
    lines = []
    subheader = get_subheader_from_envelope(json_data)
    lines.append(render_header_block(subheader))
    
    log(f"Processing {source_data.get('message_count', 0)} messages")
    render_summary_section(source_data, lines)
    render_message_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Watercooler parser completed: {len(lines)} lines generated")
    trace_out()
    return True

@register_parser('peek')
def peek() -> bool:
    return _render_watercooler_parser()

@register_parser('sip')
def sip() -> bool:
    return _render_watercooler_parser()

@register_parser('gossip')
def gossip() -> bool:
    return _render_watercooler_parser()
