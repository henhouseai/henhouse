from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh_page.page_registry import get_page

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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

@register_action('modify_account_type')
@register_command('modify_account_type')
def modify_account_type() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set('type'):
            warn("No new account type provided")
            report_error("action", "New account type is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        new_type = gateway.get_arg('type')
        # Handle the case where -type is passed as a flag (returns True)
        if new_type is True:
            new_type = ""
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        # Validate account type against allowed values
        allowed_types = ['cash', 'checking', 'savings', 'online', 'credit', 'loan', 'service', 'person', 'open order', 'lease', 'sublet', 'house fund']
        if new_type not in allowed_types:
            warn(f"Invalid account type: '{new_type}'. Allowed types: {', '.join(allowed_types)}")
            report_error("action", f"Invalid account type: '{new_type}'. Allowed types: {', '.join(allowed_types)}")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} account type to '{new_type}'")
        success = page.modify_account_type(new_type)
        if not success:
            warn("Page account type modification failed")
            report_error("action", "Page account type modification failed")
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} account type to '{new_type}' with {total_children} children")
    trace_out()
    return not is_error()

