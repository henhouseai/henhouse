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

@register_action('modify_customer_info')
@register_command('modify_customer_info')
def modify_customer_info() -> bool:
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
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        customer_name = gateway.get_arg('customerName')
        address = gateway.get_arg('address')
        city = gateway.get_arg('city')
        state = gateway.get_arg('state')
        postal_code = gateway.get_arg('postalCode')
        country = gateway.get_arg('country')
        # Handle the case where flags are passed (returns True) or not provided
        if customer_name is True:
            customer_name = None
        if customer_name == '':
            customer_name = None
        if address is True:
            address = None
        if address == '':
            address = None
        if city is True:
            city = None
        if city == '':
            city = None
        if state is True:
            state = None
        if state == '':
            state = None
        if postal_code is True:
            postal_code = None
        if postal_code == '':
            postal_code = None
        if country is True:
            country = None
        if country == '':
            country = None
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} customer info: customerName={customer_name}, address={address}, city={city}, state={state}, postalCode={postal_code}, country={country}")
        success = page.modify_customer_info(customer_name, address, city, state, postal_code, country)
        if not success:
            warn("Page customer info modification failed")
            report_error("action", "Page customer info modification failed")
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} customer info with {total_children} children")
    trace_out()
    return not is_error()

