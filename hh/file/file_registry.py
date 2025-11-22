from __future__ import annotations

from typing import Optional, Dict, Any
import json
import datetime as dt

from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hh.file.file import File

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


_file_cache: Dict[int, Any] = {}


def _deserialize_json_blob(blob, default):
    if blob in (None, '', b''):
        return default
    if isinstance(blob, (bytes, bytearray)):
        blob = blob.decode('utf-8')
    if isinstance(blob, str):
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            return default
    if isinstance(blob, (dict, list)):
        return blob
    return default


def _normalize_dt(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    if isinstance(value, str):
        try:
            return dt.datetime.fromisoformat(value)
        except ValueError:
            return None
    return None

@db_read
def _get_cache_row(conn, file_id: int) -> Optional[Dict[str, Any]]:
    query = """
        SELECT id, pages, cache_built_at
        FROM files
        WHERE id = %s
    """
    results = r_query(conn, query, [file_id], use_secondary=True)
    return results[0] if results else None


def _hydrate_file_from_cache(file_obj: "File", cache_row: Optional[Dict[str, Any]]) -> bool:
    if not cache_row:
        return False
    
    # Check staleness using main database timestamps (both loaded from main DB in do_init)
    cache_built_at_dt = _normalize_dt(file_obj.cache_built_at)
    last_modified_dt = _normalize_dt(file_obj.last_modified)

    if last_modified_dt and cache_built_at_dt and cache_built_at_dt < last_modified_dt:
        debug(f"Cache for file {file_obj.id} is stale (cache_built_at={cache_built_at_dt}, last_modified={last_modified_dt})")
        return False
    
    # If cache_built_at is NULL in main DB, cache doesn't exist yet
    if cache_built_at_dt is None:
        debug(f"Cache for file {file_obj.id} does not exist (cache_built_at is NULL)")
        return False

    # Load expensive pre-computed data from cache database directly into live fields
    file_obj.pages = _deserialize_json_blob(cache_row.get('pages'), [])
    file_obj.cache_hydrated = True
    debug(f"Hydrated file {file_obj.id} from cache (built_at={file_obj.cache_built_at})")
    return True


@db_read
def get_file(conn, file_id: int) -> Optional["File"]:
    trace_in()
    if not file_id or file_id <= 0:
        warn(f"Invalid file ID: {file_id}")
        report_error("action", f"Invalid file ID: {file_id}")
    if not is_error() and file_id in _file_cache:
        trace_out()
        return _file_cache[file_id]
    if not is_error():
        query = "SELECT id FROM files WHERE id = %s"
        results = r_query(conn, query, [file_id])
        if not results:
            warn(f"File {file_id} not found")
            report_error("action", f"File {file_id} not found")
    if not is_error():
        from hh.file.file import File

        try:
            file_instance = File(file_id=file_id)
        except Exception as exc:  # noqa: BLE001
            warn(f"Failed to load file {file_id}: {exc}")
            report_error("backend", f"Failed to load file {file_id}: {exc}")
    if not is_error():
        cache_row = _get_cache_row(conn, file_id)
        if cache_row:
            _hydrate_file_from_cache(file_instance, cache_row)
        _file_cache[file_id] = file_instance
        log(f"Retrieved file {file_id}: '{file_instance.file_name if file_instance else 'N/A'}'")
        trace_out()
        return file_instance
    trace_out()
    return None


def get_file_conn(conn, file_id: int) -> Optional["File"]:
    """Get file with explicit connection - also hydrates from cache"""
    trace_in()
    if not file_id or file_id <= 0:
        warn(f"Invalid file ID: {file_id}")
        report_error("action", f"Invalid file ID: {file_id}")
    if not is_error():
        from hh.file.file import File

        try:
            file_instance = File(file_id=file_id, conn=conn)
        except Exception as exc:  # noqa: BLE001
            warn(f"Failed to retrieve file {file_id}: {exc}")
            report_error("backend", f"Failed to retrieve file {file_id}: {exc}")
    if not is_error():
        cache_row = _get_cache_row(conn, file_id)
        if cache_row:
            _hydrate_file_from_cache(file_instance, cache_row)
        log(f"Retrieved file {file_id} with explicit connection: '{file_instance.file_name if file_instance else 'N/A'}'")
        trace_out()
        return file_instance
    trace_out()
    return None

