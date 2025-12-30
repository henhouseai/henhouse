"""Start maintenance daemon - cross-platform."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict

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
    """Start maintenance daemon."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        pm = gateway.os
        project_root = pm.find_project_root()
        is_deployed = pm.is_deployed(project_name)
        
        worker_path = _get_worker_path(project_name, is_deployed, project_root)
        log_file = _get_log_file(project_name, is_deployed, project_root)
        process_name = _get_process_filter(project_name, is_deployed)
        
        # Check if worker file exists
        if not gateway.files or not gateway.files.file_exists(str(worker_path)):
            result = {'status': 'not_found', 'error': f'Worker not found: {worker_path}'}
            trace_out()
            return result
        
        # Determine user for deployed mode
        user = f"{project_name}_root" if is_deployed else None
        
        # Check if user exists (for deployed mode)
        if is_deployed and user and not gateway.os.user_exists(user):
            result = {'status': 'user_not_found', 'error': f'User not found: {user}'}
            trace_out()
            return result
        
        # Stop any existing maintenance processes using ProcessManager
        pm = gateway.os
        existing_processes = pm.list_processes(process_name)
        pids_to_kill = [p['pid'] for p in existing_processes]
        killed_any = False
        for pid in pids_to_kill:
            if pm.kill_process(pid, force=False):
                log(f"Sent SIGTERM to PID {pid} (Maintenance)")
                killed_any = True
        
        # Determine working directory
        if is_deployed:
            cwd = f"/srv/{project_name}"
        else:
            cwd = str(project_root)
        
        # Start maintenance daemon using ProcessManager
        if is_deployed and user:
            # Deployed mode: run as root user
            cmd = ['python3', str(worker_path)]
        else:
            # Local dev mode: run as current user
            cmd = [sys.executable, str(worker_path)]
        debug(f"Starting maintenance daemon: {cmd} in {cwd} as {user}")
        
        # Use ProcessManager to start background process
        started_pid = pm.start_background_process(cmd, cwd=cwd, log_file=None, user=user)
        
        if started_pid:
            debug(f"Started process with PID: {started_pid}")
        else:
            start_result = {'status': 'failed', 'error': 'Failed to start process'}
            warn(f"Maintenance daemon failed to start")
            trace_out()
            return start_result
        
        # Give it a moment for the daemon to start
        time.sleep(1)
        
        # Check if the maintenance daemon is actually running using ProcessManager
        check_processes = pm.list_processes(process_name)
        debug(f"Process check for '{process_name}': found {len(check_processes)} processes")
        
        if check_processes:
            result_status = 'restarted' if killed_any else 'started'
            start_result = {
                'status': result_status,
                'log_file': str(log_file),
                'deployed': is_deployed,
            }
            if user:
                start_result['user'] = user
            log(f"Started maintenance daemon")
            trace_out()
            return start_result
        else:
            start_result = {'status': 'failed', 'error': 'Process not found running'}
            warn(f"Maintenance daemon failed to start")
            trace_out()
            return start_result
        
    except Exception as e:
        error_result = {'status': 'error', 'error': str(e)}
        warn(f"Error starting maintenance daemon: {e}")
        trace_out()
        return error_result


def start_ext_daemon(project_name: str, daemon_name: str) -> Dict[str, Any]:
    """Start an EXT maintenance daemon (e.g., migration).
    
    Args:
        project_name: Project name
        daemon_name: Daemon name (e.g., 'migration')
        
    Returns:
        Dictionary with start status
    """
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        pm = gateway.os
        project_root = pm.find_project_root()
        is_deployed = pm.is_deployed(project_name)
        
        # Get worker path
        if is_deployed:
            worker_path = Path(f"/srv/{project_name}/{project_name}_maintenance_{daemon_name}.py")
            process_name = f"{project_name}_maintenance_{daemon_name}.py"
        else:
            worker_path = project_root / "ext" / "deploy" / "maintenance" / f"{daemon_name}_worker.py"
            process_name = f"{daemon_name}_worker.py"
        
        # Use daemon-specific log file name
        if is_deployed:
            log_file = Path(f"/srv/{project_name}/logs/{daemon_name}_{project_name}.log")
        else:
            log_file = project_root / "logs" / f"{daemon_name}_{project_name}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if worker file exists
        if not gateway.files or not gateway.files.file_exists(str(worker_path)):
            result = {'status': 'not_found', 'error': f'Worker not found: {worker_path}'}
            trace_out()
            return result
        
        # Determine user for deployed mode
        user = f"{project_name}_root" if is_deployed else None
        
        # Check if user exists (for deployed mode)
        if is_deployed and user and not gateway.os.user_exists(user):
            result = {'status': 'user_not_found', 'error': f'User not found: {user}'}
            trace_out()
            return result
        
        # Stop any existing daemon processes using ProcessManager
        pm = gateway.os
        existing_processes = pm.list_processes(process_name)
        pids_to_kill = [p['pid'] for p in existing_processes]
        killed_any = False
        for pid in pids_to_kill:
            if pm.kill_process(pid, force=False):
                log(f"Sent SIGTERM to PID {pid} ({daemon_name})")
                killed_any = True
        
        # Determine working directory
        if is_deployed:
            cwd = f"/srv/{project_name}"
        else:
            cwd = str(project_root)
        
        # Start EXT daemon using ProcessManager
        if is_deployed and user:
            # Deployed mode: run as root user
            cmd = ['python3', str(worker_path)]
        else:
            # Local dev mode: run as current user
            cmd = [sys.executable, str(worker_path)]
        debug(f"Starting {daemon_name} daemon: {cmd} in {cwd} as {user}")
        
        # Use ProcessManager to start background process
        started_pid = pm.start_background_process(cmd, cwd=cwd, log_file=None, user=user)
        
        if started_pid:
            debug(f"Started process with PID: {started_pid}")
        else:
            start_result = {'status': 'failed', 'error': 'Failed to start process'}
            warn(f"{daemon_name} daemon failed to start")
            trace_out()
            return start_result
        
        # Give it a moment for the daemon to start
        time.sleep(1)
        
        # Check if the daemon is actually running using ProcessManager
        check_processes = pm.list_processes(process_name)
        debug(f"Process check for '{process_name}': found {len(check_processes)} processes")
        
        if check_processes:
            result_status = 'restarted' if killed_any else 'started'
            start_result = {
                'status': result_status,
                'log_file': str(log_file),
                'deployed': is_deployed,
            }
            if user:
                start_result['user'] = user
            log(f"Started {daemon_name} daemon")
            trace_out()
            return start_result
        else:
            start_result = {'status': 'failed', 'error': 'Process not found running'}
            warn(f"{daemon_name} daemon failed to start")
            trace_out()
            return start_result
        
    except Exception as e:
        error_result = {'status': 'error', 'error': str(e)}
        warn(f"Error starting {daemon_name} daemon: {e}")
        trace_out()
        return error_result


def run_maintenance_start(project_name: str) -> Dict[str, Any]:
    trace_in()
    # Start main maintenance daemon
    main_result = start_maintenance_process(project_name)
    
    # Start EXT daemons
    ext_results = {}
    gateway = get_gateway()
    if gateway and gateway.os:
        pm = gateway.os
        project_root = pm.find_project_root()
        is_deployed = pm.is_deployed(project_name)
        
        # Look for EXT maintenance workers
        if is_deployed:
            ext_maint_dir = Path(f"/srv/{project_name}")
            # Check for deployed EXT workers (pattern: {project_name}_maintenance_{daemon_name}.py)
            for worker_file in ext_maint_dir.glob(f"{project_name}_maintenance_*.py"):
                if worker_file.name == f"{project_name}_maintenance.py":
                    continue  # Skip main maintenance worker
                # Extract daemon name: henhouse_maintenance_migration.py -> migration
                daemon_name = worker_file.stem.replace(f"{project_name}_maintenance_", "")
                if daemon_name:
                    ext_results[daemon_name] = start_ext_daemon(project_name, daemon_name)
        else:
            ext_maint_dir = project_root / "ext" / "deploy" / "maintenance"
            if ext_maint_dir.exists():
                for worker_file in ext_maint_dir.glob("*_worker.py"):
                    daemon_name = worker_file.stem.replace("_worker", "")
                    ext_results[daemon_name] = start_ext_daemon(project_name, daemon_name)
    
    # Combine results
    result = {
        "main": main_result,
        "ext": ext_results
    }
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
    
    # Check if running with sudo privileges (also checks for Unix deployment)
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False
    
    # Detect project name
    project_name, _ = detect_project_context()
    log(f"Project: {project_name}")
    
    result = run_maintenance_start(project_name)
    gateway.response.set_action_response(success_payload(result))

    # Check for errors in main or ext daemons
    main_status = result.get("main", {}).get("status")
    if main_status in {"failed", "error", "not_found"}:
        report_error("action", f"Maintenance start failed: {result.get('main', {}).get('error', main_status)}")
    
    # Check ext daemons for errors
    ext_results = result.get("ext", {})
    for daemon_name, ext_result in ext_results.items():
        ext_status = ext_result.get("status")
        if ext_status in {"failed", "error", "not_found"}:
            report_error("action", f"EXT daemon {daemon_name} start failed: {ext_result.get('error', ext_status)}")

    trace_out()
    return not is_error()
