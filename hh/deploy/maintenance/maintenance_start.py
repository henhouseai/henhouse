import os
import subprocess
import time
import pwd
import signal
from pathlib import Path
from typing import Dict, Any

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


def _ensure_root():
    if os.geteuid() != 0:
        warn("Maintenance commands require sudo privileges to switch Unix users")
        report_error("action", "Maintenance commands require sudo privileges")
        return False
    return True


def _maintenance_log_file(project_name: str) -> str:
    logs_dir = Path(f"/srv/{project_name}/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return str(logs_dir / f"maintenance_{project_name}.log")


def start_maintenance_process(project_name: str) -> Dict[str, Any]:
    trace_in()
    try:
        user = f"{project_name}_root"
        app_path = f"/srv/{project_name}/{project_name}_maintenance.py"

        if not os.path.exists(app_path):
            result = {
                "status": "not_deployed",
                "error": f"Maintenance app not found: {app_path}",
            }
            trace_out()
            return result

        try:
            pwd.getpwnam(user)
        except KeyError:
            result = {"status": "user_not_found", "error": f"User not found: {user}"}
            trace_out()
            return result

        # Stop existing processes
        check_cmd = ["ps", "aux"]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        lines = check_result.stdout.splitlines()
        pids_to_kill = []
        for line in lines:
            if f"{project_name}_maintenance.py" in line and "python" in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pids_to_kill.append(int(parts[1]))
                    except ValueError:
                        pass
        for pid in pids_to_kill:
            try:
                os.kill(pid, signal.SIGTERM)
                log(f"Stopped maintenance PID {pid}")
            except ProcessLookupError:
                log(f"Maintenance PID {pid} already stopped")
            except Exception as exc:
                warn(f"Failed to stop PID {pid}: {exc}")

        log_file = _maintenance_log_file(project_name)
        cmd = (
            f'sudo -u {user} bash -c "cd /srv/{project_name} && '
            f'nohup python3 {app_path} >> {log_file} 2>&1 &"'
        )
        debug(f"Starting maintenance daemon: {cmd}")
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

        verify = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=False)
        if f"{project_name}_maintenance.py" in verify.stdout:
            result = {"status": "started", "log_file": log_file, "user": user}
        else:
            result = {"status": "failed", "error": "Process not found running"}
        trace_out()
        return result
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to start maintenance daemon: {exc}")
        trace_out()
        return {"status": "error", "error": str(exc)}


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

    if not _ensure_root():
        trace_out()
        return False

    project_name, _ = detect_project_context()
    result = run_maintenance_start(project_name)
    gateway.response.set_action_response(success_payload(result))

    if result.get("status") in {"failed", "error", "not_deployed", "user_not_found"}:
        report_error("action", f"Maintenance start failed: {result.get('status')}")

    trace_out()
    return not is_error()


