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
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import success_payload, get_data
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section, safe_str

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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
        
        # Check if process is running using ProcessManager
        pm = gateway.os
        processes = pm.list_processes(process_name)
        pids = [p['pid'] for p in processes]
        
        if pids:
            # Get full username using ProcessManager helper (ps aux truncates long usernames)
            users = []
            for pid in pids:
                username = pm.get_process_username(pid)
                if username:
                    users.append(username)
            
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
        
        # Check if process is running using ProcessManager
        pm = gateway.os
        processes = pm.list_processes(process_name)
        pids = [p['pid'] for p in processes]
        
        if pids:
            # Get full username using ProcessManager helper (ps aux truncates long usernames)
            users = []
            for pid in pids:
                username = pm.get_process_username(pid)
                if username:
                    users.append(username)
            
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


def _render_maintenance_block(source_data, lines):
    """Helper function to render maintenance daemon status table."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in _render_maintenance_block")
        trace_out()
        return

    block = "maintenance"
    if gateway.is_no(block):
        trace_out()
        return

    data_table = TableData()
    # Add header row to define column structure (no port column for maintenance daemons)
    data_table.add_row("maintenance_header", name="Daemon", user="User")

    # Get main maintenance daemon status
    main_data = source_data.get("main", {})
    main_status = main_data.get("status", "unknown")
    main_user = main_data.get("user", "")

    main_user_str = safe_str(main_user) if main_user else '-'

    if main_status == "running":
        data_table.add_row("daemon_running", name="main", user=main_user_str)
    elif main_status == "stopped":
        data_table.add_row("daemon_stopped", name="main", user=main_user_str)
    elif main_status == "not_found":
        data_table.add_row("daemon_not_found", name="main", user=main_user_str)
    elif main_status == "error":
        data_table.add_row("daemon_failed", name="main", user=main_user_str)
    else:
        data_table.add_row("daemon_not_found", name="main", user=main_user_str)

    # Get EXT maintenance daemon statuses
    ext_data = source_data.get("ext", {})
    for daemon_name, ext_daemon_data in ext_data.items():
        ext_status = ext_daemon_data.get("status", "unknown")
        ext_user = ext_daemon_data.get("user", "")

        ext_user_str = safe_str(ext_user) if ext_user else '-'

        if ext_status == "running":
            data_table.add_row("daemon_running", name=safe_str(daemon_name), user=ext_user_str)
        elif ext_status == "stopped":
            data_table.add_row("daemon_stopped", name=safe_str(daemon_name), user=ext_user_str)
        elif ext_status == "not_found":
            data_table.add_row("daemon_not_found", name=safe_str(daemon_name), user=ext_user_str)
        elif ext_status == "error":
            data_table.add_row("daemon_failed", name=safe_str(daemon_name), user=ext_user_str)
        else:
            data_table.add_row("daemon_not_found", name=safe_str(daemon_name), user=ext_user_str)

    lines.append(
        render_block(
            data_table,
            FieldConfig()
            .add_header("maintenance_header")
            .add_simple(
                [
                    "daemon_running",
                    "daemon_stopped",
                    "daemon_not_deployed",
                    "daemon_failed",
                    "daemon_not_found",
                ]
            ),
            table_overrides={"margin_l": 4},
            block_type=block,
        )
    )
    break_section(lines)
    trace_out()


@register_parser("maintenance_status")
def render_maintenance_status() -> bool:
    """Parser for maintenance_status command."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data if json_data is not None else {})
    lines = [render_header_block("l_maintenance_status_header")]
    _render_maintenance_block(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Maintenance status parser output length: {len(result)}")
    trace_out()
    return True
