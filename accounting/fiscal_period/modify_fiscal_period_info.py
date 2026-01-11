from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page

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

@register_action('modify_fiscal_period_info')
@register_command('modify_fiscal_period_info')
def modify_fiscal_period_info() -> bool:
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
        if not gateway.is_set('startDate'):
            warn("No start date provided")
            report_error("action", "Start date is required")
    if not is_error():
        if not gateway.is_set('endDate'):
            warn("No end date provided")
            report_error("action", "End date is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        start_date = gateway.get_arg('startDate')
        end_date = gateway.get_arg('endDate')
        # Handle the case where flags are passed (returns True)
        if start_date is True:
            start_date = ""
        if end_date is True:
            end_date = ""
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        # Validate date formats (YYYY-MM-DD)
        if start_date and start_date.strip():
            try:
                from datetime import datetime
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                warn(f"Invalid start date format: '{start_date}'. Expected YYYY-MM-DD")
                report_error("action", f"Invalid start date format: '{start_date}'. Expected YYYY-MM-DD")
    if not is_error():
        if end_date and end_date.strip():
            try:
                from datetime import datetime
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                warn(f"Invalid end date format: '{end_date}'. Expected YYYY-MM-DD")
                report_error("action", f"Invalid end date format: '{end_date}'. Expected YYYY-MM-DD")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} fiscal period info: startDate={start_date}, endDate={end_date}")
        success = page.modify_fiscal_period_info(start_date, end_date)
        if not success:
            warn("Page fiscal period info modification failed")
            report_error("action", "Page fiscal period info modification failed")
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} fiscal period info with {total_children} children")
    trace_out()
    return not is_error()


