"""Monitor command - launch tmux monitoring session."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

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


@register_action("monitor")
@register_command("monitor")
def monitor() -> bool:
    """Launch tmux monitoring session for the current project."""
    trace_in()
    try:
        # Detect project context
        project_name, project_root = detect_project_context()
        log(f"Detected project: {project_name} at {project_root}")

        # Find monitor.sh script (in same directory as this module)
        monitor_script = Path(__file__).parent / "monitor.sh"
        if not monitor_script.exists():
            error_msg = f"Monitor script not found: {monitor_script}"
            warn(error_msg)
            report_error("action", error_msg)
            trace_out()
            return False

        # Verify script is executable
        if not os.access(monitor_script, os.X_OK):
            error_msg = f"Monitor script not executable: {monitor_script}"
            warn(error_msg)
            report_error("action", error_msg)
            trace_out()
            return False

        log(f"Launching monitor script: {monitor_script} with project: {project_name}")

        # Replace current process with monitor script, passing project name as argument
        # This will completely replace the Python process with bash running monitor.sh
        os.execvp('/bin/bash', ['bash', str(monitor_script), project_name])

        # This line will never be reached - os.execvp() replaces the process
        trace_out()
        return True

    except Exception as e:
        error_msg = f"Failed to launch monitor: {e}"
        warn(error_msg)
        report_error("action", error_msg)
        trace_out()
        return False