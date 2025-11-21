from __future__ import annotations

from typing import Optional

from hh.deploy.maint.job_queue import update_maintenance_job
from hh.gateway.connection.connection import HenhouseConnection, get_connection, load_dsn_pair
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.response.json_standard import success_payload
from hh.page.page_registry import get_page_conn
from hh.gateway.error.error_store import report_error, is_error


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


def _open_connection_bundle() -> Optional[HenhouseConnection]:
    primary_dsn, cache_dsn = load_dsn_pair()
    if not primary_dsn or not cache_dsn:
        report_error("connection", "Unable to load DSN pair")
        return None
    primary_conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
    cache_conn = get_connection(dict_cursor=True, dsn_override=cache_dsn)
    if not primary_conn or not cache_conn:
        report_error("connection", "Failed to open maintenance connections")
        if primary_conn:
            primary_conn.close()
        if cache_conn:
            cache_conn.close()
        return None
    return HenhouseConnection(primary_conn, cache_conn)


def _close_connection_bundle(bundle: Optional[HenhouseConnection]) -> None:
    if not bundle:
        return
    for conn in (bundle.primary, bundle.secondary):
        try:
            conn.commit()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@register_command("regex_text")
@register_action("regex_text")
def regex_text() -> bool:
    gateway = get_gateway()
    if not gateway:
        report_error("request", "No gateway available")
        return False

    page_id = _parse_int(gateway.get_arg("page_id"), "page_id")
    old_name = gateway.get_arg("old_name")
    new_name = gateway.get_arg("new_name")
    last_page_id = _parse_int(gateway.get_arg("last_page_id") or "0", "last_page_id") or 0
    batch_limit = _parse_int(gateway.get_arg("batch_limit") or "25", "batch_limit") or 25

    if not old_name or not new_name:
        report_error("request", "Both old_name and new_name are required")

    job_id = gateway.get_arg("job_id")

    if is_error():
        return False

    conn_bundle = _open_connection_bundle()
    if not conn_bundle:
        return False

    try:
        page_obj = get_page_conn(conn_bundle, page_id)
        if not page_obj:
            report_error("registry", f"Page {page_id} could not be loaded")
            return False

        result = page_obj.maintenance_process_name_change(
            old_name=old_name,
            new_name=new_name,
            last_page_id=last_page_id,
            batch_limit=batch_limit,
        )

        if job_id and (result["processed"] or result["done"]):
            primary_conn = conn_bundle.primary
            update_maintenance_job(
                primary_conn,
                int(job_id),
                status="done" if result["done"] else "running",
                progress=result,
            )

        gateway.response.set_action_response(
            success_payload(
                {
                    "operation": "regex_text",
                    "page_id": page_id,
                    "old_name": old_name,
                    "new_name": new_name,
                    "result": result,
                }
            )
        )
        return not is_error()
    finally:
        _close_connection_bundle(conn_bundle)


register_maintenance_tool("regex_text")

