from __future__ import annotations
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block

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

@register_action('set_image_rank')
@register_command('set_image_rank')
def set_image_rank() -> bool:
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
        if not gateway.is_set('target_rank') and not gateway.is_set('t_rank'):
            warn("No target rank provided")
            report_error("action", "Target rank is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id')
        image_id = gateway.get_arg('image_id')
        target_rank_arg = gateway.get_arg('target_rank') or gateway.get_arg('t_rank')
        source_rank = gateway.get_arg('source_rank') or gateway.get_arg('s_rank')
        try:
            page_id = int(page_id_arg)
            image_id = int(image_id)
            target_rank = int(target_rank_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}, image ID: {image_id}, or target rank: {target_rank_arg}")
            report_error("action", "Page ID, image ID, and target rank must be numbers")
    
    # Parse optional source_rank parameter
    source_rank_int = None
    if not is_error() and source_rank:
        try:
            source_rank_int = int(source_rank)
            if source_rank_int <= 0:
                warn(f"Invalid source rank: {source_rank_int} (must be positive)")
                report_error("action", "Source rank must be a positive number")
        except ValueError:
            warn(f"Invalid source rank: {source_rank}")
            report_error("action", "Source rank must be a number")
    
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    if not is_error():
        # Get current images to validate the image exists and check for duplicates
        current_images = page.get_images_data()
        image_instances = []
        for img in current_images:
            if img['id'] == image_id:
                image_instances.append({
                    'image_id': image_id,
                    'image_rank': img.get('image_rank')
                })
        
        if not image_instances:
            warn(f"Image {image_id} not found in page {page_id}")
            report_error("action", f"Image {image_id} not found in page {page_id}")
    
    if not is_error():
        # Check for duplicates if source_rank not specified
        if source_rank_int is None:
            if len(image_instances) > 1:
                warn(f"Image {image_id} appears {len(image_instances)} times in page {page_id}. Source rank must be specified.")
                report_error("action", f"Image {image_id} appears {len(image_instances)} times in page {page_id}. Source rank must be specified.")
            else:
                # Use the single instance's rank
                source_rank_int = image_instances[0]['image_rank']
                log(f"Using current rank {source_rank_int} for image {image_id}")
        else:
            # Validate that the specified source_rank exists for this image
            source_rank_found = any(inst['image_rank'] == source_rank_int for inst in image_instances)
            if not source_rank_found:
                warn(f"Image {image_id} not found at rank {source_rank_int} in page {page_id}")
                report_error("action", f"Image {image_id} not found at rank {source_rank_int} in page {page_id}")
    
    if not is_error():
        # Validate that new rank is positive
        if target_rank <= 0:
            warn(f"Invalid target rank: {target_rank} (must be positive)")
            report_error("action", "Target rank must be a positive number")
    
    if not is_error():
        log(f"Setting image {image_id} rank from {source_rank_int} to {target_rank} in page {page_id}")
        success = page.set_image_rank(image_id, source_rank_int, target_rank)
        if not success:
            warn(f"Failed to set image {image_id} rank from {source_rank_int} to {target_rank}")
            report_error("action", f"Failed to set image {image_id} rank from {source_rank_int} to {target_rank}")
    
    if not is_error():
        # Reload page to get updated state
        log(f"Reloading page {page_id} to get updated state")
        updated_page = get_page(page_id=page_id)
        if not updated_page:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")
    
    if not is_error():
        # Get updated images list with current ranks
        updated_images = updated_page.get_images_data(rebuild=True)
        
        # Build abbreviated response structure
        images_list = []
        for img in updated_images:
            images_list.append({
                "id": img.get('id'),
                "image_rank": img.get('image_rank'),
                "caption": img.get('caption')
            })
        
        response_data = {
            "page_id": page_id,
            "image_id": image_id,
            "source_rank": source_rank_int,
            "target_rank": target_rank,
            "images": images_list
        }
        
        log(f"Successfully set image {image_id} rank from {source_rank_int} to {target_rank} in page {page_id}")
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()


@register_parser('set_image_rank')
def set_image_rank_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    try:
        source_data = get_data(gateway.response.get_action_response())
        page_id = source_data.get("page_id")
        image_id = source_data.get("image_id")
        source_rank = source_data.get("source_rank")
        target_rank = source_data.get("target_rank")
        images = source_data.get("images", [])
        
        lines = [render_header_block("l_set_image_rank_header")]
        
        table = TableData()
        table.add_row("set_image_rank_header", info="")
        
        # Operation summary
        table.add_row("page_id", info=str(page_id))
        table.add_row("extra_data_moved_image_id", info=str(image_id))
        table.add_row("extra_data_old_rank", info=str(source_rank))
        table.add_row("extra_data_new_rank", info=str(target_rank))
        
        # Images table header
        if images:
            table.add_row("images_header", info="")
            for img in images:
                caption = img.get("caption") or "untitled"
                table.add_row(
                    "image_item",
                    info=f"Rank {img.get('image_rank')}: Image {img.get('id')} - {caption}"
                )
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("set_image_rank_header")
                .add_simple(["page_id", "extra_data_moved_image_id", "extra_data_old_rank", "extra_data_new_rank", "images_header", "image_item"]),
                block_type="rows",
                table_overrides={"margin_l": 4},
            )
        )
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False
