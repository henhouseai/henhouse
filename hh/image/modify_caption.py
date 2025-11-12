from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
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

@register_action('modify_caption')
@register_command('modify_caption')
def modify_caption() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    image_id_arg = gateway.get_arg('image_id') or gateway.get_arg('id')
    caption = gateway.get_arg('caption')
    
    if not image_id_arg:
        warn("No image ID provided")
        report_error("action", "Image ID is required")
    if not caption:
        warn("No caption provided")
        report_error("action", "Caption is required")
    if caption is True:
        if gateway.get_arg('clear'):
            caption = ''
        else:
            warn("Empty caption provided, use -clear to clear it")
            report_error("action", "Empty caption provided, use -clear to clear it")

    if not is_error():
        try:
            image_id = int(image_id_arg)
        except ValueError:
            warn(f"Invalid image ID: {image_id_arg}")
            report_error("action", "Image ID must be a number")
    
    if not is_error():
        log(f"Loading image {image_id}")
        image = get_image(image_id=image_id)
        if not image:
            warn(f"Image {image_id} not found")
            report_error("action", f"Image {image_id} not found")
    
    if not is_error():
        log(f"Modifying caption for image {image_id} to: {caption}")
        old_caption = image.caption
        success = image.modify_caption(caption)
        if not success:
            warn(f"Failed to modify caption for image {image_id}")
            report_error("action", f"Failed to modify caption for image {image_id}")
    
    # Reload image to show updated state
    if not is_error():
        log(f"Reloading image {image_id} to show updated state")
        updated_image = get_image(image_id=image_id)
        if not updated_image:
            warn(f"Failed to reload image {image_id}")
            report_error("action", f"Failed to reload image {image_id}")
    
    if not is_error():
        response_data = updated_image.show_image()
        
        # Add operation-specific metadata
        response_data.update({
            "image_id": image_id,
            "old_caption": old_caption,
            "new_caption": caption,
            "operation": "modify_caption"
        })
        
        log(f"Successfully modified caption for image {image_id}")
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()

