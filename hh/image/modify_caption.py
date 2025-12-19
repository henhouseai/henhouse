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

@register_action('modify_image_caption')
@register_command('modify_image_caption')
def modify_image_caption() -> bool:
    trace_in()
    gateway = get_gateway()
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

    image_id: int = 0
    if not is_error():
        try:
            image_id = int(image_id_arg)
        except ValueError:
            warn(f"Invalid image ID: {image_id_arg}")
            report_error("action", "Image ID must be a number")
    
    image = None
    if not is_error():
        log(f"Loading image {image_id}")
        image = get_image(image_id=image_id)
        if not image:
            warn(f"Image {image_id} not found")
            report_error("action", f"Image {image_id} not found")
    
    old_caption: str = ""
    if not is_error() and image is not None:
        log(f"Modifying caption for image {image_id} to: {caption}")
        old_caption = image.caption if image.caption is not None else ""
        success = image.modify_caption(caption)
        if not success:
            warn(f"Failed to modify caption for image {image_id}")
            report_error("action", f"Failed to modify caption for image {image_id}")
    
    if not is_error():
        # Build minimal response structure
        response_data = {
            "image_id": image_id,
            "old_caption": old_caption,
            "new_caption": caption
        }
        
        log(f"Successfully modified caption for image {image_id}")
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()


@register_parser('modify_image_caption')
def modify_image_caption_parser() -> bool:
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
        old_caption = source_data.get("old_caption", "")
        new_caption = source_data.get("new_caption", "")
        
        lines = [render_header_block("l_modify_image_caption_header")]
        
        table = TableData()
        table.add_row("modify_image_caption_header", info="")
        
        # Operation details
        table.add_row("image_id", info=str(image_id))
        table.add_row("extra_data_old_caption", info=old_caption if old_caption else "N/A")
        table.add_row("extra_data_new_caption", info=new_caption if new_caption else "N/A")
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("modify_image_caption_header")
                .add_simple(["image_id", "extra_data_old_caption", "extra_data_new_caption"]),
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

