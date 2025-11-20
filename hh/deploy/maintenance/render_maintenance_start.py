from hh.gateway.registry.registry import register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.response.json_standard import get_data
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section, safe_str

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


def render_maintenance_block(source_data, lines):
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_maintenance_block")
        trace_out()
        return

    block = "maintenance"
    if gateway.is_no(block):
        trace_out()
        return

    data_table = TableData()
    data_table.add_row("maintenance_status_header", name="")

    status = source_data.get("status", "unknown")
    if status == "started":
        data_table.add_row("daemon_started", name="Maintenance daemon started")
    elif status == "failed":
        data_table.add_row("daemon_failed", name="Maintenance daemon failed to start")
    elif status == "error":
        error_msg = source_data.get("error", "Unknown error")
        data_table.add_row("daemon_failed", name=safe_str(error_msg))
    elif status == "not_deployed":
        data_table.add_row("daemon_not_deployed", name="Maintenance script not deployed")
    elif status == "user_not_found":
        data_table.add_row("daemon_not_found", name="Root tier user not found")
    else:
        data_table.add_row("daemon_running", name=f"Status: {status}")

    lines.append(
        render_block(
            data_table,
            FieldConfig()
            .add_header("maintenance_status_header")
            .add_simple(
                [
                    "daemon_started",
                    "daemon_failed",
                    "daemon_not_deployed",
                    "daemon_not_found",
                    "daemon_running",
                ]
            ),
            table_overrides={"margin_l": 4},
            block_type=block,
        )
    )
    break_section(lines)
    trace_out()


@register_parser("maintenance_start")
def maintenance_start() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data)
    lines = [render_header_block("l_maintenance_start_header")]
    render_maintenance_block(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Maintenance start parser output length: {len(result)}")
    trace_out()
    return True


