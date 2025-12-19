from __future__ import annotations
from typing import Dict, Any, List
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

@register_action('move_audios')
@register_command('move_audios')
def move_audios() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('source_page') and not gateway.is_set('s_page'):
        warn("No source page ID provided")
        report_error("action", "Source page ID is required")
    if not is_error():
        if not gateway.is_set('target_page') and not gateway.is_set('t_page'):
            warn("No target page ID provided")
            report_error("action", "Target page ID is required")
    source_page_id: int = 0
    target_page_id: int = 0
    if not is_error():
        # Source specification
        source_page_arg = gateway.get_arg('source_page') or gateway.get_arg('s_page')
        source_ranks_str = gateway.get_arg('source_rank') or gateway.get_arg('s_rank')  # Optional CSV of ranks
        
        # Destination specification
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page')
        target_rank = gateway.get_arg('target_rank') or gateway.get_arg('t_rank')
        
        try:
            source_page_id = int(source_page_arg)
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid IDs provided. Source: {source_page_arg}, Target: {target_page_arg}")
            report_error("action", "All IDs must be numbers")
    
    # Parse optional target rank parameter
    target_rank_int: int | None = None
    if not is_error() and target_rank:
        try:
            target_rank_int = int(target_rank)
            if target_rank_int <= 0:
                warn(f"Invalid target rank: {target_rank_int} (must be positive)")
                report_error("action", "Target rank must be a positive number")
        except ValueError:
            warn(f"Invalid target rank: {target_rank}")
            report_error("action", "Target rank must be a number")
    
    # Load source page
    source_page = None
    if not is_error():
        log(f"Loading source page {source_page_id}")
        source_page = get_page(page_id=source_page_id)
        if not source_page:
            warn(f"Source page {source_page_id} not found")
            report_error("action", f"Source page {source_page_id} not found")
    
    # Load target page
    target_page = None
    if not is_error():
        log(f"Loading target page {target_page_id}")
        target_page = get_page(page_id=target_page_id)
        if not target_page:
            warn(f"Target page {target_page_id} not found")
            report_error("action", f"Target page {target_page_id} not found")
    
    # Get source audio to determine what to move
    audio_instances: List[Dict[str, Any]] = []
    source_ranks: List[int] = []
    if not is_error() and source_page is not None:
        log(f"Getting audio from source page {source_page_id}")
        source_audio = source_page.get_audio_data()
        
        if source_ranks_str:
            # Parse CSV of ranks
            try:
                source_ranks = [int(rank_str.strip()) for rank_str in source_ranks_str.split(',') if rank_str.strip()]
                if not source_ranks:
                    warn("No valid source ranks provided")
                    report_error("action", "No valid source ranks provided")
            except ValueError:
                warn(f"Invalid source ranks format: {source_ranks_str}")
                report_error("action", "Source ranks must be comma-separated numbers")
            
            # Build audio instances for specified ranks
            if not is_error():
                for rank in source_ranks:
                    for aud in source_audio:
                        if aud.get('audio_rank') == rank:
                            audio_instances.append({
                                'audio_id': aud['id'],
                                'source_page_id': source_page_id,
                                'source_rank': rank
                            })
                            break
                    else:
                        warn(f"Audio not found at rank {rank} in source page {source_page_id}")
                        report_error("action", f"Audio not found at rank {rank} in source page {source_page_id}")
        else:
            # Move all audio
            log(f"Moving all audio from source page {source_page_id}")
            for aud in source_audio:
                audio_instances.append({
                    'audio_id': aud['id'],
                    'source_page_id': source_page_id,
                    'source_rank': aud.get('audio_rank')
                })
    
    if not is_error() and not audio_instances:
        warn("No audio to move")
        report_error("action", "No audio to move")
    
    # Perform the move operation
    if not is_error() and target_page is not None:
        log(f"Moving {len(audio_instances)} audio from page {source_page_id} to page {target_page_id}")
        success = target_page.move_media_items("audio", audio_instances, target_rank=target_rank_int)
        if not success:
            warn(f"Failed to move audio from page {source_page_id} to page {target_page_id}")
            report_error("action", f"Failed to move audio from page {source_page_id} to page {target_page_id}")
    
    # Reload target page to show updated state
    updated_page = None
    if not is_error():
        log(f"Reloading target page {target_page_id} to show updated state")
        updated_page = get_page(page_id=target_page_id)
        if not updated_page:
            warn(f"Failed to reload target page {target_page_id}")
            report_error("action", f"Failed to reload target page {target_page_id}")
    
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        
        # Add operation-specific metadata
        response_data.update({
            "moved_count": len(audio_instances),
            "source_page_id": source_page_id,
            "operation": "move_audios"
        })
        
        if source_ranks_str:
            response_data.update({
                "source_ranks": source_ranks
            })
        else:
            response_data.update({
                "move_type": "all_audio"
            })
        
        if target_rank_int is not None:
            response_data.update({
                "set_rank": target_rank_int,
                "rank_operation": "applied"
            })
            log(f"Successfully moved {len(audio_instances)} audio to target page {target_page_id} starting at rank {target_rank_int}")
        else:
            response_data.update({
                "rank_operation": "skipped"
            })
            log(f"Successfully moved {len(audio_instances)} audio to target page {target_page_id}")
        
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()
