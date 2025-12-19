from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
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

@register_action('remove_audio')
@register_command('remove_audio')
def remove_audio() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('page_id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set('audio_id'):
            warn("No audio ID provided")
            report_error("action", "Audio ID is required")
    page_id: int = 0
    audio_id: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg('page_id')
        audio_id_arg = gateway.get_arg('audio_id')
        rank = gateway.get_arg('rank')
        try:
            page_id = int(page_id_arg)
            audio_id = int(audio_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg} or audio ID: {audio_id_arg}")
            report_error("action", "Page ID and audio ID must be numbers")
    
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
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    if not is_error() and page is not None:
        # If rank is specified, validate that the audio exists at that rank
        if rank_int is not None:
            log(f"Validating audio {audio_id} exists at rank {rank_int} in page {page_id}")
            # Get current audio to validate the rank
            current_audio = page.get_audio_data()
            audio_found_at_rank = False
            for aud in current_audio:
                if aud['id'] == audio_id and aud.get('audio_rank') == rank_int:
                    audio_found_at_rank = True
                    break
            
            if not audio_found_at_rank:
                warn(f"Audio {audio_id} not found at rank {rank_int} in page {page_id}")
                report_error("action", f"Audio {audio_id} not found at rank {rank_int} in page {page_id}")
    
    removed_count: int = 0
    if not is_error() and page is not None:
        if rank_int is not None:
            log(f"Removing audio {audio_id} at rank {rank_int} from page {page_id}")
            success = page.remove_media_item("audio", audio_id, rank_int)
            if not success:
                warn(f"Failed to remove audio {audio_id} at rank {rank_int} from page {page_id}")
                report_error("action", f"Failed to remove audio {audio_id} at rank {rank_int}")
            else:
                removed_count = 1
        else:
            log(f"Removing all instances of audio {audio_id} from page {page_id}")
            # Get all instances of this audio in the page
            current_audio = page.get_audio_data()
            instances_to_remove = []
            for aud in current_audio:
                if aud['id'] == audio_id:
                    instances_to_remove.append({
                        'audio_id': audio_id,
                        'audio_rank': aud.get('audio_rank')
                    })
            
            if not instances_to_remove:
                warn(f"No instances of audio {audio_id} found in page {page_id}")
                report_error("action", f"No instances of audio {audio_id} found in page {page_id}")
            
            # Remove each instance (reverse order to avoid rank shifting issues)
            for instance in sorted(instances_to_remove, key=lambda x: x['audio_rank'], reverse=True):
                if not is_error():
                    success = page.remove_media_item("audio", instance['audio_id'], instance['audio_rank'])
                    if success:
                        removed_count += 1
                    else:
                        warn(f"Failed to remove audio {instance['audio_id']} at rank {instance['audio_rank']}")
                        report_error("action", f"Failed to remove audio {instance['audio_id']} at rank {instance['audio_rank']}")
    
    updated_page = None
    if not is_error():
        # Reload page to get updated state
        log(f"Reloading page {page_id} to show updated state")
        updated_page = get_page(page_id=page_id)
        if not updated_page:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")
    
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        
        # Add operation-specific metadata
        if rank_int is not None:
            response_data.update({
                "removed_audio_id": audio_id,
                "removed_rank": rank_int,
                "removal_type": "single_instance"
            })
            log(f"Successfully removed audio {audio_id} at rank {rank_int} from page {page_id}")
        else:
            response_data.update({
                "removed_audio_id": audio_id,
                "removed_instances": removed_count,
                "removal_type": "all_instances"
            })
            log(f"Successfully removed {removed_count} instances of audio {audio_id} from page {page_id}")
        
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()
