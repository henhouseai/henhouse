"""
Modify doc section info for DocSection pages.

Allows updating section_level, sort_order, and section_type metadata fields.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh_page.page_registry import get_page
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

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


@register_action('modify_doc_section_info')
@register_command('modify_doc_section_info')
def modify_doc_section_info() -> bool:
    """
    Modify doc section metadata fields.
    Supports section_level, sort_order, and section_type.
    """
    trace_in()

    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Validate required page_id
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
        trace_out()
        return not is_error()

    page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
    try:
        page_id = int(page_id_arg)
    except ValueError:
        warn(f"Invalid page ID: {page_id_arg}")
        report_error("action", "Page ID must be a number")
        trace_out()
        return not is_error()

    # Get optional parameters
    section_level_arg = gateway.get_arg('section_level')
    sort_order_arg = gateway.get_arg('sort_order')
    section_type = gateway.get_arg('section_type')

    # Convert string arguments to appropriate types
    section_level = None
    sort_order = None

    if section_level_arg is not None:
        try:
            section_level = int(section_level_arg)
        except ValueError:
            warn(f"Invalid section_level: {section_level_arg}")
            report_error("action", "section_level must be a number")
            trace_out()
            return not is_error()

    if sort_order_arg is not None:
        try:
            sort_order = int(sort_order_arg)
        except ValueError:
            warn(f"Invalid sort_order: {sort_order_arg}")
            report_error("action", "sort_order must be a number")
            trace_out()
            return not is_error()

    # Validate at least one parameter provided
    if section_level is None and sort_order is None and section_type is None:
        warn("No fields to update provided")
        report_error("action", "At least one field (section_level, sort_order, or section_type) must be provided")
        trace_out()
        return not is_error()

    # Load and validate page
    log(f"Loading page {page_id}")
    page = get_page(page_id=page_id)
    if not page:
        warn(f"Page {page_id} not found")
        report_error("action", f"Page {page_id} not found")
        trace_out()
        return not is_error()

    # Check if page is a DocSection
    if not hasattr(page, 'modify_doc_section_info'):
        warn(f"Page {page_id} is not a DocSection (class: {page.__class__.__name__})")
        report_error("action", f"Page {page_id} is not a DocSection")
        trace_out()
        return not is_error()

    # Perform the modification
    log(f"Modifying doc section {page_id} info: section_level={section_level}, sort_order={sort_order}, section_type={section_type}")
    success = page.modify_doc_section_info(
        section_level=section_level,
        sort_order=sort_order,
        section_type=section_type
    )

    if not success:
        warn("Doc section info modification failed")
        report_error("action", "Doc section info modification failed")
        trace_out()
        return not is_error()

    # Build response data for parser
    response_data = {
        "page_id": page_id,
        "section_level": getattr(page, 'section_level', ''),
        "sort_order": getattr(page, 'sort_order', ''),
        "section_type": getattr(page, 'section_type', ''),
        "success": success
    }
    gateway.response.set_action_response(success_payload(response_data))

    log(f"Successfully modified doc section {page_id} info")

    trace_out()
    return not is_error()


@register_parser('modify_doc_section_info')
def parser_modify_doc_section_info() -> bool:
    """
    Parser for modify_doc_section_info action.
    Shows doc section info changes in a clean format.
    """
    trace_in()

    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        return trace_out(False)

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        return trace_out(False)

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data) if json_data and isinstance(json_data, dict) else {}

        lines = [render_header_block("modify_doc_section_info_header")]

        # Main doc section info table
        table = TableData()
        table.add_row("page_id", value=str(source_data.get("page_id", "")))
        table.add_row("doc_section_level", value=str(source_data.get("section_level", "")))
        table.add_row("doc_section_sort_order", value=str(source_data.get("sort_order", "")))
        table.add_row("doc_section_type", value=source_data.get("section_type", ""))
        table.add_row("success", value=str(source_data.get("success", False)))

        lines.append(
            render_block(
                table,
                FieldConfig().add_simple([
                    "page_id", "doc_section_level", "doc_section_sort_order", "doc_section_type", "success"
                ]),
                block_type="doc_section_info",
                table_overrides={"margin_l": 4}
            )
        )

        gateway.response.add_output(finalize_output(lines))

    except Exception as e:
        warn(f"Parser error in modify_doc_section_info: {e}")
        report_error("backend", f"Parser error: {e}")

    trace_out()
    return not is_error()