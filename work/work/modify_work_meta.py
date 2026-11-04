from __future__ import annotations
from typing import Dict, Any
import json
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

@register_action('modify_work_meta')
@register_command('modify_work_meta')
def modify_work_meta() -> bool:
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
        if not gateway.is_set('action'):
            warn("No action provided")
            report_error("action", "Action is required")
    if not is_error():
        action = gateway.get_arg('action')
        valid_actions = ['add', 'remove', 'set', 'set_all']
        if action not in valid_actions:
            warn(f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}")
            report_error("action", f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}")
    if not is_error():
        field = gateway.get_arg('field') or 'meta'
    if not is_error():
        # For remove action, expect keys (array); for others, expect data (dict)
        if action == 'remove':
            if not gateway.is_set('keys'):
                warn("No keys provided")
                report_error("action", "Keys is required for remove action")
        else:
            if not gateway.is_set('data'):
                warn("No data provided")
                report_error("action", "Data is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    data_dict = None
    keys_list = None
    if not is_error():
        # Parse keys (for remove) or data (for others)
        if action == 'remove':
            keys_json = gateway.get_arg('keys')
            try:
                keys_list = json.loads(keys_json)
                if not isinstance(keys_list, list):
                    warn("Keys must be a JSON array")
                    report_error("action", "Keys must be a JSON array")
            except json.JSONDecodeError as exc:
                warn(f"Invalid JSON for keys: {exc}")
                report_error("action", f"Invalid JSON for keys: {exc}")
        else:
            data_json = gateway.get_arg('data')
            try:
                data_dict = json.loads(data_json)
                if not isinstance(data_dict, dict):
                    warn("Data must be a JSON object")
                    report_error("action", "Data must be a JSON object")
            except json.JSONDecodeError as exc:
                warn(f"Invalid JSON for data: {exc}")
                report_error("action", f"Invalid JSON for data: {exc}")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error():
        if page:
            if page.class_name not in ['work_docket', 'ask', 'task', 'step']:
                warn(f"Page {page_id} is not a WorkPage (class: {page.class_name})")
                report_error("action", f"Page {page_id} is not a WorkPage")
    success = False
    response_data = None
    if not is_error():
        if action == 'add':
            if field == 'log':
                log(f"Adding log entry for page {page_id}")
                if page:
                    success = page.work_add_log(data_dict)
            else:
                log(f"Adding to {field} for page {page_id}")
                if page:
                    success = page.work_add(data_dict, field)
        elif action == 'remove':
            log(f"Removing from {field} for page {page_id}")
            if page:
                success = page.work_remove(keys_list, field)
        elif action == 'set':
            log(f"Setting {field} for page {page_id}")
            if page:
                success = page.work_set(data_dict, field)
        elif action == 'set_all':
            log(f"Setting all {field} for page {page_id}")
            if page:
                success = page.work_set_all(data_dict, field)
        else:
            warn(f"Unknown action: {action}")
            report_error("action", f"Unknown action: {action}")
            success = False
    if not is_error():
        if page:
            if not success:
                warn(f"Page {action} failed")
                report_error("action", f"Page {action} failed")

            # Check for response mode flags
            full_page = gateway.is_set('full_page')
            full_meta = gateway.is_set('full_meta')

            if full_page:
                # Mode 3: full_page - return complete show_page() data
                response_data = page.show_page()
                gateway.response.set_action_response(success_payload(response_data))
                log(f"Successfully executed {action} on {field} for page {page_id} (full_page mode)")
            elif full_meta:
                # Mode 2: full_meta - return specific metadata bucket
                metadata = page._get_metadata_dict()
                response_data = {
                    "page_id": page_id,
                    "action": action,
                    "field": field,
                    "success": success,
                    "metadata": metadata.get(field, {})
                }
                gateway.response.set_action_response(success_payload(response_data))
                log(f"Successfully executed {action} on {field} for page {page_id} (full_meta mode)")
            else:
                # Mode 1: summary (default) - return condensed summary
                # Generate operation summary dynamically
                if action == 'add':
                    if field == 'log':
                        operation_summary = "Added 1 log entry"
                    else:
                        count = len(data_dict.keys()) if data_dict else 0
                        operation_summary = f"Added {count} {field} {'entry' if count == 1 else 'entries'}"
                elif action == 'remove':
                    count = len(keys_list) if keys_list else 0
                    operation_summary = f"Removed {count} {field} {'key' if count == 1 else 'keys'}"
                elif action == 'set':
                    count = len(data_dict.keys()) if data_dict else 0
                    operation_summary = f"Set {count} {field} {'key' if count == 1 else 'keys'}"
                elif action == 'set_all':
                    count = len(data_dict.keys()) if data_dict else 0
                    operation_summary = f"Replaced {field} with {count} {'entry' if count == 1 else 'entries'}"
                else:
                    operation_summary = f"Performed {action} on {field}"

                response_data = {
                    "page_id": page_id,
                    "action": action,
                    "field": field,
                    "success": success,
                    "operation_summary": operation_summary
                }
                gateway.response.set_action_response(success_payload(response_data))
                log(f"Successfully executed {action} on {field} for page {page_id} (summary mode)")
    trace_out()
    return not is_error()


@register_parser('modify_work_meta')
def parser_modify_work_meta() -> bool:
    """
    Dedicated parser for modify_work_meta action.
    Supports 3 modes: summary (default), full_meta, full_page.
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

    # Check for full_page mode - delegate to show_page parser
    if gateway.is_set('full_page'):
        from hh_page.render_show_page import show_page as parser_show_page
        return parser_show_page()

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data) if json_data and isinstance(json_data, dict) else {}

        lines = [render_header_block("l_modify_work_meta_header")]

        # Check if this is full_meta mode (has 'metadata' field)
        is_full_meta = 'metadata' in source_data

        if is_full_meta:
            # Full metadata mode - show metadata content
            table = TableData()
            table.add_row("page_id", value=str(source_data.get("page_id", "")))
            table.add_row("work_meta_action", value=source_data.get("action", ""))
            table.add_row("work_meta_field", value=source_data.get("field", ""))
            table.add_row("work_meta_success", value=str(source_data.get("success", False)))

            # Format metadata display
            metadata = source_data.get("metadata", {})
            if metadata:
                metadata_str = json.dumps(metadata, indent=2)
                table.add_row("work_meta_content", value=metadata_str)

            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_simple(["page_id", "work_meta_action", "work_meta_field", "work_meta_success", "work_meta_content"]),
                    block_type="work_meta",
                    table_overrides={"margin_l": 4},
                )
            )
        else:
            # Summary mode - show operation summary
            table = TableData()
            table.add_row("page_id", value=str(source_data.get("page_id", "")))
            table.add_row("work_meta_action", value=source_data.get("action", ""))
            table.add_row("work_meta_field", value=source_data.get("field", ""))
            table.add_row("work_meta_success", value=str(source_data.get("success", False)))
            table.add_row("work_meta_operation_summary", value=source_data.get("operation_summary", ""))

            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_simple(["page_id", "work_meta_action", "work_meta_field", "work_meta_success", "work_meta_operation_summary"]),
                    block_type="work_meta",
                    table_overrides={"margin_l": 4},
                )
            )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        return trace_out(True)

    except Exception as exc:
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        return trace_out(False)
