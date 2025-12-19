from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.audio.audio_registry import get_audio
from hh.page.page import Page
from hh.audio.audio import Audio
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

@register_action('add_audio')
@register_command('add_audio')
def add_audio() -> bool:
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
            warn(f"Audio file not found: {file_path}")
            report_error("action", f"Audio file not found: {file_path}")
        elif not os.access(file_path, os.R_OK):
            warn(f"Audio file not readable: {file_path}")
            report_error("action", f"Audio file not readable: {file_path}")
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
    new_audio_id: int | None = None
    if not is_error() and parent_page is not None:
        caption = gateway.get_arg('caption')
        # Use filename as default caption if no caption provided
        if not caption:
            caption = Path(file_path).stem  # Get filename without extension
            log(f"Using filename as caption: {caption}")
        
        log(f"Adding audio '{caption}' to page {target_page_id}")
        new_audio_id = parent_page.add_audio(file_path, caption)
        audio_created = not is_error() and new_audio_id is not None
        if not audio_created:
            warn("Audio creation failed")
            report_error("action", "Audio creation failed")
    updated_page = None
    if not is_error():
        log(f"Reloading parent page {target_page_id} to show new audio")
        updated_page = get_page(page_id=target_page_id)
        if not updated_page or updated_page.name is None:
            warn(f"Failed to reload parent page {target_page_id}")
            report_error("action", f"Failed to reload parent page {target_page_id}")
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        page_name = updated_page.name if updated_page.name is not None else "Unknown"
        log(f"Successfully added audio {new_audio_id} to page {target_page_id}: {page_name}")
    trace_out()
    return not is_error()
