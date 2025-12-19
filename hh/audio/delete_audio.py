from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.audio.audio_registry import get_audio

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

@register_action('delete_audio')
@register_command('delete_audio')
def delete_audio() -> bool:
    trace_in()
    gateway = get_gateway()
    audio_id_arg = gateway.get_arg('audio_id') or gateway.get_arg('id')
    if not audio_id_arg:
        warn("No audio ID provided")
        report_error("action", "Audio ID is required")
    audio_id: int = 0
    if not is_error():
        try:
            audio_id = int(audio_id_arg)
        except ValueError:
            warn(f"Invalid audio ID: {audio_id_arg}")
            report_error("action", "Audio ID must be a number")
    audio = None
    if not is_error():
        log(f"Loading audio {audio_id}")
        audio = get_audio(audio_id=audio_id)
        if not audio:
            warn(f"Audio {audio_id} not found")
            report_error("action", f"Audio {audio_id} not found")
    if not is_error() and audio is not None:
        log(f"Deleting audio {audio_id}")
        success = audio.delete_from_database()
        if not success:
            warn(f"Failed to delete audio {audio_id}")
            report_error("action", f"Failed to delete audio {audio_id}")
        else:
            log(f"Successfully deleted audio {audio_id}")
            gateway.response.set_action_response(success_payload({"audio_id": audio_id, "deleted": True}))
    trace_out()
    return not is_error()
