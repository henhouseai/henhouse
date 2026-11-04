from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh_page.page_registry import get_page
from accounting.currency_math import DecimalMath

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

@register_action('modify_transfer_info')
@register_command('modify_transfer_info')
def modify_transfer_info() -> bool:
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
        if not gateway.is_set('amount'):
            warn("No amount provided")
            report_error("action", "Amount is required")
    if not is_error():
        if not gateway.is_set('fee'):
            warn("No fee provided")
            report_error("action", "Fee is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        date = gateway.get_arg('date')
        amount_arg = gateway.get_arg('amount')
        modifier_arg = gateway.get_arg('modifier')
        fee_arg = gateway.get_arg('fee')
        # Handle the case where -date is passed as a flag (returns True) or not provided
        if date is True:
            date = ""
        if date is None:
            date = ""
        # Handle modifier - default to 0 if not provided
        if modifier_arg is None:
            modifier_arg = '0'
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        # Validate date format (YYYY-MM-DD) if provided
        if date and date.strip():
            try:
                from datetime import datetime
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                warn(f"Invalid date format: '{date}'. Expected YYYY-MM-DD")
                report_error("action", f"Invalid date format: '{date}'. Expected YYYY-MM-DD")
    if not is_error():
        # Validate and normalize amount
        try:
            amount = DecimalMath.normalize(str(amount_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            amount_value = DecimalMath._string_to_units(amount)
            if amount_value < -99999999 or amount_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Amount out of range: {amount}")
                report_error("action", f"Amount must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid amount: {amount_arg}")
            report_error("action", "Amount must be a valid currency value")
    if not is_error():
        # Validate and normalize modifier
        try:
            modifier = DecimalMath.normalize(str(modifier_arg))
        except (ValueError, TypeError):
            warn(f"Invalid modifier: {modifier_arg}")
            report_error("action", "Modifier must be a valid currency value")
    if not is_error():
        # Validate and normalize fee
        try:
            fee = DecimalMath.normalize(str(fee_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            fee_value = DecimalMath._string_to_units(fee)
            if fee_value < -99999999 or fee_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Fee out of range: {fee}")
                report_error("action", f"Fee must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid fee: {fee_arg}")
            report_error("action", "Fee must be a valid currency value")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} transfer info: date={date}, amount={amount}, modifier={modifier}, fee={fee}")
        success = page.modify_transfer_info(date, amount, modifier, fee)
        if not success:
            warn("Page transfer info modification failed")
            report_error("action", "Page transfer info modification failed")
        if not is_error() and hasattr(page, 'recalculateGeneratedValues'):
            page.recalculateGeneratedValues()
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} transfer info with {total_children} children")
    trace_out()
    return not is_error()

