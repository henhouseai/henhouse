from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from pathlib import Path
import os

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

@register_action('upload_image')
@register_command('upload_image')
def upload_image() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Get page ID (required)
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    
    # Get file0_path and file0_name (from multipart upload)
    if not gateway.is_set('file0_path'):
        warn("No file0_path provided")
        report_error("action", "File path is required")
    
    if not gateway.is_set('file0_name'):
        warn("No file0_name provided")
        report_error("action", "File name is required")
    
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        file_path = gateway.get_arg('file0_path')
        original_filename = gateway.get_arg('file0_name')
        caption = gateway.get_arg('caption')  # Optional override
        
        # Validate file exists
        if not Path(file_path).exists():
            warn(f"Image file not found: {file_path}")
            report_error("action", f"Image file not found: {file_path}")
        elif not os.access(file_path, os.R_OK):
            warn(f"Image file not readable: {file_path}")
            report_error("action", f"Image file not readable: {file_path}")
    
    if not is_error():
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    if not is_error():
        # Use original filename as default caption if no caption provided
        if not caption:
            # Use the original filename (without extension) as caption
            caption = Path(original_filename).stem
            log(f"Using original filename as caption: {caption}")
        
        log(f"Uploading image '{caption}' to page {page_id} from temp file: {file_path}")
        new_image_id = page.add_image(file_path, caption)
        image_created = not is_error() and new_image_id is not None
        if not image_created:
            warn("Image upload failed")
            report_error("action", "Image upload failed")
    
    if not is_error():
        log(f"Reloading page {page_id} to show new image")
        updated_page = get_page(page_id=page_id)
        page_loaded = not is_error() and updated_page.name is not None
        if not page_loaded:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")
    
    if not is_error():
        response_data = updated_page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        log(f"Successfully uploaded image {new_image_id} to page {page_id}: {updated_page.name}")
    
    trace_out()
    return not is_error()

