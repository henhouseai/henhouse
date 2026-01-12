from __future__ import annotations
from typing import Dict, Any, Optional
import json
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.image.image_registry import get_image
from hh.page.page import Page
from hh.image.image import Image
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


def is_valid_utf8(text: str) -> bool:
    """
    Validate that a string contains only valid UTF-8 encoded characters.
    Rejects strings with corrupted Unicode sequences, invalid encoding, or suspicious character patterns.
    """
    try:
        # First check: can it be encoded as UTF-8?
        text.encode('utf-8')

        # Second check: look for corrupted Unicode patterns
        # Common corruption patterns from emoji/Unicode transmission issues
        import re

        # Check for C1 control codes (often result of corruption)
        if re.search(r'[\x80-\x9f]', text):
            return False

        # Check for isolated combining characters (often corruption artifacts)
        # This catches cases where diacritics appear without base characters
        for i, char in enumerate(text):
            if '\u0300' <= char <= '\u036f':  # Combining Diacritical Marks block
                # Check if previous character exists and is a valid base
                if i == 0 or not text[i-1].isalnum():
                    return False

        # Check for sequences that look like corrupted multi-byte UTF-8
        # Pattern: Latin-1 supplement chars that shouldn't appear in normal text
        suspicious_byte_patterns = [
            b'[\xc2-\xc3][\x80-\xbf]{0,2}',  # Over-encoded UTF-8
            b'\xef\xbf\xbd',  # UTF-8 replacement character (�)
        ]

        encoded_text = text.encode('utf-8')
        for pattern in suspicious_byte_patterns:
            if re.search(pattern, encoded_text):
                return False

        return True

    except (UnicodeEncodeError, UnicodeDecodeError):
        return False

@register_action('modify_text')
@register_command('modify_text')
def modify_text() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set('text') and not gateway.is_set('new_string'):
            warn("No text or new_string parameter provided")
            report_error("action", "text or new_string parameter is required")
    page_id: int = 0
    new_text: str = ""
    mode: str = "replace_all"
    old_string: Optional[str] = None
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        new_text = gateway.get_arg('text')
        # Handle parameter aliasing: new_string as alias for text
        if not new_text:
            new_text = gateway.get_arg('new_string')
        # Handle the case where -text is passed as a flag (returns True)
        if new_text is True:
            new_text = ""
        # Validate UTF-8 encoding to prevent corrupted character sequences
        if not is_valid_utf8(new_text):
            warn("Text contains invalid UTF-8 encoding or corrupted character sequences")
            report_error("action", "Text contains invalid UTF-8 encoding or corrupted character sequences")
        # Get optional mode parameter (defaults to replace_all)
        mode_arg = gateway.get_arg('mode')
        if mode_arg:
            mode = str(mode_arg)
        # Get optional old_string parameter (required for replace mode)
        old_string_arg = gateway.get_arg('old_string')
        if old_string_arg:
            old_string = str(old_string_arg)
            # Validate UTF-8 encoding for old_string too
            if not is_valid_utf8(old_string):
                warn("old_string contains invalid UTF-8 encoding or corrupted character sequences")
                report_error("action", "old_string contains invalid UTF-8 encoding or corrupted character sequences")
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    page = None
    old_text = ""
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
        else:
            # Capture old text for delta calculations
            old_text = page.text or ""
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} text content (mode: {mode})")
        success = page.modify_text(new_text, mode=mode, old_string=old_string)
        if not success:
            warn("Page text modification failed")
            report_error("action", "Page text modification failed")
    if not is_error() and page is not None:
        # Check which response format to return
        full_page = gateway.is_set('full_page') or gateway.is_set('return_full_page')
        full_text = gateway.is_set('full_text') or gateway.is_set('return_full_text')

        if full_page:
            # Return full page object (for HTTP TypeScript UI)
            response_data = page.show_page()
            gateway.response.set_action_response(success_payload(response_data))
            log(f"Successfully modified page {page_id} text (full_page mode)")
        elif full_text:
            # Return just the updated text (for agents who need the content)
            response_data = {
                "page_id": page_id,
                "text": page.text or ""
            }
            gateway.response.set_action_response(success_payload(response_data))
            log(f"Successfully modified page {page_id} text (full_text mode)")
        else:
            # Default: return summary stats (minimal data transfer for agents)
            lines_before = old_text.count('\n') + 1 if old_text else 0
            lines_after = (page.text.count('\n') + 1) if page.text else 0
            chars_before = len(old_text)
            chars_after = len(page.text) if page.text else 0

            response_data = {
                "page_id": page_id,
                "summary": f"Modified page {page_id} text",
                "mode": mode,
                "lines_before": lines_before,
                "lines_after": lines_after,
                "chars_before": chars_before,
                "chars_after": chars_after,
                "delta_lines": lines_after - lines_before,
                "delta_chars": chars_after - chars_before
            }
            gateway.response.set_action_response(success_payload(response_data))
            log(f"Successfully modified page {page_id} text (summary mode)")
    trace_out()
    return not is_error()


@register_parser('modify_text')
def parser_modify_text() -> bool:
    """
    Dedicated parser for modify_text action.
    Delegates to show_page parser when full_page mode is requested,
    otherwise formats output using TableData for agent consumption.
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

    # Check for full_page flag
    if gateway.is_set('full_page') or gateway.is_set('return_full_page'):
        # Lazy import and delegate to show_page parser
        from hh.page.render_show_page import show_page as parser_show_page
        return parser_show_page()

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data) if json_data and isinstance(json_data, dict) else {}

        lines = [render_header_block("l_modify_text_header")]

        # Check if this is full_text mode (has 'text' field but no 'mode' field)
        is_full_text = 'text' in source_data and 'mode' not in source_data

        if is_full_text:
            # Full text mode: show page_id and text
            table = TableData()
            table.add_row(
                "page_id",
                value=str(source_data.get("page_id", "")),
            )
            table.add_row(
                "page_text",
                value=source_data.get("text", ""),
            )

            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_simple(["page_id", "page_text"]),
                    block_type="page",
                    table_overrides={"margin_l": 4},
                )
            )
        else:
            # Summary mode: show statistics in 2-column format
            table = TableData()
            table.add_row(
                "page_id",
                value=str(source_data.get("page_id", "")),
            )
            table.add_row(
                "summary",
                value=source_data.get("summary", ""),
            )
            table.add_row(
                "mode",
                value=source_data.get("mode", ""),
            )
            table.add_row(
                "lines_before",
                value=str(source_data.get("lines_before", 0)),
            )
            table.add_row(
                "lines_after",
                value=str(source_data.get("lines_after", 0)),
            )
            table.add_row(
                "delta_lines",
                value=str(source_data.get("delta_lines", 0)),
            )
            table.add_row(
                "chars_before",
                value=str(source_data.get("chars_before", 0)),
            )
            table.add_row(
                "chars_after",
                value=str(source_data.get("chars_after", 0)),
            )
            table.add_row(
                "delta_chars",
                value=str(source_data.get("delta_chars", 0)),
            )

            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_simple(["page_id", "summary", "mode", "lines_before", "lines_after", "delta_lines", "chars_before", "chars_after", "delta_chars"]),
                    block_type="page",
                    table_overrides={"margin_l": 4},
                )
            )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        return trace_out(True)

    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        return trace_out(False)
