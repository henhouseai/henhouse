import os
import shutil
from pathlib import Path
from typing import Tuple
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

def detect_project_context() -> Tuple[str, Path]:
    trace_in()
    log("Detecting project context")
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            log(f"Found project: {project_name} at {current_path}")
            trace_out()
            return project_name, current_path
        current_path = current_path.parent
    project_name = Path.cwd().name
    log(f"Using current directory as project: {project_name}")
    trace_out()
    return project_name, Path.cwd()
