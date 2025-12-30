"""Stop maintenance daemon - cross-platform."""

from __future__ import annotations

import subprocess
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
    """Stop maintenance daemon."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        pm = gateway.os
        is_deployed = pm.is_deployed(project_name)
        process_name = _get_process_filter(project_name, is_deployed)
        
        # Find process running maintenance daemon
        cmd = ['ps', 'aux']
        ps_result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the maintenance process
        lines = ps_result.stdout.split('\n')
        pids_to_kill = []
        
        for line in lines:
            if process_name in line and 'python' in line:
                parts = line.split()
                # PID is typically the 2nd column
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids_to_kill.append(pid)
                    except ValueError:
                        pass
        
        if not pids_to_kill:
            not_running_result = {'status': 'not_running'}
            log(f"No maintenance daemon found")
            trace_out()
            return not_running_result
        
        # Kill the processes
        killed_pids = []
        for pid in pids_to_kill:
            if gateway.os.kill_process(pid, force=False):
                killed_pids.append(pid)
                log(f"Sent SIGTERM to PID {pid} (Maintenance)")
        
        if killed_pids:
            trace_out()
            return {'status': 'stopped', 'pids': killed_pids}
        else:
            trace_out()
            return {'status': 'not_found'}
        
    except Exception as e:
        error_result = {'status': 'error', 'error': str(e)}
        warn(f"Error stopping maintenance daemon: {e}")
        trace_out()
        return error_result


def stop_ext_daemon(project_name: str, daemon_name: str) -> Dict[str, Any]:
    """Stop an EXT maintenance daemon.
    
    Args:
        project_name: Project name
        daemon_name: Daemon name (e.g., 'migration')
        
    Returns:
        Dictionary with stop status
    """
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        pm = gateway.os
        is_deployed = pm.is_deployed(project_name)
        
        # Get process name
        if is_deployed:
            process_name = f"{project_name}_{daemon_name}.py"
        else:
            process_name = f"{daemon_name}_worker.py"
        
        # Find process running EXT daemon
        cmd = ['ps', 'aux']
        ps_result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the EXT daemon process
        lines = ps_result.stdout.split('\n')
        pids_to_kill = []
        
        for line in lines:
            if process_name in line and 'python' in line:
                parts = line.split()
                # PID is typically the 2nd column
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids_to_kill.append(pid)
                    except ValueError:
                        pass
        
        if not pids_to_kill:
            not_running_result = {'status': 'not_running'}
            log(f"No {daemon_name} daemon found")
            trace_out()
            return not_running_result
        
        # Kill the processes
        killed_pids = []
        for pid in pids_to_kill:
            if gateway.os.kill_process(pid, force=False):
                killed_pids.append(pid)
                log(f"Sent SIGTERM to PID {pid} ({daemon_name})")
        
        if killed_pids:
            trace_out()
            return {'status': 'stopped', 'pids': killed_pids}
        else:
            trace_out()
            return {'status': 'not_found'}
        
    except Exception as e:
        error_result = {'status': 'error', 'error': str(e)}
        warn(f"Error stopping {daemon_name} daemon: {e}")
        trace_out()
        return error_result


def run_maintenance_stop(project_name: str) -> Dict[str, Any]:
    trace_in()
    # Stop main maintenance daemon
    main_result = stop_maintenance_processes(project_name)
    
    # Stop EXT daemons
    ext_results = {}
    gateway = get_gateway()
    if gateway and gateway.os:
        pm = gateway.os
        project_root = pm.find_project_root()
        is_deployed = pm.is_deployed(project_name)
        
        # Look for EXT maintenance workers
        if is_deployed:
            ext_maint_dir = Path(f"/srv/{project_name}")
            # Check for deployed EXT workers
            for worker_file in ext_maint_dir.glob(f"{project_name}_*.py"):
                if worker_file.name == f"{project_name}_maintenance.py":
                    continue  # Skip main maintenance worker
                daemon_name = worker_file.stem.replace(f"{project_name}_", "")
                if daemon_name:
                    ext_results[daemon_name] = stop_ext_daemon(project_name, daemon_name)
        else:
            ext_maint_dir = project_root / "ext" / "deploy" / "maintenance"
            if ext_maint_dir.exists():
                for worker_file in ext_maint_dir.glob("*_worker.py"):
                    daemon_name = worker_file.stem.replace("_worker", "")
                    ext_results[daemon_name] = stop_ext_daemon(project_name, daemon_name)
    
    # Calculate summary counts
    main_status = main_result.get('status')
    stopped_count = 1 if main_status == 'stopped' else 0
    not_running_count = 1 if main_status == 'not_running' else 0
    failed_count = 1 if main_status == 'error' else 0
    
    # Count EXT daemon results
    for ext_result in ext_results.values():
        ext_status = ext_result.get('status')
        if ext_status == 'stopped':
            stopped_count += 1
        elif ext_status == 'not_running':
            not_running_count += 1
        elif ext_status == 'error':
            failed_count += 1
    
    total_daemons = 1 + len(ext_results)  # 1 main + ext daemons
    
    # Combine results
    result = {
        "project_name": project_name,
        "main": main_result,
        "ext": ext_results,
        "summary": {
            "total": total_daemons,
            "stopped": stopped_count,
            "not_running": not_running_count,
            "failed": failed_count,
        },
    }
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
    
    # Check if running in deployed Unix environment
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False
    
    # Detect project name
    project_name, _ = detect_project_context()
    log(f"Project: {project_name}")
    
    result_data = run_maintenance_stop(project_name)
    gateway.response.set_action_response(success_payload(result_data))
    
    if result_data['summary']['failed'] > 0:
        warn(f"Maintenance daemon stop completed with {result_data['summary']['failed']} failures")
        report_error("action", f"Maintenance daemon stop: {result_data['summary']['failed']} failed")
    
    log(
        f"Maintenance daemon stop completed: "
        f"{result_data['summary']['stopped']} stopped, "
        f"{result_data['summary']['not_running']} not running"
    )
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True
