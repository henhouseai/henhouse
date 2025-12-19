from __future__ import annotations
from typing import Dict, Any, Mapping, cast
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_registry import get_image
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

@register_action('set_image_visibility')
@register_command('set_image_visibility')
def set_image_visibility() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('image_id') and not gateway.is_set('id'):
        warn("No image ID provided")
        report_error("action", "Image ID is required")
    if not is_error():
        if not gateway.is_set('visibility'):
            warn("No visibility value provided")
            report_error("action", "Visibility value is required")
    image_id: int = 0
    visibility: int = 0
    if not is_error():
        image_id_arg = gateway.get_arg('image_id') or gateway.get_arg('id')
        visibility_arg = gateway.get_arg('visibility')
        try:
            image_id = int(image_id_arg)
            visibility = int(visibility_arg)
        except ValueError:
            warn(f"Invalid image ID: {image_id_arg} or visibility: {visibility_arg}")
            report_error("action", "Image ID and visibility must be numbers")
    
    image = None
    if not is_error():
        log(f"Loading image {image_id}")
        image = get_image(image_id=image_id)
        if not image:
            warn(f"Image {image_id} not found")
            report_error("action", f"Image {image_id} not found")
    
    old_visibility: int = 0
    if not is_error() and image is not None:
        old_visibility = image.visibility if image.visibility is not None else 0
        # Check if update is needed
        if old_visibility == visibility:
            log(f"Image {image_id} visibility is already {visibility}, no update needed")
        else:
            log(f"Setting image {image_id} visibility from {old_visibility} to {visibility}")
            success = image.modify_visibility(visibility)
            if not success:
                warn(f"Failed to set image {image_id} visibility to {visibility}")
                report_error("action", f"Failed to set image {image_id} visibility to {visibility}")
    
    if not is_error():
        # Build response structure
        response_data = {
            "image_id": image_id,
            "old_visibility": old_visibility,
            "new_visibility": visibility
        }
        
        log(f"Successfully set image {image_id} visibility from {old_visibility} to {visibility}")
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()


@register_parser('set_image_visibility')
def set_image_visibility_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    try:
        action_response = gateway.response.get_action_response()
        if action_response is None:
            warn("Action response is None")
            report_error("backend", "Action response is None")
            trace_out()
            return False
        source_data = get_data(cast(Mapping[str, Any], action_response))
        image_id = source_data.get("image_id")
        old_visibility = source_data.get("old_visibility")
        new_visibility = source_data.get("new_visibility")
        
        lines = [render_header_block("l_set_image_visibility_header")]
        
        table = TableData()
        table.add_row("set_image_visibility_header", info="")
        
        # Operation details
        table.add_row("image_id", info=str(image_id))
        table.add_row("extra_data_old_visibility", info=str(old_visibility))
        table.add_row("extra_data_new_visibility", info=str(new_visibility))
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("set_image_visibility_header")
                .add_simple(["image_id", "extra_data_old_visibility", "extra_data_new_visibility"]),
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

