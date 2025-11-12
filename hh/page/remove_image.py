from __future__ import annotations
from typing import Dict, Any
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

@register_action('remove_image')
@register_command('remove_image')
def remove_image() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_set('page_id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set('image_id'):
            warn("No image ID provided")
            report_error("action", "Image ID is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id')
        image_id = gateway.get_arg('image_id')
        rank = gateway.get_arg('rank')
        try:
            page_id = int(page_id_arg)
            image_id = int(image_id)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg} or image ID: {image_id}")
            report_error("action", "Page ID and image ID must be numbers")
    
    # Parse optional rank parameter
    rank_int = None
    if not is_error() and rank:
        try:
            rank_int = int(rank)
            if rank_int <= 0:
                warn(f"Invalid rank: {rank_int} (must be positive)")
                report_error("action", "Rank must be a positive number")
        except ValueError:
            warn(f"Invalid rank: {rank}")
            report_error("action", "Rank must be a number")
    
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    if not is_error():
        # If rank is specified, validate that the image exists at that rank
        if rank_int is not None:
            log(f"Validating image {image_id} exists at rank {rank_int} in page {page_id}")
            # Get current images to validate the rank
            current_images = page.get_images_data()
            image_found_at_rank = False
            for img in current_images:
                if img['id'] == image_id and img.get('image_rank') == rank_int:
                    image_found_at_rank = True
                    break
            
            if not image_found_at_rank:
                warn(f"Image {image_id} not found at rank {rank_int} in page {page_id}")
                report_error("action", f"Image {image_id} not found at rank {rank_int} in page {page_id}")
    
    if not is_error():
        if rank_int is not None:
            log(f"Removing image {image_id} at rank {rank_int} from page {page_id}")
            success = page.remove_image(image_id, rank_int)
            if not success:
                warn(f"Failed to remove image {image_id} at rank {rank_int} from page {page_id}")
                report_error("action", f"Failed to remove image {image_id} at rank {rank_int}")
        else:
            log(f"Removing all instances of image {image_id} from page {page_id}")
            # Get all instances of this image in the page
            current_images = page.get_images_data()
            instances_to_remove = []
            for img in current_images:
                if img['id'] == image_id:
                    instances_to_remove.append({
                        'image_id': image_id,
                        'image_rank': img.get('image_rank')
                    })
            
            if not instances_to_remove:
                warn(f"No instances of image {image_id} found in page {page_id}")
                report_error("action", f"No instances of image {image_id} found in page {page_id}")
            
            # Remove each instance (reverse order to avoid rank shifting issues)
            removed_count = 0
            for instance in sorted(instances_to_remove, key=lambda x: x['image_rank'], reverse=True):
                if not is_error():
                    success = page.remove_image(instance['image_id'], instance['image_rank'])
                    if success:
                        removed_count += 1
                    else:
                        warn(f"Failed to remove image {instance['image_id']} at rank {instance['image_rank']}")
                        report_error("action", f"Failed to remove image {instance['image_id']} at rank {instance['image_rank']}")
    
    if not is_error():
        # Reload page to get updated state
        log(f"Reloading page {page_id} to show updated state")
        updated_page = get_page(page_id=page_id)
        if not updated_page:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")
    
    if not is_error():
        response_data = updated_page.show_page()
        
        # Add operation-specific metadata
        if rank_int is not None:
            response_data.update({
                "removed_image_id": image_id,
                "removed_rank": rank_int,
                "removal_type": "single_instance"
            })
            log(f"Successfully removed image {image_id} at rank {rank_int} from page {page_id}")
        else:
            response_data.update({
                "removed_image_id": image_id,
                "removed_instances": removed_count,
                "removal_type": "all_instances"
            })
            log(f"Successfully removed {removed_count} instances of image {image_id} from page {page_id}")
        
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()
