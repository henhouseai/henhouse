from __future__ import annotations

import json
from typing import Any, Dict

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.response.json_standard import success_payload
from hh.page.page_registry import get_page


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


def _extract_json_arg(gateway, arg_name: str):
    if not gateway.is_set(arg_name):
        return None
    value = gateway.get_arg(arg_name)
    if value is None:
        return None
    try:
        json.loads(value)
        return value
    except (TypeError, ValueError):
        warn(f"Invalid JSON supplied for {arg_name}")
        report_error("action", f"Invalid JSON for {arg_name}")
        return None


def _extract_bool_arg(gateway, arg_name: str):
    if not gateway.is_set(arg_name):
        return None
    value = gateway.get_arg(arg_name)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'y'}:
            return True
        if normalized in {'0', 'false', 'no', 'n'}:
            return False
    warn(f"Invalid boolean supplied for {arg_name}: {value}")
    report_error("action", f"Invalid boolean for {arg_name}")
    return None


@register_action('modify_mcp_action_request')
@register_command('modify_mcp_action_request')
def modify_mcp_action_request() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
    if not page_id_arg:
        warn("Page ID is required")
        report_error("action", "Page ID is required")
    else:
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
            page_id = None

    page = None
    if not is_error() and page_id is not None:
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")

    if is_error():
        trace_out()
        return False

    update_kwargs: Dict[str, Any] = {
        "tool_name": gateway.get_arg('tool_name') if gateway.is_set('tool_name') else None,
        "arguments": _extract_json_arg(gateway, 'arguments'),
        "extraction_spec": _extract_json_arg(gateway, 'extraction_spec'),
        "status": gateway.get_arg('status') if gateway.is_set('status') else None,
        "result": _extract_json_arg(gateway, 'result'),
        "is_create": _extract_bool_arg(gateway, 'is_create'),
        "is_read": _extract_bool_arg(gateway, 'is_read'),
        "is_update": _extract_bool_arg(gateway, 'is_update'),
        "is_delete": _extract_bool_arg(gateway, 'is_delete'),
    }

    if not any(value is not None for value in update_kwargs.values()):
        warn("No MCP action request fields specified to modify")
        report_error("action", "No MCP action request fields specified")

    if not is_error() and page is not None:
        success = page.update_action_request(**update_kwargs)
        if not success:
            warn("Failed to update MCP action request")
            report_error("action", "Failed to update MCP action request")
        else:
            response = page.show_page()
            gateway.response.set_action_response(success_payload(response))
            total_children = sum(
                len(group.get('children', []))
                for group in response.get('children_by_class', {}).values()
            )
            log(f"Modified MCP action request {page_id} (children: {total_children})")

    trace_out()
    return not is_error()

