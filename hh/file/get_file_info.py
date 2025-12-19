from __future__ import annotations
from typing import Mapping, cast, Any

from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.download import register_download_tool
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import safe_str
from hh.file.file_registry import get_file

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message=None: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_action("get_file_info")
@register_command("get_file_info")
def get_file_info_action() -> bool:
    trace_in()
    gateway = get_gateway()
    file_id_arg = gateway.get_arg("file_id") or gateway.get_arg("id")
    if not file_id_arg:
        warn("No file ID provided")
        report_error("action", "File ID is required")
        trace_out()
        return False

    try:
        file_id = int(file_id_arg)
    except ValueError:
        report_error("action", f"Invalid file ID: {file_id_arg}")
        trace_out()
        return False

    file_obj = get_file(file_id=file_id)
    if not file_obj:
        report_error("action", f"File {file_id} not found")
        trace_out()
        return False

    data = file_obj.get_file_data()
    payload = {"file": data}
    gateway.response.set_action_response(success_payload(payload))
    log(f"Retrieved file info for {data.get('id')}")

    trace_out()
    return not is_error()


@register_parser("get_file_info")
def get_file_info_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        action_response = gateway.response.get_action_response()
        if action_response is None:
            warn("Action response is None")
            report_error("backend", "Action response is None")
            trace_out()
            return False
        source_data = get_data(cast(Mapping[str, Any], action_response))
        file_data = (source_data or {}).get("file", {})

        lines = [render_header_block("l_file_info_header")]

        table = TableData()
        table.add_row("file_info_header", info="")
        table.add_row("file_id", info=safe_str(file_data.get("id")))
        table.add_row("file_name", info=safe_str(file_data.get("file_name")))
        table.add_row("file_path", info=safe_str(file_data.get("file_path")))
        table.add_row("file_mime", info=safe_str(file_data.get("mime_type")))
        table.add_row("file_size_bytes", info=safe_str(file_data.get("size_bytes")))
        table.add_row("file_visibility", info=safe_str(file_data.get("visibility")))
        table.add_row("file_uploaded", info=safe_str(file_data.get("uploaded")))
        table.add_row("file_last_modified", info=safe_str(file_data.get("last_modified")))

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("file_info_header")
                .add_simple(
                    [
                        "file_id",
                        "file_name",
                        "file_path",
                        "file_mime",
                        "file_size_bytes",
                        "file_visibility",
                        "file_uploaded",
                        "file_last_modified",
                    ]
                ),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        gateway.response.add_output(finalize_output(lines))
        log("get_file_info parser completed successfully")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False


register_download_tool("get_file_info")

