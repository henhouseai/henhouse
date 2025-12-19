from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.tp.tp import TextProcessor

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

@register_action('get_text')
@register_command('get_text')
def get_text() -> bool:
    """Get processed/parsed text for a page. Returns HTTP-rendered text processed through TextProcessor."""
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    page_id: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    page = None
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        raw_text = page.text if page.text is not None else ""
        log(f"Processing text for page {page_id} (length: {len(raw_text)})")
        # Use get_prepared_text() which will check cache, process if needed, and set flag
        prepared_payload = page.get_prepared_text()
        if prepared_payload is None:
            warn(f"Text processing failed for page {page_id}")
            report_error("action", "Text processing failed - validation errors detected")
        else:
            processor = TextProcessor()
            processed_text = processor.postprocess(prepared_payload, final_decorator='http')
            response_data = {
                'page_id': page_id,
                'raw_text': raw_text,
                'processed_text': processed_text
            }
            gateway.response.set_action_response(success_payload(response_data))
            log(f"Successfully processed text for page {page_id} (processed length: {len(processed_text)})")
    
    trace_out()
    return not is_error()

