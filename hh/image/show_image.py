from __future__ import annotations
from typing import Dict, Any, List
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

@register_action('show_image')
@register_command('show_image')
def show_image() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    image_id = gateway.get_arg('id')
    if not image_id:
        warn("No image ID provided")
        report_error("action", "Image ID is required")
    if not is_error():
        try:
            image_id = int(image_id)
        except ValueError:
            warn(f"Invalid image ID: {image_id}")
            report_error("action", "Image ID must be a number")
    if not is_error():
        log(f"Loading image {image_id}")
        image = get_image(image_id=image_id)
        if not image:
            warn(f"Image {image_id} not found")
            report_error("action", f"Image {image_id} not found")
    if not is_error():
        # Get complete image display data using the unified show_image method
        response_data = image.show_image()
        gateway.response.set_action_response(success_payload(response_data))
        log(f"Successfully loaded image {image_id}: {image.caption}")
    trace_out()
    return not is_error()
