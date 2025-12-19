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

@register_action('upload_images')
@register_command('upload_images')
def upload_image() -> bool:
    trace_in()
    gateway = get_gateway()
    # Get page ID (required)
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    
    # Check for at least one file
    if not gateway.is_set('file0_path'):
        warn("No file0_path provided")
        report_error("action", "At least one file path is required")
    
    if not gateway.is_set('file0_name'):
        warn("No file0_name provided")
        report_error("action", "At least one file name is required")
    
    page_id: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    
    page = None
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    # Process multiple files in ascending order (file0, file1, file2, ...)
    uploaded_image_ids = []
    if not is_error() and page is not None:
        file_idx = 0
        while True:
            file_path_key = f'file{file_idx}_path'
            file_name_key = f'file{file_idx}_name'
            
            # Check if this file exists
            if not gateway.is_set(file_path_key):
                # No more files, stop processing
                break
            
            if not gateway.is_set(file_name_key):
                warn(f"File {file_idx} has path but no name")
                report_error("action", f"File {file_idx} name is required")
                break  # Stop on error
            
            file_path = gateway.get_arg(file_path_key)
            original_filename = gateway.get_arg(file_name_key)
            caption = gateway.get_arg('caption')  # Optional override (applies to all files if set)
            
            # Validate file exists
            if not Path(file_path).exists():
                warn(f"Image file {file_idx} not found: {file_path}")
                report_error("action", f"Image file {file_idx} not found: {file_path}")
                break  # Stop on error
            
            if not os.access(file_path, os.R_OK):
                warn(f"Image file {file_idx} not readable: {file_path}")
                report_error("action", f"Image file {file_idx} not readable: {file_path}")
                break  # Stop on error
            
            # Check for errors before processing this file
            if is_error():
                break  # Stop processing if any previous error occurred
            
            # Use original filename as default caption if no caption provided
            file_caption = caption
            if not file_caption:
                # Use the original filename (without extension) as caption
                file_caption = Path(original_filename).stem
            
            log(f"Uploading image {file_idx} '{file_caption}' to page {page_id} from temp file: {file_path}")
            new_image_id = page.add_image(file_path, file_caption)
            
            # Check for errors after upload
            if is_error():
                warn(f"Image {file_idx} upload failed")
                break  # Stop on error
            
            if new_image_id is None:
                warn(f"Image {file_idx} upload failed: no image ID returned")
                report_error("action", f"Image {file_idx} upload failed")
                break  # Stop on error
            
            uploaded_image_ids.append(new_image_id)
            log(f"Successfully uploaded image {file_idx} (ID: {new_image_id}) to page {page_id}")
            
            file_idx += 1
    
    updated_page = None
    if not is_error():
        log(f"Reloading page {page_id} to show new images")
        updated_page = get_page(page_id=page_id)
        if not updated_page or updated_page.name is None:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")
    
    if not is_error() and updated_page is not None:
        response_data = updated_page.get_page()
        gateway.response.set_action_response(success_payload(response_data))
        page_name = updated_page.name if updated_page.name is not None else "Unknown"
        log(f"Successfully uploaded {len(uploaded_image_ids)} image(s) to page {page_id}: {page_name}")
    
    trace_out()
    return not is_error()

