from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.video.video_registry import get_video

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

@register_action('delete_video')
@register_command('delete_video')
def delete_video() -> bool:
    trace_in()
    gateway = get_gateway()
    video_id_arg = gateway.get_arg('video_id') or gateway.get_arg('id')
    if not video_id_arg:
        warn("No video ID provided")
        report_error("action", "Video ID is required")
    video_id: int = 0
    if not is_error():
        try:
            video_id = int(video_id_arg)
        except ValueError:
            warn(f"Invalid video ID: {video_id_arg}")
            report_error("action", "Video ID must be a number")
    video = None
    if not is_error():
        log(f"Loading video {video_id}")
        video = get_video(video_id=video_id)
        if not video:
            warn(f"Video {video_id} not found")
            report_error("action", f"Video {video_id} not found")
    if not is_error() and video is not None:
        log(f"Deleting video {video_id}")
        success = video.delete_from_database()
        if not success:
            warn(f"Failed to delete video {video_id}")
            report_error("action", f"Failed to delete video {video_id}")
        else:
            log(f"Successfully deleted video {video_id}")
            gateway.response.set_action_response(success_payload({"video_id": video_id, "deleted": True}))
    trace_out()
    return not is_error()
