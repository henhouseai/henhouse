"""Check maintenance daemon status - cross-platform."""

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
    """Get status of main maintenance daemon."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os or not gateway.files:
            error_result = {'daemon': 'main', 'status': 'error', 'error': 'Gateway or ProcessManager or FileSystem not available'}
            trace_out()
            return error_result
        
        pm = gateway.os
        project_root = pm.find_project_root()
        is_deployed = pm.is_deployed(project_name)
        
        worker_path = _get_worker_path(project_name, is_deployed, project_root)
        process_name = _get_process_filter(project_name, is_deployed)
        
        # Check if worker file exists
        if not gateway.files.file_exists(str(worker_path)):
            not_found_result = {
                'daemon': 'main',
                'status': 'not_found',
                'error': f'Worker not found: {worker_path}',
                'deployed': is_deployed,
            }
            trace_out()
            return not_found_result
        
        # Check if process is running
        cmd = ['ps', 'aux']
        ps_result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the maintenance process
        lines = ps_result.stdout.split('\n')
        pids = []
        
        for line in lines:
            if process_name in line and 'python' in line:
                parts = line.split()
                # ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # PID is column 1
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids.append(pid)
                    except ValueError:
                        pass
        
        if pids:
            # Get full username using stat command (ps aux truncates long usernames)
            users = []
            for pid in pids:
                try:
                    stat_result = subprocess.run(['stat', '-c', '%U', f'/proc/{pid}/'], capture_output=True, text=True, check=False)
                    if stat_result.returncode == 0:
                        user = stat_result.stdout.strip()
                        if user:
                            users.append(user)
                except Exception:
                    pass
            
            # Get unique users (should be same for all PIDs of same daemon)
            unique_users = list(set(users)) if users else ['unknown']
            user = unique_users[0] if unique_users else 'unknown'
            running_result = {
                'daemon': 'main',
                'status': 'running',
                'pids': pids,
                'user': user,
                'port': None,  # Maintenance daemons don't use ports
                'deployed': is_deployed,
                'worker_path': str(worker_path),
            }
            log(f"Maintenance daemon is running (PIDs: {pids}, User: {user})")
            trace_out()
            return running_result
        else:
            stopped_result = {
                'daemon': 'main',
                'status': 'stopped',
                'user': None,
                'port': None,
                'deployed': is_deployed,
                'worker_path': str(worker_path),
            }
            log(f"Maintenance daemon is stopped")
            trace_out()
            return stopped_result
        
    except Exception as e:
        error_result = {'daemon': 'main', 'status': 'error', 'error': str(e)}
        warn(f"Error checking maintenance daemon status: {e}")
        trace_out()
        return error_result


def status_ext_daemon(project_name: str, daemon_name: str) -> Dict[str, Any]:
    """Check status of an EXT maintenance daemon.
    
    Args:
        project_name: Project name
        daemon_name: Daemon name (e.g., 'migration')
        
    Returns:
        Dictionary with status
    """
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os or not gateway.files:
            error_result = {'daemon': daemon_name, 'status': 'error', 'error': 'Gateway or ProcessManager or FileSystem not available'}
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
        
        # Check if worker file exists
        if not gateway.files.file_exists(str(worker_path)):
            not_found_result = {
                'daemon': daemon_name,
                'status': 'not_found',
                'error': f'Worker not found: {worker_path}',
                'deployed': is_deployed,
            }
            trace_out()
            return not_found_result
        
        # Check if process is running
        cmd = ['ps', 'aux']
        ps_result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the EXT daemon process
        lines = ps_result.stdout.split('\n')
        pids = []
        
        for line in lines:
            if process_name in line and 'python' in line:
                parts = line.split()
                # ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # PID is column 1
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids.append(pid)
                    except ValueError:
                        pass
        
        if pids:
            # Get full username using stat command (ps aux truncates long usernames)
            users = []
            for pid in pids:
                try:
                    stat_result = subprocess.run(['stat', '-c', '%U', f'/proc/{pid}/'], capture_output=True, text=True, check=False)
                    if stat_result.returncode == 0:
                        user = stat_result.stdout.strip()
                        if user:
                            users.append(user)
                except Exception:
                    pass
            
            # Get unique users (should be same for all PIDs of same daemon)
            unique_users = list(set(users)) if users else ['unknown']
            user = unique_users[0] if unique_users else 'unknown'
            running_result = {
                'daemon': daemon_name,
                'status': 'running',
                'pids': pids,
                'user': user,
                'port': None,  # EXT maintenance daemons don't use ports
                'deployed': is_deployed,
                'worker_path': str(worker_path),
            }
            log(f"{daemon_name} daemon is running (PIDs: {pids}, User: {user})")
            trace_out()
            return running_result
        else:
            stopped_result = {
                'daemon': daemon_name,
                'status': 'stopped',
                'user': None,
                'port': None,
                'deployed': is_deployed,
                'worker_path': str(worker_path),
            }
            log(f"{daemon_name} daemon is stopped")
            trace_out()
            return stopped_result
        
    except Exception as e:
        error_result = {'daemon': daemon_name, 'status': 'error', 'error': str(e)}
        warn(f"Error checking {daemon_name} daemon status: {e}")
        trace_out()
        return error_result


def run_maintenance_status(project_name: str) -> Dict[str, Any]:
    trace_in()
    # Check main maintenance daemon status
    main_result = status_maintenance_process(project_name)
    
    # Check EXT daemon statuses
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
                    ext_results[daemon_name] = status_ext_daemon(project_name, daemon_name)
        else:
            ext_maint_dir = project_root / "ext" / "deploy" / "maintenance"
            if ext_maint_dir.exists():
                for worker_file in ext_maint_dir.glob("*_worker.py"):
                    daemon_name = worker_file.stem.replace("_worker", "")
                    ext_results[daemon_name] = status_ext_daemon(project_name, daemon_name)
    
    # Build list of all daemon results
    all_results = [main_result]
    all_results.extend(ext_results.values())
    
    # Calculate summary counts
    running_count = sum(1 for r in all_results if r.get('status') == 'running')
    stopped_count = sum(1 for r in all_results if r.get('status') == 'stopped')
    not_found_count = sum(1 for r in all_results if r.get('status') == 'not_found')
    error_count = sum(1 for r in all_results if r.get('status') == 'error')
    
    # Combine results
    result = {
        "project_name": project_name,
        "main": main_result,
        "ext": ext_results,
        "summary": {
            "total": 1 + len(ext_results),  # 1 main + ext daemons
            "running": running_count,
            "stopped": stopped_count,
            "not_found": not_found_count,
            "errors": error_count,
        }
    }
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
    
    # Detect project name
    project_name, _ = detect_project_context()
    log(f"Project: {project_name}")
    
    result_data = run_maintenance_status(project_name)
    gateway.response.set_action_response(success_payload(result_data))
    
    log(
        f"Maintenance daemon status: "
        f"{result_data['summary']['running']} running, "
        f"{result_data['summary']['stopped']} stopped"
    )
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True
