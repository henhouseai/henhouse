"""Check maintenance daemon status - cross-platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hh.deploy.utils import detect_project_context
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


def _get_worker_path(project_name: str, is_deployed: bool, project_root: Path) -> Path:
    """Get path to worker script based on deployment mode."""
    if is_deployed:
        return Path(f"/srv/{project_name}/{project_name}_maintenance.py")
    else:
        return project_root / "hh" / "deploy" / "maintenance" / "worker.py"


def _get_process_filter(project_name: str, is_deployed: bool) -> str:
    """Get process name filter based on deployment mode."""
    if is_deployed:
        return f"{project_name}_maintenance.py"
    else:
        return "worker.py"


def status_maintenance_process(project_name: str) -> Dict[str, Any]:
    trace_in()
    gateway = get_gateway()
    
    if not gateway.os:
        warn("ProcessManager not available (psutil not installed)")
        report_error("action", "ProcessManager not available - install psutil")
        trace_out()
        return {"status": "error", "error": "ProcessManager not available"}
    
    pm = gateway.os
    project_root = pm.find_project_root()
    is_deployed = pm.is_deployed(project_name)
    
    worker_path = _get_worker_path(project_name, is_deployed, project_root)
    process_filter = _get_process_filter(project_name, is_deployed)
    
    # Check if worker exists
    if not worker_path.exists():
        trace_out()
        return {
            "status": "not_found",
            "error": f"Worker not found: {worker_path}",
            "deployed": is_deployed,
        }
    
    # Find running processes
    processes = pm.list_processes(process_filter)
    
    if processes:
        pids = [p["pid"] for p in processes]
        trace_out()
        return {
            "status": "running",
            "pids": pids,
            "deployed": is_deployed,
            "worker_path": str(worker_path),
        }
    
    trace_out()
    return {
        "status": "stopped",
        "deployed": is_deployed,
        "worker_path": str(worker_path),
    }


def run_maintenance_status(project_name: str) -> Dict[str, Any]:
    trace_in()
    result = status_maintenance_process(project_name)
    trace_out()
    return result


@register_action("maintenance_status")
@register_command("maintenance_status")
def maintenance_status() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    project_name, _ = detect_project_context()
    result = run_maintenance_status(project_name)
    gateway.response.set_action_response(success_payload(result))

    trace_out()
    return not is_error()
