import os
import subprocess
from typing import Dict, Any, List

from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
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


def status_maintenance_process(project_name: str) -> Dict[str, Any]:
    trace_in()
    try:
        app_path = f"/srv/{project_name}/{project_name}_maintenance.py"
        if not os.path.exists(app_path):
            trace_out()
            return {"status": "not_deployed", "error": f"File not found: {app_path}"}

        cmd = ["ps", "aux"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        lines = result.stdout.splitlines()
        pids: List[int] = []
        for line in lines:
            if f"{project_name}_maintenance.py" in line and "python" in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pids.append(int(parts[1]))
                    except ValueError:
                        pass

        if pids:
            trace_out()
            return {"status": "running", "pids": pids}

        trace_out()
        return {"status": "stopped"}
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to fetch maintenance status: {exc}")
        trace_out()
        return {"status": "error", "error": str(exc)}


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


