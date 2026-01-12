from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
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

@register_action('modify_invoice_cost_breakdown')
@register_command('modify_invoice_cost_breakdown')
def modify_invoice_cost_breakdown() -> bool:
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
        if not gateway.is_set('total'):
            warn("No total provided")
            report_error("action", "Total is required")
    if not is_error():
        if not gateway.is_set('tax'):
            warn("No tax provided")
            report_error("action", "Tax is required")
    if not is_error():
        if not gateway.is_set('shipping'):
            warn("No shipping provided")
            report_error("action", "Shipping is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        total_arg = gateway.get_arg('total')
        tax_arg = gateway.get_arg('tax')
        shipping_arg = gateway.get_arg('shipping')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        # Validate and normalize total
        try:
            total = DecimalMath.normalize(str(total_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            total_value = DecimalMath._string_to_units(total)
            if total_value < -99999999 or total_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Total out of range: {total}")
                report_error("action", f"Total must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid total: {total_arg}")
            report_error("action", "Total must be a valid currency value")
    if not is_error():
        # Validate and normalize tax
        try:
            tax = DecimalMath.normalize(str(tax_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            tax_value = DecimalMath._string_to_units(tax)
            if tax_value < -99999999 or tax_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Tax out of range: {tax}")
                report_error("action", f"Tax must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid tax: {tax_arg}")
            report_error("action", "Tax must be a valid currency value")
    if not is_error():
        # Validate and normalize shipping
        try:
            shipping = DecimalMath.normalize(str(shipping_arg))
            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            shipping_value = DecimalMath._string_to_units(shipping)
            if shipping_value < -99999999 or shipping_value > 99999999:  # -999999.99 to 999999.99 in cents
                warn(f"Shipping out of range: {shipping}")
                report_error("action", f"Shipping must be between -999999.99 and 999999.99")
        except (ValueError, TypeError):
            warn(f"Invalid shipping: {shipping_arg}")
            report_error("action", "Shipping must be a valid currency value")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} cost breakdown: total={total}, tax={tax}, shipping={shipping}")
        success = page.modify_invoice_cost_breakdown(total, tax, shipping)
        if not success:
            warn("Page cost breakdown modification failed")
            report_error("action", "Page cost breakdown modification failed")
        if not is_error() and hasattr(page, 'recalculateGeneratedValues'):
            page.recalculateGeneratedValues()
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} cost breakdown with {total_children} children")
    trace_out()
    return not is_error()

