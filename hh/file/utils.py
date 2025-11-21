from __future__ import annotations

import mimetypes
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from uuid import uuid4

from hh.deploy.utils import detect_project_context
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.image.utils import create_date_directory

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


def _sanitize_filename(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in (".", "_", "-", " ") else "-" for ch in name)
    safe = safe.strip()
    return safe or "file"


def store_uploaded_file(temp_path: str, original_filename: str) -> Tuple[str, str, int, str]:
    """
    Copy the uploaded file into the /srv/files/{project}/{Y}/{m}/{d} hierarchy.
    Returns (relative_path, stored_filename, size_bytes, mime_type).
    """
    trace_in()
    project_name, _ = detect_project_context()
    base_path = Path(f"/srv/files/{project_name}")
    base_path.mkdir(parents=True, exist_ok=True)
    os.chmod(base_path, 0o775)

    date_path = create_date_directory(base_path)

    original_name = Path(original_filename).name
    sanitized_stem = _sanitize_filename(Path(original_name).stem)
    suffix = Path(original_name).suffix
    unique_suffix = uuid4().hex[:8]
    stored_filename = f"{sanitized_stem}-{unique_suffix}{suffix}"

    destination = date_path / stored_filename
    shutil.copy2(temp_path, destination)
    os.chmod(destination, 0o664)

    relative_path = destination.relative_to(base_path).as_posix()
    size_bytes = destination.stat().st_size
    mime_type = mimetypes.guess_type(destination.name)[0] or "application/octet-stream"

    log(f"Stored file '{original_name}' as {destination} ({size_bytes} bytes, mime={mime_type})")
    trace_out()
    return relative_path, stored_filename, size_bytes, mime_type


def move_file_to_deleted(relative_path: str) -> Optional[str]:
    """
    Move the stored file into the deleted directory.
    Returns the new relative path if moved, otherwise None.
    """
    trace_in()
    try:
        project_name, _ = detect_project_context()
        base_path = Path(f"/srv/files/{project_name}")
        current_path = base_path / relative_path
        if not current_path.exists():
            warn(f"File not found for soft delete: {current_path}")
            trace_out()
            return None

        deleted_path = base_path / "deleted"
        deleted_path.mkdir(parents=True, exist_ok=True)
        os.chmod(deleted_path, 0o775)

        destination = deleted_path / current_path.name
        shutil.move(str(current_path), destination)
        os.chmod(destination, 0o664)
        log(f"Moved file to deleted folder: {current_path} -> {destination}")
        trace_out()
        return destination.relative_to(base_path).as_posix()
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to move file to deleted folder: {exc}")
        trace_out()
        return None

