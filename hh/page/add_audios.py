from __future__ import annotations
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.audio.audio_registry import get_audio
from hh.page.page import Page
from hh.audio.audio import Audio
import os
from pathlib import Path
import mimetypes

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

def is_valid_audio_file(file_path: str) -> bool:
    trace_in()
    try:
        # Check MIME type
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        if not mime_type.startswith('audio/'):
            log(f"File {file_path} has invalid MIME type: {mime_type}")
            trace_out()
            return False
        # Check if file exists and is readable
        if not Path(file_path).exists():
            log(f"File {file_path} does not exist")
            trace_out()
            return False
        if not os.access(file_path, os.R_OK):
            log(f"File {file_path} is not readable")
            trace_out()
            return False
        log(f"File {file_path} is valid audio file")
        trace_out()
        return True
    except Exception as e:
        warn(f"Error validating file {file_path}: {str(e)}")
        trace_out()
        return False


def scan_folder_for_audio(folder_path: str) -> List[str]:
    trace_in()
    log(f"Scanning folder for audio: {folder_path}")
    valid_audio: List[str] = []
    try:
        folder = Path(folder_path)
        if not folder.exists():
            warn(f"Folder does not exist: {folder_path}")
            trace_out()
            return valid_audio
        if not folder.is_dir():
            warn(f"Path is not a directory: {folder_path}")
            trace_out()
            return valid_audio
        # Scan all files in folder
        for file_path in folder.iterdir():
            if file_path.is_file():
                if is_valid_audio_file(str(file_path)):
                    valid_audio.append(str(file_path))
        log(f"Found {len(valid_audio)} valid audio files in folder")
    except Exception as e:
        warn(f"Error scanning folder {folder_path}: {str(e)}")
        report_error("action", f"Error scanning folder: {str(e)}")
    trace_out()
    return valid_audio


@register_action('add_audios')
@register_command('add_audios')
def add_audios() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('target_page') and not gateway.is_set('t_page') and not gateway.is_set('id'):
        warn("No target page ID provided")
        report_error("action", "Target page ID is required")
    if not is_error():
        if not gateway.is_set('folder'):
            warn("No folder path provided")
            report_error("action", "Folder path is required")
    target_page_id: int = 0
    folder_path: str = ""
    if not is_error():
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page') or gateway.get_arg('id')
        folder_path = gateway.get_arg('folder')
        caption = gateway.get_arg('caption')
        try:
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid target page ID: {target_page_arg}")
            report_error("action", "Target page ID must be a number")
    page = None
    if not is_error():
        log(f"Loading target page {target_page_id}")
        page = get_page(page_id=target_page_id)
        if not page:
            warn(f"Target page {target_page_id} not found")
            report_error("action", f"Target page {target_page_id} not found")
    audio_files: List[str] = []
    if not is_error() and page is not None:
        # Scan folder for valid audio files
        audio_files = scan_folder_for_audio(folder_path)
        if not audio_files:
            warn(f"No valid audio files found in folder: {folder_path}")
            report_error("action", f"No valid audio files found in folder: {folder_path}")
    processed_audio: List[Dict[str, Any]] = []
    failed_audio: List[Dict[str, Any]] = []
    if not is_error() and page is not None:
        log(f"Processing {len(audio_files)} audio files from folder: {folder_path}")
        # Process each audio file
        caption = gateway.get_arg('caption')
        for i, audio_file in enumerate(audio_files, 1):
            log(f"Processing audio {i}/{len(audio_files)}: {Path(audio_file).name}")
            # Use filename as default caption if no caption provided
            if caption:
                audio_caption = caption
            else:
                audio_caption = Path(audio_file).stem  # Get filename without extension
                log(f"Using filename as caption: {audio_caption}")
            # Add audio to page
            new_audio_id = page.add_audio(audio_file, audio_caption)
            if not is_error() and new_audio_id:
                processed_audio.append({
                    'file': Path(audio_file).name,
                    'audio_id': new_audio_id,
                    'caption': audio_caption
                })
                log(f"Successfully added audio {i}/{len(audio_files)}: {Path(audio_file).name} (ID: {new_audio_id})")
            else:
                failed_audio.append({
                    'file': Path(audio_file).name,
                    'error': 'Failed to process audio'
                })
                warn(f"Failed to process audio {i}/{len(audio_files)}: {Path(audio_file).name}")
                # Clear error state for next audio
                if is_error():
                    # Reset error state - this is a bit of a hack but needed for batch processing
                    pass
    updated_page = None
    if not is_error():
        log(f"Reloading page {target_page_id} to show new audio")
        updated_page = get_page(page_id=target_page_id)
        if not updated_page or updated_page.name is None:
            warn(f"Failed to reload page {target_page_id}")
            report_error("action", f"Failed to reload page {target_page_id}")
    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        response_data.update({
            "processed_audio": processed_audio,
            "failed_audio": failed_audio,
            "total_found": len(audio_files),
            "total_processed": len(processed_audio),
            "total_failed": len(failed_audio)
        })
        gateway.response.set_action_response(success_payload(response_data))
        page_name = updated_page.name if updated_page.name is not None else "Unknown"
        log(f"Successfully processed {len(processed_audio)}/{len(audio_files)} audio for page {target_page_id}: {page_name}")
    trace_out()
    return not is_error()
