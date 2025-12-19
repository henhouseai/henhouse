from __future__ import annotations
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.image.image_registry import get_image

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

@register_action('copy_images')
@register_command('copy_images')
def copy_images() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('target_page') and not gateway.is_set('t_page'):
        warn("No target page ID provided")
        report_error("action", "Target page ID is required")
    if not is_error():
        if not gateway.is_set('image_id'):
            warn("No image IDs provided")
            report_error("action", "Image IDs are required")
    target_page_id: int = 0
    if not is_error():
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page')
        image_id_str = gateway.get_arg('image_id')
        rank = gateway.get_arg('rank')
        
        try:
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid target page ID: {target_page_arg}")
            report_error("action", "Target page ID must be a number")
    
    # Parse comma-separated image IDs
    image_ids: List[int] = []
    if not is_error() and image_id_str:
        try:
            image_ids = [int(id_str.strip()) for id_str in image_id_str.split(',') if id_str.strip()]
            if not image_ids:
                warn("No valid image IDs provided")
                report_error("action", "No valid image IDs provided")
        except ValueError:
            warn(f"Invalid image ID format: {image_id_str}")
            report_error("action", "Image IDs must be comma-separated numbers")
    
    # Parse optional rank parameter
    rank_int: int | None = None
    if not is_error() and rank:
        try:
            rank_int = int(rank)
            if rank_int <= 0:
                warn(f"Invalid rank: {rank_int} (must be positive)")
                report_error("action", "Rank must be a positive number")
        except ValueError:
            warn(f"Invalid rank: {rank}")
            report_error("action", "Rank must be a number")
    
    page = None
    if not is_error():
        log(f"Loading target page {target_page_id}")
        page = get_page(page_id=target_page_id)
        if not page:
            warn(f"Target page {target_page_id} not found")
            report_error("action", f"Target page {target_page_id} not found")
    
    # Verify all images exist
    if not is_error():
        for image_id in image_ids:
            log(f"Loading image {image_id}")
            image = get_image(image_id=image_id)
            if not image:
                warn(f"Image {image_id} not found")
                report_error("action", f"Image {image_id} not found")
    
    if not is_error() and page is not None:
        log(f"Copying {len(image_ids)} images to target page {target_page_id}")
        success = page.copy_media_items("image", image_ids, target_rank=rank_int)
        if not success:
            warn(f"Failed to copy images to target page {target_page_id}")
            report_error("action", f"Failed to copy images to target page {target_page_id}")
    
    updated_page = None
    if not is_error():
        # Reload page to get updated state
        log(f"Reloading target page {target_page_id} to show updated state")
        updated_page = get_page(page_id=target_page_id)
        if not updated_page:
            warn(f"Failed to reload target page {target_page_id}")
            report_error("action", f"Failed to reload target page {target_page_id}")
    
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        
        # Add operation-specific metadata
        response_data.update({
            "copied_image_ids": image_ids,
            "operation": "copy_images"
        })
        
        if rank_int is not None:
            response_data.update({
                "set_rank_start": rank_int,
                "rank_operation": "applied"
            })
            log(f"Successfully copied {len(image_ids)} images to target page {target_page_id} starting at rank {rank_int}")
        else:
            response_data.update({
                "rank_operation": "skipped"
            })
            log(f"Successfully copied {len(image_ids)} images to target page {target_page_id}")
        
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()
