"""Stop maintenance daemon - cross-platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.response.json_standard import success_payload

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


def _get_process_filter(project_name: str, is_deployed: bool) -> str:
    """Get process name filter based on deployment mode."""
    if is_deployed:
        return f"{project_name}_maintenance.py"
    else:
        return "worker.py"


def stop_maintenance_processes(project_name: str) -> Dict[str, Any]:
    trace_in()
    gateway = get_gateway()
    
    if not gateway.os:
        warn("ProcessManager not available (psutil not installed)")
        report_error("action", "ProcessManager not available - install psutil")
        trace_out()
        return {"status": "error", "error": "ProcessManager not available"}
    
    pm = gateway.os
    is_deployed = pm.is_deployed(project_name)
    process_filter = _get_process_filter(project_name, is_deployed)
    
    # Find running processes
    processes = pm.list_processes(process_filter)
    
    if not processes:
        trace_out()
        return {"status": "not_running"}
    
    # Kill each process
    killed: List[int] = []
    for proc in processes:
        pid = proc["pid"]
        if pm.kill_process(pid):
            killed.append(pid)
            log(f"Stopped maintenance PID {pid}")
        else:
            warn(f"Failed to stop PID {pid}")
    
    trace_out()
    return {"status": "stopped", "pids": killed}


def run_maintenance_stop(project_name: str) -> Dict[str, Any]:
    trace_in()
    result = stop_maintenance_processes(project_name)
    trace_out()
    return result


@register_action("maintenance_stop")
@register_command("maintenance_stop")
def maintenance_stop() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    project_name, _ = detect_project_context()
    result = run_maintenance_stop(project_name)
    gateway.response.set_action_response(success_payload(result))

    if result.get("status") == "error":
        report_error("action", "Failed to stop maintenance daemon")

    trace_out()
    return not is_error()
