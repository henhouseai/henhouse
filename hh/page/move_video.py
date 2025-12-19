from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
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

@register_action('move_video')
@register_command('move_video')
def move_video() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('source_page') and not gateway.is_set('s_page'):
        warn("No source page ID provided")
        report_error("action", "Source page ID is required")
    if not is_error():
        if not gateway.is_set('video_id'):
            warn("No video ID provided")
            report_error("action", "Video ID is required")
    if not is_error():
        if not gateway.is_set('target_page') and not gateway.is_set('t_page'):
            warn("No target page ID provided")
            report_error("action", "Target page ID is required")
    source_page_id: int = 0
    video_id: int = 0
    target_page_id: int = 0
    if not is_error():
        # Source specification
        source_page_arg = gateway.get_arg('source_page') or gateway.get_arg('s_page')
        video_id_arg = gateway.get_arg('video_id')
        source_rank = gateway.get_arg('source_rank') or gateway.get_arg('s_rank')
        
        # Destination specification
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page')
        target_rank = gateway.get_arg('target_rank') or gateway.get_arg('t_rank')
        
        try:
            source_page_id = int(source_page_arg)
            video_id = int(video_id_arg)
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid IDs provided. Source: {source_page_arg}, Video: {video_id_arg}, Target: {target_page_arg}")
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
    
    source_page = None
    if not is_error():
        log(f"Loading source page {source_page_id}")
        source_page = get_page(page_id=source_page_id)
        if not source_page:
            warn(f"Source page {source_page_id} not found")
            report_error("action", f"Source page {source_page_id} not found")
    
    # Auto-detect old_rank if not provided
    source_rank_int: int | None = None
    if not is_error() and source_page is not None:
        if source_rank:
            try:
                source_rank_int = int(source_rank)
                if source_rank_int <= 0:
                    warn(f"Invalid source rank: {source_rank_int} (must be positive)")
                    report_error("action", "Source rank must be a positive number")
            except ValueError:
                warn(f"Invalid source rank: {source_rank}")
                report_error("action", "Source rank must be a number")
        else:
            # Auto-detect old_rank if not provided
            log(f"Source rank not provided, checking for video instances in source page {source_page_id}")
            current_video = source_page.get_video_data()
            video_instances = [vid for vid in current_video if vid['id'] == video_id]
            
            if len(video_instances) == 0:
                warn(f"Video {video_id} not found in source page {source_page_id}")
                report_error("action", f"Video {video_id} not found in source page {source_page_id}")
            elif len(video_instances) > 1:
                warn(f"Video {video_id} appears {len(video_instances)} times in source page {source_page_id}. Old rank must be specified.")
                report_error("action", f"Video {video_id} appears {len(video_instances)} times in source page {source_page_id}. Old rank must be specified.")
            else:
                # Use the single instance's rank
                source_rank_int = video_instances[0]['video_rank']
                log(f"Using detected source rank {source_rank_int} for video {video_id}")
    
    target_page = None
    if not is_error():
        log(f"Loading target page {target_page_id}")
        target_page = get_page(page_id=target_page_id)
        if not target_page:
            warn(f"Target page {target_page_id} not found")
            report_error("action", f"Target page {target_page_id} not found")
    
    if not is_error():
        log(f"Loading video {video_id}")
        video = get_video(video_id=video_id)
        if not video:
            warn(f"Video {video_id} not found")
            report_error("action", f"Video {video_id} not found")
    
    if not is_error() and target_page is not None and source_rank_int is not None:
        log(f"Moving video {video_id} from page {source_page_id} rank {source_rank_int} to page {target_page_id}")
        # Create video instance structure for move_videos
        video_instances = [{
            'video_id': video_id,
            'source_page_id': source_page_id,
            'source_rank': source_rank_int
        }]
        success = target_page.move_media_items("video", video_instances, target_rank=target_rank_int)
        if not success:
            warn(f"Failed to move video {video_id} from page {source_page_id} to page {target_page_id}")
            report_error("action", f"Failed to move video {video_id} from page {source_page_id} to page {target_page_id}")
    
    updated_page = None
    if not is_error():
        # Reload target page to get updated state
        log(f"Reloading target page {target_page_id} to show updated state")
        updated_page = get_page(page_id=target_page_id)
        if not updated_page:
            warn(f"Failed to reload target page {target_page_id}")
            report_error("action", f"Failed to reload target page {target_page_id}")
    
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        
        # Add operation-specific metadata
        response_data.update({
            "moved_video_id": video_id,
            "source_page_id": source_page_id,
            "source_rank": source_rank_int,
            "operation": "move_video"
        })
        
        if target_rank_int is not None:
            response_data.update({
                "set_rank": target_rank_int,
                "rank_operation": "applied"
            })
            log(f"Successfully moved video {video_id} from page {source_page_id} rank {source_rank_int} to page {target_page_id} rank {target_rank_int}")
        else:
            response_data.update({
                "rank_operation": "skipped"
            })
            log(f"Successfully moved video {video_id} from page {source_page_id} rank {source_rank_int} to page {target_page_id}")
        
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()
