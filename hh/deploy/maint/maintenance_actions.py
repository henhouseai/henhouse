from __future__ import annotations

from typing import Optional

from hh.gateway.connection.connection import HenhouseConnection, get_connection, load_dsn_pair
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.response.json_standard import success_payload
from hh.page.page_registry import get_page_conn
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
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


def _parse_int(arg_value: Optional[str], name: str) -> Optional[int]:
    if arg_value is None:
        report_error("request", f"Missing required argument: {name}")
        return None
    try:
        parsed = int(arg_value)
        if parsed <= 0:
            raise ValueError
        return parsed
    except ValueError:
        report_error("request", f"Invalid integer for {name}: {arg_value}")
        return None


def _open_henhouse_connection() -> Optional[HenhouseConnection]:
    primary_dsn, cache_dsn = load_dsn_pair()
    if not primary_dsn or not cache_dsn:
        report_error("connection", "Unable to load DSN pair for maintenance action")
        return None
    primary_conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
    cache_conn = get_connection(dict_cursor=True, dsn_override=cache_dsn)
    if not primary_conn or not cache_conn:
        report_error("connection", "Failed to open database connections for maintenance action")
        if primary_conn:
            primary_conn.close()
        if cache_conn:
            cache_conn.close()
        return None
    return HenhouseConnection(primary_conn, cache_conn)


def _close_henhouse_connection(conn: Optional[HenhouseConnection]) -> None:
    if not conn:
        return
    try:
        conn.primary.commit()
    except Exception:
        pass
    try:
        conn.primary.close()
    except Exception:
        pass
    try:
        conn.secondary.commit()
    except Exception:
        pass
    try:
        if conn.secondary is not conn.primary:
            conn.secondary.close()
    except Exception:
        pass


@register_command("maintenance_fix_reference")
@register_action("maintenance_fix_reference")
def maintenance_fix_reference() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    source_page_id = _parse_int(gateway.get_arg("source_page_id"), "source_page_id")
    target_page_id = _parse_int(gateway.get_arg("target_page_id"), "target_page_id")
    old_name = gateway.get_arg("old_name")
    new_name = gateway.get_arg("new_name")

    if not old_name or not new_name:
        report_error("request", "Both old_name and new_name are required")

    if is_error():
        trace_out()
        return False

    conn_bundle = _open_henhouse_connection()
    if not conn_bundle:
        trace_out()
        return False

    try:
        source_page = get_page_conn(conn_bundle, source_page_id)
        if not source_page:
            report_error("registry", f"Source page {source_page_id} could not be loaded")
        if is_error():
            trace_out()
            return False

        maintenance_result = source_page.maintenance_process_name_change(
            old_name=old_name,
            new_name=new_name,
            last_page_id=max(0, target_page_id - 1),
            batch_limit=1,
        )

        data = {
            "operation": "maintenance_fix_reference",
            "source_page_id": source_page_id,
            "target_page_id": target_page_id,
            "result": maintenance_result,
        }
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return not is_error()
    except Exception as exc:  # noqa: BLE001
        warn(f"Maintenance fix failed: {exc}")
        report_error("action", f"Maintenance fix failed: {exc}")
        trace_out()
        return False
    finally:
        _close_henhouse_connection(conn_bundle)


register_maintenance_tool("maintenance_fix_reference")


@register_parser("maintenance_fix_reference")
def maintenance_fix_reference_parser() -> bool:
    """Basic CLI output for maintenance fixes."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    if not gateway.response.has_action_response():
        report_error("backend", "No action response available")
        trace_out()
        return False

    import json

    payload = gateway.response.get_action_response()
    gateway.response.add_output(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )
    trace_out()
    return True

