import os
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional, Union
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

ENVELOPE_VERSION = "2.0"
STATUS_OK = "ok"
STATUS_ERROR = "err"
STATUS_PARTIAL = "partial"

from typing import TypedDict

class ErrorPayload(TypedDict, total=False):
    msg: str
    cod: str
    ret: bool
    src: str
    info: Dict[str, Any]

class SuccessEnvelope(TypedDict, total=False):
    sta: str
    tim: str
    ver: str
    met: Dict[str, Any]
    dat: Dict[str, Any]

class ErrorEnvelope(TypedDict, total=False):
    sta: str
    tim: str
    ver: str
    met: Dict[str, Any]
    err: ErrorPayload

class PartialEnvelope(TypedDict, total=False):
    sta: str
    tim: str
    ver: str
    met: Dict[str, Any]
    dat: Dict[str, Any]
    err: ErrorPayload

Envelope = Union[SuccessEnvelope, ErrorEnvelope, PartialEnvelope]

from hh.gateway.connection.utils import iso_now

def _create_base_envelope(meta: Optional[Dict[str, Any]] = None) -> OrderedDict[str, Any]:
    envelope: OrderedDict[str, Any] = OrderedDict()
    envelope["tim"] = iso_now()
    envelope["ver"] = ENVELOPE_VERSION
    if meta:
        envelope["met"] = dict(meta)
    return envelope

def success_payload(
    data: Mapping[str, Any], 
    *, 
    meta: Optional[Mapping[str, Any]] = None,
    rid: Optional[str] = None
) -> Dict[str, Any]:
    trace_in()
    envelope = {
        "content": [
            {
                "type": "text",
                "text": dict(data)
            }
        ]
    }
    log(f"Created success payload with {len(data)} data keys")
    trace_out()
    return envelope

def is_success(envelope: Mapping[str, Any]) -> bool:
    return envelope.get("sta") == STATUS_OK

def is_error(envelope: Mapping[str, Any]) -> bool:
    return envelope.get("sta") == STATUS_ERROR

def is_partial(envelope: Mapping[str, Any]) -> bool:
    return envelope.get("sta") == STATUS_PARTIAL

def get_data(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    # MCP RPC format: extract from content[0].text
    if "content" in envelope and isinstance(envelope["content"], list) and len(envelope["content"]) > 0:
        content_item = envelope["content"][0]
        if content_item.get("type") == "text" and "text" in content_item:
            return content_item["text"]
    # Fallback to old Gateway format for backward compatibility
    return envelope.get("dat", {})

def get_error(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    return envelope.get("err", {})

def get_meta(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    return envelope.get("met", {})

def with_count(iterable: Any) -> Dict[str, Any]:
    trace_in()
    try:
        count = len(iterable)
        log(f"Counted {count} items in iterable")
        trace_out()
        return {"cnt": count}
    except (TypeError, AttributeError):
        log("Could not count items in iterable (not iterable)")
        trace_out()
        return {}

def ensure_success(envelope: Mapping[str, Any]) -> None:
    trace_in()
    if not is_success(envelope):
        error_info = get_error(envelope)
        message = error_info.get("msg", "Unknown error")
        code = error_info.get("cod", "unknown")
        log(f"Ensuring success failed: {code} - {message}")
        trace_out()
        raise ValueError(f"Operation failed ({code}): {message}")
    log("Envelope is successful")
    trace_out()

ERROR_CODES = {
    "db_conn": {"message": "Database connection failed", "retryable": True, "source": "db"},
    "db_dead": {"message": "Database deadlock detected", "retryable": True, "source": "db"},
    "db_constraint": {"message": "Database constraint violation", "retryable": False, "source": "db"},
    "db_permission": {"message": "Database access denied", "retryable": False, "source": "db"},
    "db_execution": {"message": "Database execution error", "retryable": False, "source": "db"},
    "db_table_missing": {"message": "Database table does not exist", "retryable": False, "source": "db"},
    "db_column_missing": {"message": "Database column does not exist", "retryable": False, "source": "db"},
    "db_foreign_key": {"message": "Foreign key constraint violation", "retryable": False, "source": "db"},
    "db_syntax": {"message": "SQL syntax error", "retryable": False, "source": "db"},
    "db_connection_lost": {"message": "Database connection lost", "retryable": True, "source": "db"},
    "val_required": {"message": "Required field missing", "retryable": False, "source": "validation"},
    "val_format": {"message": "Invalid format", "retryable": False, "source": "validation"},
    "sys_unk": {"message": "Unknown system error", "retryable": False, "source": "system"},
    "partial_success": {"message": "Partial success with warnings", "retryable": False, "source": "business"},
    "net_timeout": {"message": "Network timeout", "retryable": True, "source": "network"},
    "auth_failed": {"message": "Authentication failed", "retryable": False, "source": "auth"},
}

def resolve_error(code: str) -> tuple[str, bool, str]:
    trace_in()
    error_info: Dict[str, Any] = ERROR_CODES.get(code, ERROR_CODES["sys_unk"])
    message: str = error_info.get("message", "Unknown error")
    retryable: bool = error_info.get("retryable", False)
    source: str = error_info.get("source", "system")
    log(f"Resolved error code: {code} -> {message[:50]}...")
    trace_out()
    return message, retryable, source

def has_error_and_data(envelope: Mapping[str, Any]) -> bool:
    if not is_error(envelope):
        return False
    business_data_keys = set(envelope.keys()) - {"tim", "ver", "sta", "met", "err"}
    return len(business_data_keys) > 0

def extract_error_only(envelope: Mapping[str, Any]) -> Envelope:
    if not is_error(envelope):
        # Type cast for mypy - envelope should match Envelope structure
        return envelope  # type: ignore[return-value]
    err_payload: Dict[str, Any] = envelope.get("err", {})
    if not isinstance(err_payload, dict):
        err_payload = {}
    return _create_error_envelope(envelope, err_payload)

def split_error_envelope(envelope: Mapping[str, Any]) -> tuple[Optional[Envelope], Optional[Envelope]]:
    trace_in()
    if not isinstance(envelope, dict) or not is_error(envelope):
        log("Envelope is not an error envelope, returning as-is")
        trace_out()
        # Type cast for mypy - envelope should match Envelope structure
        return None, envelope  # type: ignore[return-value]
    error_payload: Dict[str, Any] = envelope.get("err", {})
    if not error_payload or not isinstance(error_payload, dict):
        log("No error payload found, returning as-is")
        trace_out()
        # Type cast for mypy - envelope should match Envelope structure
        return None, envelope  # type: ignore[return-value]
    remaining_data: Dict[str, Any] = {}
    for key, value in envelope.items():
        if key not in {"tim", "ver", "sta", "met", "err"}:
            remaining_data[key] = value
    error_envelope = _create_error_envelope(envelope, error_payload)
    success_envelope: Optional[Envelope] = None
    if remaining_data:
        # _create_success_envelope returns Dict, but we need Envelope
        # For now, cast it since the structure matches
        success_envelope = _create_success_envelope(envelope, remaining_data)  # type: ignore[assignment]
        log(f"Split envelope: error + success with {len(remaining_data)} data keys")
    else:
        log("Split envelope: error only")
    trace_out()
    return error_envelope, success_envelope

def _create_error_envelope(original: Mapping[str, Any], error_payload: Mapping[str, Any]) -> Envelope:
    envelope = _create_base_envelope(
        meta=original.get("met", {})
    )
    envelope["sta"] = STATUS_ERROR
    envelope["err"] = dict(error_payload)
    # Type cast for mypy - OrderedDict matches Envelope structure
    return envelope  # type: ignore[return-value]

def _create_success_envelope(original: Mapping[str, Any], data: Mapping[str, Any]) -> Dict[str, Any]:
    envelope: Dict[str, Any] = {
        "content": [
            {
                "type": "text",
                "text": dict(data)
            }
        ]
    }
    return envelope
