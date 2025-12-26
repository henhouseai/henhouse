from __future__ import annotations
from typing import Dict, Any
import json
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
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
            response_data = page.show_page()
            gateway.response.set_action_response(success_payload(response_data))
    if not is_error() and response_data:
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully executed {action} on {field} for page {page_id} with {total_children} children")
    trace_out()
    return not is_error()

