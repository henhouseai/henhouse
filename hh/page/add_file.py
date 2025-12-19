from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.file.file_registry import get_file
from hh.page.page import Page
from hh.file.file import File
import os
from pathlib import Path

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

@register_action('add_file')
@register_command('add_file')
def add_file() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('target_page') and not gateway.is_set('t_page') and not gateway.is_set('id'):
        warn("No target parent ID provided")
        report_error("action", "Target parent ID is required")
    if not is_error():
        if not gateway.is_set('file'):
            warn("No file path provided")
            report_error("action", "File path is required")
    target_page_id: int = 0
    file_path: str = ""
    if not is_error():
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page') or gateway.get_arg('id')
        file_path = gateway.get_arg('file')
        # Validate file exists
        if not Path(file_path).exists():
            warn(f"File not found: {file_path}")
            report_error("action", f"File not found: {file_path}")
        elif not os.access(file_path, os.R_OK):
            warn(f"File not readable: {file_path}")
            report_error("action", f"File not readable: {file_path}")
    if not is_error():
        try:
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid target parent ID: {target_page_arg}")
            report_error("action", "Target parent ID must be a number")
    parent_page = None
    if not is_error():
        log(f"Loading parent page {target_page_id}")
        parent_page = get_page(page_id=target_page_id)
        if not parent_page:
            warn(f"Parent page {target_page_id} not found")
            report_error("action", f"Parent page {target_page_id} not found")
    new_file_id: int | None = None
    if not is_error() and parent_page is not None:
        description = gateway.get_arg('description') or gateway.get_arg('caption')
        # Use filename as default description if no description provided
        if not description:
            description = Path(file_path).stem  # Get filename without extension
            log(f"Using filename as description: {description}")
        
        log(f"Adding file '{description}' to page {target_page_id}")
        # Use file_path as both temp_path and original_filename
        new_file_id = parent_page.add_file(file_path, Path(file_path).name, description)
        file_created = not is_error() and new_file_id is not None
        if not file_created:
            warn("File creation failed")
            report_error("action", "File creation failed")
    updated_page = None
    if not is_error():
        log(f"Reloading parent page {target_page_id} to show new file")
        updated_page = get_page(page_id=target_page_id)
        if not updated_page or updated_page.name is None:
            warn(f"Failed to reload parent page {target_page_id}")
            report_error("action", f"Failed to reload parent page {target_page_id}")
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        page_name = updated_page.name if updated_page.name is not None else "Unknown"
        log(f"Successfully added file {new_file_id} to page {target_page_id}: {page_name}")
    trace_out()
    return not is_error()
