from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.file.file_registry import get_file

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

@register_action('move_file')
@register_command('move_file')
def move_file() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('source_page') and not gateway.is_set('s_page'):
        warn("No source page ID provided")
        report_error("action", "Source page ID is required")
    if not is_error():
        if not gateway.is_set('file_id'):
            warn("No file ID provided")
            report_error("action", "File ID is required")
    if not is_error():
        if not gateway.is_set('target_page') and not gateway.is_set('t_page'):
            warn("No target page ID provided")
            report_error("action", "Target page ID is required")
    source_page_id: int = 0
    file_id: int = 0
    target_page_id: int = 0
    if not is_error():
        # Source specification
        source_page_arg = gateway.get_arg('source_page') or gateway.get_arg('s_page')
        file_id_arg = gateway.get_arg('file_id')
        source_rank = gateway.get_arg('source_rank') or gateway.get_arg('s_rank')
        
        # Destination specification
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page')
        target_rank = gateway.get_arg('target_rank') or gateway.get_arg('t_rank')
        
        try:
            source_page_id = int(source_page_arg)
            file_id = int(file_id_arg)
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid IDs provided. Source: {source_page_arg}, File: {file_id_arg}, Target: {target_page_arg}")
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
            log(f"Source rank not provided, checking for file instances in source page {source_page_id}")
            current_files = source_page.get_files_data()
            file_instances = [f for f in current_files if f['id'] == file_id]
            
            if len(file_instances) == 0:
                warn(f"File {file_id} not found in source page {source_page_id}")
                report_error("action", f"File {file_id} not found in source page {source_page_id}")
            elif len(file_instances) > 1:
                warn(f"File {file_id} appears {len(file_instances)} times in source page {source_page_id}. Old rank must be specified.")
                report_error("action", f"File {file_id} appears {len(file_instances)} times in source page {source_page_id}. Old rank must be specified.")
            else:
                # Use the single instance's rank
                source_rank_int = file_instances[0]['file_rank']
                log(f"Using detected source rank {source_rank_int} for file {file_id}")
    
    target_page = None
    if not is_error():
        log(f"Loading target page {target_page_id}")
        target_page = get_page(page_id=target_page_id)
        if not target_page:
            warn(f"Target page {target_page_id} not found")
            report_error("action", f"Target page {target_page_id} not found")
    
    if not is_error():
        log(f"Loading file {file_id}")
        file_obj = get_file(file_id=file_id)
        if not file_obj:
            warn(f"File {file_id} not found")
            report_error("action", f"File {file_id} not found")
    
    if not is_error() and target_page is not None and source_rank_int is not None:
        log(f"Moving file {file_id} from page {source_page_id} rank {source_rank_int} to page {target_page_id}")
        # Create file instance structure for move_files
        file_instances = [{
            'file_id': file_id,
            'source_page_id': source_page_id,
            'source_rank': source_rank_int
        }]
        success = target_page.move_media_items("file", file_instances, target_rank=target_rank_int)
        if not success:
            warn(f"Failed to move file {file_id} from page {source_page_id} to page {target_page_id}")
            report_error("action", f"Failed to move file {file_id} from page {source_page_id} to page {target_page_id}")
    
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
            "moved_file_id": file_id,
            "source_page_id": source_page_id,
            "source_rank": source_rank_int,
            "operation": "move_file"
        })
        
        if target_rank_int is not None:
            response_data.update({
                "set_rank": target_rank_int,
                "rank_operation": "applied"
            })
            log(f"Successfully moved file {file_id} from page {source_page_id} rank {source_rank_int} to page {target_page_id} rank {target_rank_int}")
        else:
            response_data.update({
                "rank_operation": "skipped"
            })
            log(f"Successfully moved file {file_id} from page {source_page_id} rank {source_rank_int} to page {target_page_id}")
        
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()
