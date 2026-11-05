#!/usr/bin/env python3
"""
Migration daemon worker.
Migrates data from legacy database to new database.
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

DEFAULT_DELAY = 10.0  # Longer delay for migration (10 seconds)
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
    
    - Deployed: /srv/{project}/logs/migration_{project}.log
    - Local dev: {project_root}/logs/migration_{project}.log
    
    Note: Does not create the log file or directory. The start script creates it.
    """
    project_name = get_project_name()
    
    # Check if deployed
    deployed_logs = Path(f"/srv/{project_name}/logs")
    if deployed_logs.exists():
        return deployed_logs / f"migration_{project_name}.log"
    
    # Local dev - use project root
    project_root = find_project_root()
    local_logs = project_root / "logs"
    return local_logs / f"migration_{project_name}.log"


def configure_logging() -> None:
    """Configure logging to write to stderr and log file (if it exists).
    
    The log file is created by the start script. If it doesn't exist,
    file logging is skipped silently (no error, no creation).
    """
    log_level = os.getenv("MIGRATION_LOG_LEVEL", "INFO").upper()
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
    
    # Add file handler only if log file exists (created by start script)
    if log_file.exists():
        try:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logging.info(f"Logging to file: {log_file}")
        except Exception:
            # Fail silently if we can't open the log file
            pass
    # If log file doesn't exist, skip file logging silently (no warning)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migration daemon - migrates data from legacy database",
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
    
    # In development environment, it's in the maintenance/deploy/apps/ directory
    return project_root / "hh" / "deploy" / "maint" / "maintenance_client.py"


def run_maintenance_command(command: str) -> Tuple[int, Optional[Dict[str, Any]], str, str]:
    """Run a maintenance command and return (exit_code, parsed_response, stderr, stdout)."""
    project_root = find_project_root()
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = str(project_root)

    # Split command string to handle arguments properly
    command_parts = command.split()
    cmd = [sys.executable, str(maintenance_client_path())] + command_parts
    
    # Windows: prevent console window from appearing
    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
        "cwd": str(project_root),
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
            # If JSON parsing fails, stdout might contain error info
            # Will be logged if exit_code != 0
            pass
    
    return exit_code, response, stderr, stdout


def run_cycle() -> bool:
    """Run one migration cycle. Returns True if work was done."""
    # Run migration daemon command with batch_size=25
    exit_code, response, stderr, stdout = run_maintenance_command("migration-daemon --batch_size 25")
    
    if exit_code != 0:
        # Log detailed error information
        error_msg = f"Migration daemon command failed with exit code {exit_code}"
        if stderr.strip():
            error_msg += f"\nStderr output:\n{stderr.strip()}"
        if stdout.strip() and not response:
            # If stdout exists but JSON parsing failed, include it
            error_msg += f"\nStdout output (non-JSON):\n{stdout.strip()[:1000]}"  # Limit to first 1000 chars
        if response:
            error_msg += f"\nResponse: {json.dumps(response, indent=2)}"
        logging.error(error_msg)
        return False
    
    if response and response.get("status") == "ok":
        data = response.get("data", {})
        result = data.get("result", {})
        migrated = result.get("migrated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)
        
        # Account migration results
        account_migrated = result.get("account_migrated", 0)
        account_skipped = result.get("account_skipped", 0)
        account_errors = result.get("account_errors", 0)
        
        # Account link setting results
        links_set = result.get("links_set", 0)
        link_errors = result.get("link_errors", 0)
        
        # Statement migration results
        statement_migrated = result.get("statement_migrated", 0)
        statement_skipped = result.get("statement_skipped", 0)
        statement_errors = result.get("statement_errors", 0)
        
        # Log page migration if there was work
        if migrated > 0 or errors > 0:
            logging.info(f"Migration cycle: {migrated} pages migrated, {skipped} pages skipped, {errors} page errors")
            return True
        
        # Log account migration if there was work
        if account_migrated > 0 or account_errors > 0:
            logging.info(f"Migration cycle: {account_migrated} accounts migrated, {account_skipped} accounts skipped, {account_errors} account errors")
            return True
        
        # Log account link setting if there was work
        if links_set > 0 or link_errors > 0:
            logging.info(f"Migration cycle: {links_set} account links set, {link_errors} link errors")
            return True
        
        # Log statement migration if there was work
        if statement_migrated > 0 or statement_errors > 0:
            logging.info(f"Migration cycle: {statement_migrated} statements migrated, {statement_skipped} statements skipped, {statement_errors} statement errors")
            return True
        
        # If we have skipped items, log appropriately
        if skipped > 0:
            logging.debug(f"Migration cycle: {skipped} pages skipped (waiting for parents)")
            return False
        elif account_skipped > 0:
            logging.debug(f"Migration cycle: {account_skipped} accounts skipped (waiting for parents)")
            return False
        elif statement_skipped > 0:
            logging.debug(f"Migration cycle: {statement_skipped} statements skipped (waiting for parents)")
            return False
        else:
            logging.debug("Migration cycle: No work to do")
            return False
    else:
        logging.warning(f"Migration daemon returned unexpected response: {response}")
        return False


def main() -> int:
    global RUNNING
    
    args = parse_args()
    
    # Configure logging first
    configure_logging()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    project_name = get_project_name()
    logging.info(f"Migration worker starting for {project_name} (delay: {args.delay}s)")
    logging.info("Press Ctrl+C to stop")
    
    cycle = 0
    last_heartbeat = datetime.now()
    
    while RUNNING:
        cycle += 1
        
        try:
            work_done = run_cycle()
        except Exception as e:
            logging.exception(f"Cycle error: {e}")
            work_done = False
        
        if RUNNING:
            # Force flush all log handlers and sync to disk
            for handler in logging.getLogger().handlers:
                handler.flush()
                if hasattr(handler, 'stream') and hasattr(handler.stream, 'fileno'):
                    try:
                        os.fsync(handler.stream.fileno())
                    except (OSError, AttributeError):
                        pass
            
            # Log heartbeat every 15 minutes
            now = datetime.now()
            minutes_since_heartbeat = (now - last_heartbeat).total_seconds() / 60
            if minutes_since_heartbeat >= 15:
                logging.info("Heartbeat: Migration daemon running")
                last_heartbeat = now
            
            # Sleep based on work status
            if work_done:
                time.sleep(2.0)  # Quick turnaround if work was done (2 seconds)
            else:
                time.sleep(args.delay)  # Normal delay when idle
    
    logging.info("Migration worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

