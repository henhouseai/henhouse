from __future__ import annotations

from typing import Any, Dict, List

from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.registry.registry import register_parser
from hh.gateway.response.json_standard import get_data
from hh.render.config.config import break_section, safe_str
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block

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


def _render_summary_table(source_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    table = TableData()
    table.add_row(
        "rebuild_cache_summary_header",
        target="target",
        processed="processed",
        remaining="remaining",
    )
    rows = [
        ("Pages", source_data.get("pages_processed", 0), source_data.get("pages_remaining", 0)),
        ("Images", source_data.get("images_processed", 0), source_data.get("images_remaining", 0)),
    ]
    for label, processed, remaining in rows:
        table.add_row(
            "rebuild_cache_summary_row",
            target=label,
            processed=str(processed),
            remaining=str(remaining),
        )
    lines.append(
        render_block(
            table,
            FieldConfig().add_header("rebuild_cache_summary_header").add_simple(["rebuild_cache_summary_row"]),
            table_overrides={"margin_l": 4},
            block_type="rows",
        )
    )
    break_section(lines)
    trace_out()


def _render_details_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    details = TableData()
    details.add_row("rebuild_cache_details_header", label="detail", value="value")
    items = {
        "Cache DB": source_data.get("cache_database", ""),
        "Limit": source_data.get("limit", 0),
        "Processed Pages": ", ".join(str(i) for i in source_data.get("processed_page_ids", [])) or "None",
        "Processed Images": ", ".join(str(i) for i in source_data.get("processed_image_ids", [])) or "None",
        "Errors": str(len(source_data.get("errors", []))),
    }
    for label, value in items.items():
        details.add_row("rebuild_cache_details_row", label=safe_str(label), value=safe_str(str(value)))
    lines.append(
        render_block(
            details,
            FieldConfig().add_header("rebuild_cache_details_header").add_simple(["rebuild_cache_details_row"]),
            table_overrides={"margin_l": 4},
            block_type="rows",
        )
    )
    break_section(lines)
    trace_out()


def _render_errors_section(source_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    errors = source_data.get("errors") or []
    if not errors:
        trace_out()
        return
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    table = TableData()
    table.add_row("rebuild_cache_errors_header", entity="entity", identifier="id", message="message")
    for entry in errors:
        table.add_row(
            "rebuild_cache_errors_row",
            entity=safe_str(entry.get("entity", "unknown")),
            identifier=safe_str(str(entry.get("id", "n/a"))),
            message=safe_str(entry.get("error", "unknown error")),
        )
    lines.append(
        render_block(
            table,
            FieldConfig().add_header("rebuild_cache_errors_header").add_simple(["rebuild_cache_errors_row"]),
            table_overrides={"margin_l": 4},
            block_type="rows",
        )
    )
    break_section(lines)
    trace_out()


@register_parser("rebuild_cache")
def rebuild_cache_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    payload = gateway.response.get_action_response()
    source_data = get_data(payload)
    lines: List[str] = []
    lines.append(render_header_block("l_rebuild_cache_header"))
    _render_summary_table(source_data, lines)
    _render_details_section(source_data, lines)
    _render_errors_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log("Rendered rebuild_cache output successfully")
    trace_out()
    return True

