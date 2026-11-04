from __future__ import annotations
from typing import Dict, Any, Optional
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

# Valid recipient classes for transfers
VALID_TRANSFER_RECIPIENTS = ['statement', 'sale', 'invoice']

@register_action('modify_target_info')
@register_command('modify_target_info')
def modify_target_info() -> bool:
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
        if not gateway.is_set('transfer_to'):
            warn("No transfer_to provided")
            report_error("action", "Transfer to is required (pass empty string to clear)")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        transfer_to_arg = gateway.get_arg('transfer_to')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        # Handle empty string as None (clearing the transfer)
        # Convert to string first to handle any type
        transfer_to_str = str(transfer_to_arg) if transfer_to_arg is not None else ''
        transfer_to_value = None
        if transfer_to_str.strip():  # Only process if not empty/whitespace
            try:
                transfer_to_value = int(transfer_to_str)
            except (ValueError, TypeError):
                warn(f"Invalid transfer_to page ID: {transfer_to_arg}")
                report_error("action", "Transfer to page ID must be a number or empty string to clear")
    if not is_error() and transfer_to_value is not None:
        # Validate that the target page exists and is a valid recipient
        log(f"Validating transfer target page {transfer_to_value}")
        target_page = get_page(page_id=transfer_to_value)
        if not target_page:
            warn(f"Transfer target page {transfer_to_value} not found")
            report_error("action", f"Transfer target page {transfer_to_value} not found")
        elif not hasattr(target_page, 'class_name') or target_page.class_name not in VALID_TRANSFER_RECIPIENTS:
            target_class = getattr(target_page, 'class_name', 'unknown')
            warn(f"Invalid transfer target class: '{target_class}'. Must be one of: {', '.join(VALID_TRANSFER_RECIPIENTS)}")
            report_error("action", f"Invalid transfer target class: '{target_class}'. Must be one of: {', '.join(VALID_TRANSFER_RECIPIENTS)}")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error() and page is not None:
        # Get old transferTo before updating (to recalculate it later)
        old_transfer_to = getattr(page, 'transferTo', None)
        
        log(f"Modifying page {page_id} transfer_to to '{transfer_to_value}'")
        success = page.modify_target_info(transfer_to_value)
        if not success:
            warn("Page transfer_to modification failed")
            report_error("action", "Page transfer_to modification failed")
        
        # Recalculate affected pages (matching legacy behavior)
        if not is_error():
            # Recalculate parent page
            if page.parent:
                parent_page = get_page(page.parent)
                if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                    parent_page.recalculateGeneratedValues()
            
            # Recalculate new transferTo page (if set)
            if transfer_to_value:
                new_transfer_to_page = get_page(transfer_to_value)
                if new_transfer_to_page and hasattr(new_transfer_to_page, 'recalculateGeneratedValues'):
                    new_transfer_to_page.recalculateGeneratedValues()
            
            # Recalculate old transferTo page (if it exists and is different from new)
            if old_transfer_to and old_transfer_to != transfer_to_value:
                old_transfer_to_page = get_page(old_transfer_to)
                if old_transfer_to_page and hasattr(old_transfer_to_page, 'recalculateGeneratedValues'):
                    old_transfer_to_page.recalculateGeneratedValues()
        
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} transfer_to to '{transfer_to_value}' with {total_children} children")
    trace_out()
    return not is_error()

