from __future__ import annotations

from pathlib import Path
from typing import List

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page

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


def _collect_file_args(gateway) -> List[dict]:
    files: List[dict] = []
    index = 0
    while True:
        path_key = f"file{index}_path"
        name_key = f"file{index}_name"
        if not gateway.is_set(path_key):
            break
        if not gateway.is_set(name_key):
            warn(f"File {index} missing name argument")
            report_error("action", f"File {index} name is required")
            break
        temp_path = gateway.get_arg(path_key)
        original_name = gateway.get_arg(name_key)
        description_key = f"file{index}_description"
        description = gateway.get_arg(description_key) if gateway.is_set(description_key) else None
        files.append(
            {
                "temp_path": temp_path,
                "original_name": original_name,
                "description": description,
            }
        )
        index += 1
    return files


@register_action("upload_files")
@register_command("upload_files")
def upload_files() -> bool:
    trace_in()
    gateway = get_gateway()
    page_id_arg = gateway.get_arg("page_id") or gateway.get_arg("id")
    if not page_id_arg:
        warn("No page ID provided")
        report_error("action", "Page ID is required")

    files = _collect_file_args(gateway)
    if not files:
        warn("No files provided for upload")
        report_error("action", "At least one file is required")

    page_id: int = 0
    if not is_error():
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be an integer")

    page = None
    if not is_error():
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")

    uploaded_ids: List[int] = []
    if not is_error() and page is not None:
        for idx, file_entry in enumerate(files):
            temp_path = file_entry["temp_path"]
            original_name = file_entry["original_name"]
            description = file_entry["description"]
            if not Path(temp_path).exists():
                warn(f"File {idx} not found at {temp_path}")
                report_error("action", f"File {idx} not found")
                break
            new_id = page.add_file(temp_path, original_name, description)
            if is_error():
                warn(f"Failed to upload file {original_name}")
                break
            if new_id is None:
                warn(f"File upload returned no ID for {original_name}")
                report_error("action", f"File upload failed for {original_name}")
                break
            uploaded_ids.append(new_id)

    updated_page = None
    if not is_error():
        updated_page = get_page(page_id=page_id)
        if not updated_page:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")

    if not is_error() and updated_page is not None:
        payload = updated_page.get_page()
        gateway.response.set_action_response(success_payload(payload))
        log(f"Uploaded {len(uploaded_ids)} file(s) to page {page_id}")

    trace_out()
    return not is_error()

