"""Start maintenance daemon - cross-platform."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict

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


def _get_log_file(project_name: str, is_deployed: bool, project_root: Path) -> Path:
    """Get log file path based on deployment mode."""
    if is_deployed:
        logs_dir = Path(f"/srv/{project_name}/logs")
    else:
        logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"maintenance_{project_name}.log"


def _get_process_filter(project_name: str, is_deployed: bool) -> str:
    """Get process name filter based on deployment mode."""
    if is_deployed:
        return f"{project_name}_maintenance.py"
    else:
        return "worker.py"


def start_maintenance_process(project_name: str) -> Dict[str, Any]:
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
    
    # Check privileges on deployed systems
    if is_deployed and not pm.is_privileged():
        warn("Maintenance commands require sudo privileges on deployed systems")
        report_error("action", "Maintenance commands require sudo privileges")
        trace_out()
        return {"status": "error", "error": "Requires sudo privileges"}
    
    worker_path = _get_worker_path(project_name, is_deployed, project_root)
    log_file = _get_log_file(project_name, is_deployed, project_root)
    process_filter = _get_process_filter(project_name, is_deployed)
    
    # Check worker exists
    if not worker_path.exists():
        result = {
            "status": "not_found",
            "error": f"Worker not found: {worker_path}",
        }
        trace_out()
        return result
    
    # Stop existing processes
    existing = pm.list_processes(process_filter)
    for proc in existing:
        pid = proc["pid"]
        log(f"Stopping existing maintenance process PID {pid}")
        pm.kill_process(pid)
    
    # Determine user for deployed mode
    user = f"{project_name}_root" if is_deployed else None
    
    # Determine working directory
    if is_deployed:
        cwd = f"/srv/{project_name}"
    else:
        cwd = str(project_root)
    
    # Build command
    cmd = [sys.executable, str(worker_path)]
    
    # Start the process
    debug(f"Starting maintenance daemon: {cmd} (cwd={cwd}, log={log_file}, user={user})")
    pid = pm.start_background_process(
        cmd=cmd,
        cwd=cwd,
        log_file=str(log_file),
        user=user,
    )
    
    if not pid:
        result = {"status": "failed", "error": "Failed to start process"}
        trace_out()
        return result
    
    # Wait a moment and verify
    time.sleep(1)
    running = pm.list_processes(process_filter)
    
    if running:
        final_result: dict[str, str | list[int] | bool] = {
            "status": "started",
            "log_file": str(log_file),
            "pids": [p["pid"] for p in running],
            "deployed": is_deployed,
        }
        if user:
            final_result["user"] = user
        return final_result
    else:
        return {"status": "failed", "error": "Process not found after start"}


def run_maintenance_start(project_name: str) -> Dict[str, Any]:
    trace_in()
    result = start_maintenance_process(project_name)
    trace_out()
    return result


@register_action("maintenance_start")
@register_command("maintenance_start")
def maintenance_start() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    project_name, _ = detect_project_context()
    result = run_maintenance_start(project_name)
    gateway.response.set_action_response(success_payload(result))

    if result.get("status") in {"failed", "error", "not_found"}:
        report_error("action", f"Maintenance start failed: {result.get('error', result.get('status'))}")

    trace_out()
    return not is_error()
