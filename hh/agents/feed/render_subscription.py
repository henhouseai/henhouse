from __future__ import annotations
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.gateway.response.json_standard import get_data
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


def render_subscription_parser() -> bool:
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
    lines.append(render_header_block('l_subscription_header'))
    actual_data = get_data(json_data)
    summary_data = TableData()
    if actual_data.get('subscription_created'):
        operation = "Subscription Created"
        field_type = "subscription_created"
        log("Rendering subscription created")
    elif actual_data.get('subscription_removed'):
        operation = "Subscription Removed"
        field_type = "subscription_removed"
        log("Rendering subscription removed")
    summary_data.add_row(
        field_type,
        value=operation
    )
    target_type = actual_data.get('target_type', 'Unknown')
    target_id = actual_data.get('target_id', 'Unknown')
    target_title = actual_data.get('target_title', 'Unknown')
    log(f"Target: {target_type} {target_id} - {target_title}")
    summary_data.add_row(
        'target_type',
        value=target_type.upper()
    )
    summary_data.add_row(
        'target_id',
        value=str(target_id)
    )
    summary_data.add_row(
        'target_title',
        value=target_title
    )
    if 'messages_queued' in actual_data:
        messages_count = actual_data.get('messages_queued', 0)
        log(f"Messages queued: {messages_count}")
        summary_data.add_row(
            'messages_queued',
            value=str(messages_count)
        )
    elif 'messages_removed' in actual_data:
        messages_count = actual_data.get('messages_removed', 0)
        log(f"Messages removed: {messages_count}")
        summary_data.add_row(
            'messages_removed',
            value=str(messages_count)
        )
    total_chars = actual_data.get('total_characters', 0)
    if total_chars > 0:
        log(f"Total characters: {total_chars:,}")
        summary_data.add_row(
            'total_characters',
            value=f"{total_chars:,}"
        )
    queue_table = actual_data.get('queue_table', '')
    if queue_table:
        log(f"Queue table: {queue_table}")
        summary_data.add_row(
            'queue_table',
            value=queue_table
        )
    lines.append(render_block(
        summary_data, 
        FieldConfig()
            .add_header('subscription_header')
            .add_simple(['target_type', 'target_id', 'target_title', 'messages_queued', 'messages_removed', 'total_characters', 'queue_table', 'error']),
        table_overrides={'margin_l': 4}
    ))
    log(f"Rendered {summary_data.num_rows()} summary fields")
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

@register_http('subscribe_agent')
@register_parser('subscribe_agent')
def subscribe_agent() -> bool:
    return render_subscription_parser()

@register_http('subscribe_ask')
@register_parser('subscribe_ask')
def subscribe_ask() -> bool:
    return render_subscription_parser()

@register_http('subscribe_docket')
@register_parser('subscribe_docket')
def subscribe_docket() -> bool:
    return render_subscription_parser()

@register_http('subscribe_keyword')
@register_parser('subscribe_keyword')
def subscribe_keyword() -> bool:
    return render_subscription_parser()

@register_http('subscribe_operator')
@register_parser('subscribe_operator')
def subscribe_operator() -> bool:
    return render_subscription_parser()

@register_http('subscribe_sidecar')
@register_parser('subscribe_sidecar')
def subscribe_sidecar() -> bool:
    return render_subscription_parser()

@register_http('subscribe_step')
@register_parser('subscribe_step')
def subscribe_step() -> bool:
    return render_subscription_parser()

@register_http('subscribe_task')
@register_parser('subscribe_task')
def subscribe_task() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_agent')
@register_parser('unsubscribe_agent')
def unsubscribe_agent() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_ask')
@register_parser('unsubscribe_ask')
def unsubscribe_ask() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_docket')
@register_parser('unsubscribe_docket')
def unsubscribe_docket() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_keyword')
@register_parser('unsubscribe_keyword')
def unsubscribe_keyword() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_operator')
@register_parser('unsubscribe_operator')
def unsubscribe_operator() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_sidecar')
@register_parser('unsubscribe_sidecar')
def unsubscribe_sidecar() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_step')
@register_parser('unsubscribe_step')
def unsubscribe_step() -> bool:
    return render_subscription_parser()

@register_http('unsubscribe_task')
@register_parser('unsubscribe_task')
def unsubscribe_task() -> bool:
    return render_subscription_parser()
