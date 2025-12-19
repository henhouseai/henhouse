#!/usr/bin/env python3
"""
Maintenance daemon worker.
Monitors job queue and stale caches, dispatches maintenance tasks.
"""

from __future__ import annotations
from typing import Any

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DELAY = 5.0
RUNNING = True


def find_project_root() -> Path:
    """Walk up from this file until we find the project root (contains hh/)."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / "hh").is_dir():
            return current
        current = current.parent
    raise RuntimeError("Could not locate project root (hh/ directory)")


def get_project_name() -> str:
    """Get project name from project root directory name."""
    return find_project_root().name


def get_log_file_path() -> Path:
    """Determine log file path based on deployment status.
    
    - Deployed: /srv/{project}/logs/maintenance_{project}.log
    - Local dev: {project_root}/logs/maintenance_{project}.log
    """
    project_name = get_project_name()
    
    # Check if deployed
    deployed_logs = Path(f"/srv/{project_name}/logs")
    if deployed_logs.exists():
        return deployed_logs / f"maintenance_{project_name}.log"
    
    # Local dev - use project root
    project_root = find_project_root()
    local_logs = project_root / "logs"
    local_logs.mkdir(parents=True, exist_ok=True)
    return local_logs / f"maintenance_{project_name}.log"


def configure_logging() -> None:
    """Configure logging to write to both stderr and log file."""
    log_level = os.getenv("MAINTENANCE_LOG_LEVEL", "DEBUG").upper()  # Temporarily DEBUG for troubleshooting
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    
    # Get log file path
    log_file = get_log_file_path()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add stderr handler (for terminal output)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    
    # Add file handler
    try:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logging.info(f"Logging to file: {log_file}")
    except Exception as e:
        logging.warning(f"Could not open log file {log_file}: {e}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Maintenance daemon - monitors and processes maintenance tasks",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Seconds to wait between cycles (default: {DEFAULT_DELAY})",
    )
    return parser.parse_args()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global RUNNING
    logging.info("Shutdown signal received, finishing current cycle...")
    RUNNING = False


def maintenance_client_path() -> Path:
    """Get path to maintenance_client.py."""
    project_root = find_project_root()
    
    # In deployed environment, maintenance_client.py is at the top level
    deployed_client = project_root / "maintenance_client.py"
    if deployed_client.exists():
        return deployed_client
    
    # In development environment, it's in the hh/deploy/maint/ directory
    return project_root / "hh" / "deploy" / "maint" / "maintenance_client.py"


def run_maintenance_command(command: str, with_log: bool = False, verbose_debug: bool = False) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Run a maintenance command and return (exit_code, parsed_response)."""
    project_root = find_project_root()
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = str(project_root)

    cmd = [sys.executable, str(maintenance_client_path()), command]
    if with_log:
        cmd.append("-log")
    
    # Debug logging to see exact command (only when verbose)
    if verbose_debug:
        logging.debug(f"Running command: {' '.join(cmd)}")
        logging.debug(f"Environment PYTHONPATH: {env.get('PYTHONPATH')}")
    
    # Windows: prevent console window from appearing
    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    
    process = subprocess.Popen(cmd, **kwargs)  # type: ignore[call-overload]
    stdout, stderr = process.communicate()
    exit_code = process.returncode
    
    # Parse JSON response
    response = None
    if stdout.strip():
        try:
            response = json.loads(stdout.strip())
        except json.JSONDecodeError:
            pass
    
    return exit_code, response


def extract_error_debug(response: Dict[str, Any]) -> str:
    """Extract errors and debug info from response for storage."""
    extracted = {}
    if response.get("errors"):
        extracted["errors"] = response["errors"]
    if response.get("debug"):
        extracted["debug"] = response["debug"]
    return json.dumps(extracted, ensure_ascii=False, separators=(",", ":")) if extracted else ""


def run_maintenance_command_with_args(args: List[str]) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Run maintenance client with explicit argument list."""
    project_root = find_project_root()
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = str(project_root)

    cmd = [sys.executable, str(maintenance_client_path())] + args
    
    # Windows: prevent console window from appearing
    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    
    process = subprocess.Popen(cmd, **kwargs)  # type: ignore[call-overload]
    stdout, stderr = process.communicate()
    exit_code = process.returncode
    
    # Parse JSON response
    response = None
    if stdout.strip():
        try:
            response = json.loads(stdout.strip())
        except json.JSONDecodeError:
            pass
    
    return exit_code, response


def update_job_status(
    job_id: int,
    status: str,
    progress: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> bool:
    """Update a maintenance job via the update-maintenance-job command."""
    args = ["update-maintenance-job", "-job_id", str(job_id), "-status", status]
    if progress:
        progress_json = json.dumps(progress, ensure_ascii=False, separators=(",", ":"))
        args.extend(["-progress", progress_json])
    if error_message:
        args.extend(["-error_message", error_message])
    
    exit_code, response = run_maintenance_command_with_args(args)
    return exit_code == 0


def get_jobs_status(verbose_debug: bool = False) -> Optional[Dict[str, Any]]:
    """Get current maintenance jobs status."""
    if verbose_debug:
        # Debug logging to see what paths we're using (only during heartbeat or when there's work)
        project_root = find_project_root()
        client_path = maintenance_client_path()
        logging.debug(f"Project root: {project_root}")
        logging.debug(f"Client path: {client_path}")
        logging.debug(f"Client exists: {client_path.exists()}")
    
    exit_code, response = run_maintenance_command("maintenance-jobs-status", verbose_debug=verbose_debug)
    
    if response and response.get("status") == "ok":
        data = response.get("data", {})
        # Log useful status info only when there's work OR during heartbeat
        if data.get("has_work", False) or verbose_debug:
            logging.info(f"maintenance-jobs-status response: {response}")
            logging.info(f"Status data: {data}")
        return data
    else:
        logging.error(f"Failed to get jobs status - exit_code: {exit_code}, response: {response}")
        return None


def build_work_docket(status: Dict[str, Any]) -> List[Tuple[str, bool]]:
    """Build ordered list of (command, is_job_queue) tuples based on status.
    
    Priority:
    1. Pending jobs from maintenance_jobs (by priority)
    2. Stale cache refreshes
    
    is_job_queue=True means the command needs job status updates via update-maintenance-job.
    """
    docket = []
    
    # Pending jobs first (sorted by priority would require more info)
    # For now, just add each job type once
    pending_jobs = status.get("pending_jobs", {})
    for job_type in pending_jobs.keys():
        # Convert job_type to command (underscore to hyphen)
        command = job_type.replace("_", "-")
        docket.append((command, True))  # is_job_queue=True
    
    # Then stale cache refreshes (not job queue items)
    if status.get("stale_pages", 0) > 0:
        docket.append(("page-cache-refresh", False))
    if status.get("stale_images", 0) > 0:
        docket.append(("image-cache-refresh", False))
    if status.get("stale_files", 0) > 0:
        docket.append(("file-cache-refresh", False))
    
    return docket


def handle_job_response(command: str, exit_code: int, response: Optional[Dict[str, Any]]) -> None:
    """Handle response from a job queue command, updating job status as needed."""
    if not response:
        logging.warning("No response to process")
        return
    
    # For maintenance backend, response is already flat (no "data" wrapper)
    data = response if isinstance(response, dict) else {}
    job_id = data.get("job_id")
    
    if not job_id:
        logging.debug("No job_id in response (no job claimed)")
        return
    
    has_error = exit_code != 0 or response.get("status") != "ok"
    
    if has_error:
        # Error occurred - retry with -log to get debug info
        logging.warning(f"Error detected, retrying with -log for job {job_id}")
        retry_exit, retry_response = run_maintenance_command(command, with_log=True, verbose_debug=False)
        
        # Extract errors and debug from retry response
        error_data = extract_error_debug(retry_response) if retry_response else ""
        
        # Build progress with context
        progress = {
            "last_page_id": data.get("resolution_id"),
            "error_context": {
                "command": command,
                "exit_code": retry_exit,
            }
        }
        
        # Update job status to error
        logging.error(f"Updating job {job_id} to error status")
        update_job_status(job_id, "error", progress=progress, error_message=error_data)
    else:
        # Success - check if done or still in progress
        done = data.get("done", False)
        
        if done:
            # Job complete
            progress = {
                "last_page_id": data.get("resolution_id"),
            }
            logging.info(f"Job {job_id} complete, updating to done")
            update_job_status(job_id, "done", progress=progress)
        else:
            # Still in progress - update progress and set back to pending
            result = data.get("result", {})
            progress = {
                "last_page_id": data.get("resolution_id"),
                "pages_processed": result.get("processed", 0),
                "pages_modified": 1 if result.get("modified") else 0,
            }
            logging.debug(f"Job {job_id} in progress, updating to pending")
            update_job_status(job_id, "pending", progress=progress)


def run_cycle(last_heartbeat: datetime) -> tuple[bool, datetime]:
    """Run one maintenance cycle. Returns (work_done, new_last_heartbeat)."""
    # Check if we should log a heartbeat (every 15 minutes)
    now = datetime.now()
    minutes_since_heartbeat = (now - last_heartbeat).total_seconds() / 60
    is_heartbeat_time = minutes_since_heartbeat >= 15
    
    # Get current status (with verbose debug only during heartbeat time or when there might be work)
    status = get_jobs_status(verbose_debug=is_heartbeat_time)
    if status is None:
        logging.error("Failed to get maintenance status")
        return False, last_heartbeat
    
    # Check if there's work
    if not status.get("has_work", False):
        if is_heartbeat_time:
            # Log heartbeat with current status
            pending_jobs = status.get("pending_jobs", {})
            stale_counts = []
            if status.get("stale_pages", 0) > 0:
                stale_counts.append(f"{status['stale_pages']} pages")
            if status.get("stale_images", 0) > 0:
                stale_counts.append(f"{status['stale_images']} images") 
            if status.get("stale_files", 0) > 0:
                stale_counts.append(f"{status['stale_files']} files")
            
            # Status check info is redundant with status data - removed
            
            if pending_jobs or stale_counts:
                # There's work but has_work is False - this shouldn't happen, but log it
                work_summary = []
                if pending_jobs:
                    job_summary = ", ".join(f"{job_type}({count})" for job_type, count in pending_jobs.items())
                    work_summary.append(f"Jobs: {job_summary}")
                if stale_counts:
                    work_summary.append(f"Stale: {', '.join(stale_counts)}")
                logging.info(f"Heartbeat: Work detected but not flagged - {' | '.join(work_summary)}")
            else:
                logging.info("Heartbeat: No work found")
            
            return False, now
        
        # No logging when idle and not time for heartbeat - keeps log clean
        return False, last_heartbeat
    
    # We already have the status from the first call - no need to call again
    
    # Build work docket
    docket = build_work_docket(status)
    if not docket:
        # No logging when no tasks - keeps log clean
        return False, last_heartbeat
    
    # Status check info is redundant with status data - removed
    
    # Log summary of available work
    pending_jobs = status.get("pending_jobs", {})
    stale_counts = []
    if status.get("stale_pages", 0) > 0:
        stale_counts.append(f"{status['stale_pages']} pages")
    if status.get("stale_images", 0) > 0:
        stale_counts.append(f"{status['stale_images']} images") 
    if status.get("stale_files", 0) > 0:
        stale_counts.append(f"{status['stale_files']} files")
    
    work_summary = []
    if pending_jobs:
        job_summary = ", ".join(f"{job_type}({count})" for job_type, count in pending_jobs.items())
        work_summary.append(f"Jobs: {job_summary}")
    if stale_counts:
        work_summary.append(f"Stale: {', '.join(stale_counts)}")
    
    logging.info(f"Work available: {' | '.join(work_summary)}")
    # Work docket only shows during heartbeat cycles
    if is_heartbeat_time:
        logging.debug(f"Work docket: {', '.join(cmd for cmd, _ in docket)}")
    
    # Execute each task
    for command, is_job_queue in docket:
        if not RUNNING:
            logging.info("Shutdown requested, stopping cycle")
            break
        
        exit_code, response = run_maintenance_command(command, verbose_debug=False)
        
        if is_job_queue:
            # Job queue item - handle status updates
            handle_job_response(command, exit_code, response)
        else:
            # Simple cache refresh - just report result
            if exit_code == 0:
                logging.info(f"{command}: OK")
            else:
                error_msg = "unknown error"
                if response and response.get("errors"):
                    errors = response["errors"]
                    if errors:
                        error_msg = errors[0].get("content", error_msg)
                logging.error(f"{command}: FAILED - {error_msg}")
    
    return True, last_heartbeat


def main() -> int:
    global RUNNING
    
    args = parse_args()
    
    # Configure logging first
    configure_logging()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    project_name = get_project_name()
    logging.info(f"Maintenance worker starting for {project_name} (delay: {args.delay}s)")
    logging.info("Press Ctrl+C to stop")
    
    cycle = 0
    last_heartbeat = datetime.now()  # Initialize heartbeat timer
    
    while RUNNING:
        cycle += 1
        # Only log cycle number when work is actually done
        cycle_logged = False
        
        try:
            work_done, last_heartbeat = run_cycle(last_heartbeat)
        except Exception as e:
            logging.exception(f"Cycle error: {e}")
            work_done = False
        
        if RUNNING:
            # Force flush all log handlers and sync to disk
            for handler in logging.getLogger().handlers:
                handler.flush()
                # Force OS-level sync if it's a file handler
                if hasattr(handler, 'stream') and hasattr(handler.stream, 'fileno'):
                    try:
                        os.fsync(handler.stream.fileno())
                    except (OSError, AttributeError):
                        pass
            
            # Sleep based on work status: 0.5 second if work was done, full delay if idle
            if work_done:
                time.sleep(0.5)  # Quick turnaround for continuous work processing
            else:
                time.sleep(args.delay)  # Normal delay when idle
    
    logging.info("Maintenance worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
