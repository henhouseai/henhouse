from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import success_payload, get_data
from hh.video.video_registry import get_video
from hh.video.video_quality_tiers import VIDEO_QUALITY_TIERS, VIDEO_STANDARD_EXTENSION, VIDEO_STANDARD_MIME_TYPE
from hh.video.video_utils import transcode_to_mp4
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.maint.job_queue import claim_next_maintenance_job, update_maintenance_job
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

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


@register_command("video_transcode")
@register_action("video_transcode")
def video_transcode() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("request", "No gateway available")
        trace_out()
        return False

    # Claim a video_transcode job
    job = claim_next_maintenance_job("video_transcode")
    
    if not job:
        log("No video_transcode job available")
        gateway.response.set_action_response(
            success_payload({
                "operation": "video_transcode",
                "job_id": None,
                "video_id": None,
                "done": True,
                "message": "No job available",
            })
        )
        trace_out()
        return True
    
    job_id = job["id"]
    payload = job.get("payload") or {}
    
    video_id = payload.get("video_id")
    
    if not video_id:
        warn(f"Job {job_id} missing required payload field: video_id")
        report_error("request", f"Job {job_id} missing required payload field: video_id")
        trace_out()
        return False
    
    log(f"Processing video_transcode job {job_id} for video {video_id}")
    
    # Get video object
    video = get_video(video_id)
    if not video:
        warn(f"Video {video_id} could not be loaded")
        report_error("registry", f"Video {video_id} could not be loaded")
        trace_out()
        return False
    
    # Get instances to find the 'full' instance
    instances = video.get_instances()
    full_instance = None
    for instance in instances:
        if instance.get('instance_type') == 'full':
            full_instance = instance
            break
    
    if not full_instance:
        warn(f"No 'full' instance found for video {video_id}")
        report_error("action", f"No 'full' instance found for video {video_id}")
        trace_out()
        return False
    
    # Check which instances already exist
    existing_types = {inst.get('instance_type') for inst in instances}
    tiers_to_create = []
    for tier_name in VIDEO_QUALITY_TIERS.keys():
        if tier_name not in existing_types:
            tiers_to_create.append(tier_name)
    
    if not tiers_to_create:
        log(f"Video {video_id} already has all quality tiers, marking job as done")
        gateway.response.set_action_response(
            success_payload({
                "operation": "video_transcode",
                "job_id": job_id,
                "video_id": video_id,
                "done": True,
                "message": "All quality tiers already exist",
            })
        )
        trace_out()
        return True
    
    # Get file paths
    try:
        project_name, _ = detect_project_context()
        base_path = Path(f"/srv/video/{project_name}")
        source_rel_path = full_instance.get('file_path')
        if not source_rel_path:
            warn(f"No file_path in full instance for video {video_id}")
            report_error("action", f"No file_path in full instance for video {video_id}")
            trace_out()
            return False
        
        source_path = base_path / source_rel_path
        if not source_path.exists():
            warn(f"Source file not found: {source_path}")
            report_error("action", f"Source file not found: {source_path}")
            trace_out()
            return False
        
        # Process each quality tier
        created_count = 0
        from hh.video.video_utils import get_video_info
        
        for tier_name in tiers_to_create:
            tier_config = VIDEO_QUALITY_TIERS.get(tier_name, {})
            width = tier_config.get('width')
            height = tier_config.get('height')
            bitrate = tier_config.get('bitrate', 2500)
            
            # Generate destination path (same directory, different extension and tier suffix)
            source_path_obj = Path(source_path)
            # First tier in config gets base filename, others get tier suffix
            tier_names = list(VIDEO_QUALITY_TIERS.keys())
            if tier_name == tier_names[0]:
                # First tier uses base name with standard extension
                dest_path = source_path_obj.with_suffix(VIDEO_STANDARD_EXTENSION)
            else:
                # Other tiers add tier name to filename
                stem = source_path_obj.stem
                dest_path = source_path_obj.parent / f"{stem}_{tier_name}{VIDEO_STANDARD_EXTENSION}"
            
            dest_rel_path = str(dest_path.relative_to(base_path))
            
            log(f"Transcoding video {video_id} tier '{tier_name}': {source_path} -> {dest_path} (H.264 {width}x{height if height else 'auto'} {bitrate}kbps)")
            success = transcode_to_mp4(str(source_path), str(dest_path), width=width, height=height, bitrate=bitrate)
            
            if not success:
                warn(f"Transcoding failed for video {video_id} tier '{tier_name}'")
                # Continue with other tiers even if one fails
                continue
            
            # Get file size and metadata of transcoded file
            size_bytes = dest_path.stat().st_size
            video_info = get_video_info(str(dest_path))
            transcoded_width = video_info.get('width') if video_info else (width or full_instance.get('width'))
            transcoded_height = video_info.get('height') if video_info else (height or full_instance.get('height'))
            transcoded_duration = video_info.get('duration_seconds') if video_info else full_instance.get('duration_seconds')
            transcoded_bitrate = video_info.get('bitrate') if video_info else bitrate
            
            # Create instance entry
            video.add_video_instance(
                instance_type=tier_name,
                file_path=dest_rel_path,
                mime_type=VIDEO_STANDARD_MIME_TYPE,
                size_bytes=size_bytes,
                width=transcoded_width,
                height=transcoded_height,
                duration_seconds=transcoded_duration,
                bitrate=transcoded_bitrate
            )
            created_count += 1
            log(f"Successfully created '{tier_name}' instance for video {video_id}")
        
        if created_count == 0:
            warn(f"Failed to create any quality tiers for video {video_id}")
            report_error("action", f"Failed to create any quality tiers for video {video_id}")
            trace_out()
            return False
        
        # Flag video modification
        video.flag_video_modification(f"{created_count} quality tier(s) transcoded")
        
        log(f"Successfully transcoded video {video_id}: created {created_count} quality tier(s)")
        gateway.response.set_action_response(
            success_payload({
                "operation": "video_transcode",
                "job_id": job_id,
                "video_id": video_id,
                "done": True,
                "message": f"Transcoding completed: {created_count} tier(s) created",
            })
        )
        trace_out()
        return True
    except Exception as e:
        warn(f"Error during video transcoding: {str(e)}")
        report_error("action", f"Error during video transcoding: {str(e)}")
        trace_out()
        return False


@register_parser("video_transcode")
def video_transcode_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})
        job_id = source_data.get("job_id")
        video_id = source_data.get("video_id")
        done = source_data.get("done", False)
        error_occurred = is_error()
        
        conn = gateway.conn
        
        # Update job table if we have a job_id
        if job_id and conn:
            if error_occurred:
                update_maintenance_job(
                    job_id=job_id,
                    status="error",
                )
                log(f"Set job {job_id} status to error")
            elif done:
                update_maintenance_job(
                    job_id=job_id,
                    status="done",
                )
                log(f"Set job {job_id} status to done")
        
        # Render output
        lines = [render_header_block("video_transcode_header")]
        
        table = TableData()
        table.add_row(
            "video_transcode_header",
            info="",
        )
        
        if done:
            if video_id:
                table.add_row(
                    "video_transcode_complete",
                    info=f"Video {video_id}: {source_data.get('message', 'Transcoding completed')}",
                )
            else:
                table.add_row(
                    "no_job_available",
                    info=source_data.get("message", "No job available"),
                )
        elif error_occurred:
            table.add_row(
                "video_transcode_error",
                info="An error occurred during transcoding",
            )
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("video_transcode_header")
                .add_simple(["video_transcode_complete", "no_job_available"])
                .add_simple_color("video_transcode_error", "red"),
                block_type="maintenance",
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


register_maintenance_tool("video_transcode")
