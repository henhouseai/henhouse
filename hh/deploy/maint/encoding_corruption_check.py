"""Encoding corruption check module for maintenance daemon and manual runs."""

from __future__ import annotations

from typing import Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.page.page_registry import get_page
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message=None: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


# Known corruption patterns mapping corrupted sequences to correct Unicode
CORRUPTION_PATTERNS = {
    "â†’": "→"
}


def detect_corruption_in_text(text: str) -> list[str]:
    """Detect known corruption patterns in text."""
    found_patterns = []
    # Sort patterns by length (longest first) to avoid partial matches
    sorted_patterns = sorted(CORRUPTION_PATTERNS.keys(), key=len, reverse=True)

    # First, find all known corruption patterns
    for corrupted in sorted_patterns:
        if corrupted in text:
            found_patterns.append(corrupted)

    # Additionally, investigate sequences starting with known corruption characters
    # that extend until whitespace, treating them as potentially longer corrupted sequences
    extended_patterns = []
    for pattern in sorted_patterns:
        start_pos = 0
        while True:
            # Find the next occurrence of this pattern
            pos = text.find(pattern, start_pos)
            if pos == -1:
                break

            # From this position, look backwards to find the start of the corrupted sequence
            # (any character that looks like it might be part of UTF-8 corruption)
            seq_start = pos
            for i in range(pos - 1, -1, -1):
                char = text[i]
                # Stop at whitespace or normal ASCII characters
                if char.isspace() or (ord(char) < 128 and char.isprintable() and char not in 'Ââ€'):
                    break
                seq_start = i

            # From the pattern end, look forwards until whitespace
            seq_end = pos + len(pattern)
            for i in range(pos + len(pattern), len(text)):
                char = text[i]
                # Stop at whitespace
                if char.isspace():
                    break
                seq_end = i + 1

            # Extract the extended sequence
            extended_seq = text[seq_start:seq_end]
            if len(extended_seq) > len(pattern) and extended_seq not in found_patterns and extended_seq not in extended_patterns:
                extended_patterns.append(extended_seq)

            start_pos = pos + 1

    return found_patterns + extended_patterns


def check_pages_with_corruption() -> list[dict]:
    """Check for pages containing text encoding corruption patterns."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []

    # Build SQL query to find pages with corruption patterns
    where_clauses = []
    params = []

    for corrupted in CORRUPTION_PATTERNS.keys():
        where_clauses.append("text LIKE %s")
        params.append(f"%{corrupted}%")

    if not where_clauses:
        return []

    where_clause = ' OR '.join(where_clauses)
    query = "SELECT id, name, LENGTH(text) as text_length FROM pages WHERE " + where_clause + " ORDER BY id"

    rows = gateway.conn.read(query, params)

    # For each page, analyze the specific corruption patterns
    result = []
    for row in rows:
        page_id = row["id"]
        try:
            # Get the full page to analyze text content
            page = get_page(page_id)
            if page and hasattr(page, 'text') and page.text is not None:
                patterns_found: list[str] = detect_corruption_in_text(page.text)
                if patterns_found:
                    result.append({
                        "id": page_id,
                        "name": row["name"],
                        "text_length": row["text_length"],
                        "patterns_found": patterns_found,
                        "pattern_count": len(patterns_found)
                    })
        except Exception as exc:  # noqa: BLE001
            warn(f"Error analyzing page {page_id}: {exc}")
            continue

    return result


@register_action("encoding_corruption_check")
@register_command("encoding_corruption_check")
def encoding_corruption_check_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        corrupted_pages = check_pages_with_corruption()

        # Group by corruption patterns for summary
        pattern_summary: dict[str, dict[str, Any]] = {}
        page_summary: dict[int, dict[str, Any]] = {}

        for page in corrupted_pages:
            page_id = page["id"]
            patterns = page["patterns_found"]

            page_summary[page_id] = {
                "name": page["name"],
                "text_length": page["text_length"],
                "patterns_found": patterns,
                "pattern_count": len(patterns)
            }

            for pattern in patterns:
                if pattern not in pattern_summary:
                    correct_char = CORRUPTION_PATTERNS.get(pattern, "")
                    # DEBUG: Check why lookup fails for patterns we added
                    if pattern == "â†→":
                        debug(f"â†→ Pattern '{pattern}' (len={len(pattern)})")
                        debug(f"â†→ correct_char = '{correct_char}'")
                        debug(f"â†→ Dict has key: {'â†→' in CORRUPTION_PATTERNS}")
                        debug(f"â†→ Dict value: {CORRUPTION_PATTERNS.get('â†→', 'KEY_NOT_FOUND')}")
                    if pattern in ["â†→", "â†↓", "âœ…"] and not correct_char:
                        print(f"DEBUG: Pattern '{pattern}' (len={len(pattern)}) not found in dict")
                        print(f"DEBUG: Dict keys with â: {[k for k in CORRUPTION_PATTERNS.keys() if 'â' in k]}")
                        print(f"DEBUG: Pattern repr: {repr(pattern)}")
                        print(f"DEBUG: Dict entry repr: {repr(CORRUPTION_PATTERNS.get('â†→', 'NOT_FOUND'))}")
                    pattern_summary[pattern] = {
                        "correct_char": correct_char,
                        "pages_affected": [],
                        "total_occurrences": 0
                    }
                pattern_summary[pattern]["pages_affected"].append(page_id)
                # Count occurrences in the page text (rough estimate)
                page_obj = get_page(page_id)
                if page_obj and hasattr(page_obj, 'text') and page_obj.text is not None:
                    pattern_summary[pattern]["total_occurrences"] += page_obj.text.count(pattern)

        summary = {
            "total_corrupted_pages": len(corrupted_pages),
            "total_corruption_patterns": len(pattern_summary),
            "total_occurrences": sum(p["total_occurrences"] for p in pattern_summary.values())
        }

        log(f"Found {summary['total_corrupted_pages']} pages with encoding corruption across {summary['total_corruption_patterns']} patterns")

    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to run encoding corruption check: {exc}")
        report_error("action", f"Failed to run encoding corruption check: {exc}")
        trace_out()
        return False

    payload = {
        "operation": "encoding_corruption_check",
        "summary": summary,
        "pattern_summary": pattern_summary,
        "page_summary": page_summary,
    }
    gateway.response.set_action_response(success_payload(payload))
    log("Encoding corruption check completed successfully")
    trace_out()
    return not is_error()


@register_parser("encoding_corruption_check")
def encoding_corruption_check_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})
        summary = source_data.get("summary", {})
        pattern_summary = source_data.get("pattern_summary", {})
        page_summary = source_data.get("page_summary", {})

        lines = [render_header_block("l_encoding_corruption_check_header")]

        # Summary table
        summary_table = TableData()
        summary_table.add_row(
            "header",
            label="Encoding Corruption Summary",
            count="Count",
        )
        summary_table.add_row(
            "corrupted_pages",
            label="Pages with Corruption",
            count=str(summary.get("total_corrupted_pages", 0)),
        )
        summary_table.add_row(
            "corruption_patterns",
            label="Corruption Patterns Found",
            count=str(summary.get("total_corruption_patterns", 0)),
        )
        summary_table.add_row(
            "total_occurrences",
            label="Total Pattern Occurrences",
            count=str(summary.get("total_occurrences", 0)),
        )

        lines.append(
            render_block(
                summary_table,
                FieldConfig()
                .add_header("header")
                .add_simple(["corrupted_pages", "corruption_patterns", "total_occurrences"]),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        # Pattern details table
        if pattern_summary:
            lines.append(render_header_block("l_corruption_patterns_header"))

            pattern_table = TableData()
            pattern_table.add_row(
                "header",
                corrupted="Corrupted Sequence",
                correct="Correct Character",
                pages="Pages Affected",
                occurrences="Total Occurrences",
            )

            for corrupted, data in pattern_summary.items():
                pages_list = data.get("pages_affected", [])
                pages_preview = ", ".join(str(pid) for pid in pages_list[:10])
                if len(pages_list) > 10:
                    pages_preview += f" (+{len(pages_list) - 10} more)"

                pattern_table.add_row(
                    corrupted,
                    corrupted=f"'{corrupted}'",
                    correct=f"'{data.get('correct_char', '')}'",
                    pages=pages_preview,
                    occurrences=str(data.get("total_occurrences", 0)),
                )

            lines.append(
                render_block(
                    pattern_table,
                    FieldConfig()
                    .add_header("header")
                    .add_simple(["corrupted", "correct", "pages", "occurrences"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4},
                )
            )

        # Page details table
        if page_summary:
            lines.append(render_header_block("l_corrupted_pages_header"))

            page_table = TableData()
            page_table.add_row(
                "header",
                page_id="Page ID",
                name="Page Name",
                patterns="Corruption Patterns",
                pattern_count="Count",
            )

            for page_id, data in page_summary.items():
                patterns_str = ", ".join(f"'{p}'" for p in data.get("patterns_found", [])[:5])
                if len(data.get("patterns_found", [])) > 5:
                    patterns_str += f" (+{len(data['patterns_found']) - 5} more)"

                page_table.add_row(
                    str(page_id),
                    page_id=str(page_id),
                    name=data.get("name", ""),
                    patterns=patterns_str,
                    pattern_count=str(data.get("pattern_count", 0)),
                )

            lines.append(
                render_block(
                    page_table,
                    FieldConfig()
                    .add_header("header")
                    .add_simple(["page_id", "name", "patterns", "pattern_count"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4},
                )
            )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False


register_maintenance_tool("encoding_corruption_check")