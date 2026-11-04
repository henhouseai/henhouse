"""
Modify document info for Document pages.

Allows updating output_filename and output_format metadata fields.
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


@register_action('modify_document_info')
@register_command('modify_document_info')
def modify_document_info() -> bool:
    """
    Modify document metadata fields.
    Supports output_filename and output_format.
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
    output_filename = gateway.get_arg('output_filename')
    output_format = gateway.get_arg('output_format')

    # Validate at least one parameter provided
    if output_filename is None and output_format is None:
        warn("No fields to update provided")
        report_error("action", "At least one field (output_filename or output_format) must be provided")
        trace_out()
        return not is_error()

    # Validate output_format if provided
    if output_format is not None:
        valid_formats = ['markdown', 'html', 'json']
        if output_format not in valid_formats:
            warn(f"Invalid output_format '{output_format}'. Must be one of: {', '.join(valid_formats)}")
            report_error("action", f"Invalid output_format '{output_format}'. Must be one of: {', '.join(valid_formats)}")
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

    # Check if page is a Document
    if not hasattr(page, 'modify_document_info'):
        warn(f"Page {page_id} is not a Document (class: {page.__class__.__name__})")
        report_error("action", f"Page {page_id} is not a Document")
        trace_out()
        return not is_error()

    # Perform the modification
    log(f"Modifying document {page_id} info: output_filename={output_filename}, output_format={output_format}")
    success = page.modify_document_info(
        output_filename=output_filename,
        output_format=output_format
    )

    if not success:
        warn("Document info modification failed")
        report_error("action", "Document info modification failed")
        trace_out()
        return not is_error()

    # Build response data for parser
    response_data = {
        "page_id": page_id,
        "output_filename": getattr(page, 'output_filename', ''),
        "output_format": getattr(page, 'output_format', ''),
        "success": success
    }
    gateway.response.set_action_response(success_payload(response_data))

    log(f"Successfully modified document {page_id} info")

    trace_out()
    return not is_error()


@register_parser('modify_document_info')
def parser_modify_document_info() -> bool:
    """
    Parser for modify_document_info action.
    Shows document info changes in a clean format.
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

        lines = [render_header_block("modify_document_info_header")]

        # Main document info table
        table = TableData()
        table.add_row("page_id", value=str(source_data.get("page_id", "")))
        table.add_row("document_output_filename", value=source_data.get("output_filename", ""))
        table.add_row("document_output_format", value=source_data.get("output_format", ""))
        table.add_row("success", value=str(source_data.get("success", False)))

        lines.append(
            render_block(
                table,
                FieldConfig().add_simple([
                    "page_id", "document_output_filename", "document_output_format", "success"
                ]),
                block_type="document_info",
                table_overrides={"margin_l": 4}
            )
        )

        gateway.response.add_output(finalize_output(lines))

    except Exception as e:
        warn(f"Parser error in modify_document_info: {e}")
        report_error("backend", f"Parser error: {e}")

    trace_out()
    return not is_error()