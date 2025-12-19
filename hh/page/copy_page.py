from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.image.image_registry import get_image
from hh.page.page import Page
from hh.image.image import Image

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

@register_action('copy_page')
@register_command('copy_page')
def copy_page() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('source_page') and not gateway.is_set('s_page'):
        warn("No source page ID provided")
        report_error("action", "Source page ID is required")
    if not is_error():
        if not gateway.is_set('target_page') and not gateway.is_set('t_page'):
            warn("No target page ID provided")
            report_error("action", "Target page ID is required")
    source_page_id: int = 0
    target_page_id: int = 0
    if not is_error():
        source_page_arg = gateway.get_arg('source_page') or gateway.get_arg('s_page')
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page')
        recursive = gateway.get_arg('r') or gateway.get_arg('recursive')
        max_depth = gateway.get_arg('rd') or gateway.get_arg('recursive-depth')
        copy_images = gateway.is_set('images')
        copy_files = gateway.is_set('files')
        try:
            source_page_id = int(source_page_arg)
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid source page ID: {source_page_arg} or target page ID: {target_page_arg}")
            report_error("action", "Source page ID and target page ID must be numbers")
    # Parse recursive flag
    recursive_bool = False
    if not is_error():
        if recursive:
            recursive_bool = True
            log("Recursive copy enabled")
    # Parse max depth
    max_depth_int: int | None = None
    if not is_error() and max_depth:
        try:
            max_depth_int = int(max_depth)
            log(f"Max recursive depth set to {max_depth_int}")
        except ValueError:
            warn(f"Invalid max depth provided: {max_depth}")
            report_error("action", "Max depth must be a number")
    source_page = None
    if not is_error():
        source_page = get_page(page_id=source_page_id)
        if not source_page:
            warn(f"Source page {source_page_id} not found")
            report_error("action", f"Source page {source_page_id} not found")
    new_page_id: int = 0
    if not is_error() and source_page is not None:
        new_page_id = source_page.copy_page(target_page_id, recursive=recursive_bool, max_depth=max_depth_int, copy_images=copy_images, copy_files=copy_files)
        if new_page_id == 0:
            warn(f"Failed to copy page {source_page_id} to {target_page_id}")
            report_error("action", f"Failed to copy page {source_page_id} to {target_page_id}")
    new_page = None
    if not is_error() and new_page_id != 0:
        # Reload the new page to get updated data after copy
        new_page = get_page(page_id=new_page_id)
        if not new_page:
            warn(f"Failed to reload new page {new_page_id} after copy")
            report_error("action", f"Failed to reload new page {new_page_id} after copy")
    if not is_error() and new_page is not None:
        response_data = new_page.show_page()
        response_data.update({
            "recursive": recursive_bool,
            "max_depth": max_depth_int,
            "copy_images": copy_images,
            "copy_files": copy_files
        })
        gateway.response.set_action_response(success_payload(response_data))
        log(f"Successfully copied page {source_page_id} to page {new_page_id}")
    trace_out()
    return not is_error()
