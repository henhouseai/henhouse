from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from ext.currency_math import DecimalMath

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

@register_action('modify_finance_info')
@register_command('modify_finance_info')
def modify_finance_info() -> bool:
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
        if not gateway.is_set('interestEarned'):
            warn("No interest earned provided")
            report_error("action", "Interest earned is required")
    if not is_error():
        if not gateway.is_set('financeCharge'):
            warn("No finance charge provided")
            report_error("action", "Finance charge is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        interest_earned_arg = gateway.get_arg('interestEarned')
        finance_charge_arg = gateway.get_arg('financeCharge')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        # Validate and normalize interest earned
        try:
            interest_earned = DecimalMath.normalize(str(interest_earned_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            interest_value = DecimalMath._string_to_units(interest_earned)
            if interest_value < -99999999 or interest_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Interest earned out of range: {interest_earned}")
                report_error("action", f"Interest earned must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid interest earned: {interest_earned_arg}")
            report_error("action", "Interest earned must be a valid currency value")
    if not is_error():
        # Validate and normalize finance charge
        try:
            finance_charge = DecimalMath.normalize(str(finance_charge_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            finance_value = DecimalMath._string_to_units(finance_charge)
            if finance_value < -99999999 or finance_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Finance charge out of range: {finance_charge}")
                report_error("action", f"Finance charge must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid finance charge: {finance_charge_arg}")
            report_error("action", "Finance charge must be a valid currency value")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} finance info: interestEarned={interest_earned}, financeCharge={finance_charge}")
        success = page.modify_finance_info(interest_earned, finance_charge)
        if not success:
            warn("Page finance info modification failed")
            report_error("action", "Page finance info modification failed")
        if not is_error() and hasattr(page, 'recalculateGeneratedValues'):
            page.recalculateGeneratedValues()
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} finance info with {total_children} children")
    trace_out()
    return not is_error()

