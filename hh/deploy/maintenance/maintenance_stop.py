import os
import subprocess
import signal
from typing import Dict, Any, List

from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.deploy.utils import detect_project_context

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


def _ensure_root():
    if os.geteuid() != 0:
        warn("Maintenance commands require sudo privileges to switch Unix users")
        report_error("action", "Maintenance commands require sudo privileges")
        return False
    return True


def stop_maintenance_processes(project_name: str) -> Dict[str, Any]:
    trace_in()
    try:
        cmd = ["ps", "aux"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        lines = result.stdout.splitlines()
        pids_to_kill: List[int] = []
        for line in lines:
            if f"{project_name}_maintenance.py" in line and "python" in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pids_to_kill.append(int(parts[1]))
                    except ValueError:
                        pass

        if not pids_to_kill:
            trace_out()
            return {"status": "not_running"}

        killed = []
        for pid in pids_to_kill:
            try:
                os.kill(pid, signal.SIGTERM)
                killed.append(pid)
                log(f"Stopped maintenance PID {pid}")
            except ProcessLookupError:
                log(f"Maintenance PID {pid} already terminated")
            except Exception as exc:
                warn(f"Failed to stop PID {pid}: {exc}")

        trace_out()
        return {"status": "stopped", "pids": killed}
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to stop maintenance daemon: {exc}")
        trace_out()
        return {"status": "error", "error": str(exc)}


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

    if not _ensure_root():
        trace_out()
        return False

    project_name, _ = detect_project_context()
    result = run_maintenance_stop(project_name)
    gateway.response.set_action_response(success_payload(result))

    if result.get("status") == "error":
        report_error("action", "Failed to stop maintenance daemon")

    trace_out()
    return not is_error()


