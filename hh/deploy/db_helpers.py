"""
Database helper functions for module hooks.

Provides utilities for executing SQL files from module hooks.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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


def execute_sql_file(
    sql_file_path: Path,
    target_db: str,
    credentials_file: str,
    label: str
) -> bool:
    """
    Execute a SQL file against a target database using a credentials file.

    Args:
        sql_file_path: Path to SQL file to execute
        target_db: Database name to use
        credentials_file: Path to MySQL option file with credentials
        label: Description for logging (e.g., "hh_page init.sql")

    Returns:
        True if execution succeeded, False otherwise
    """
    trace_in()

    if not sql_file_path.exists():
        debug(f"SQL file does not exist: {sql_file_path} (skipping)")
        return trace_out(True)  # Not an error - module may not have this file

    if is_error():
        return trace_out(False)

    log(f"Executing {label}: {sql_file_path}")

    try:
        mysql_cmd = ["mysql", f"--defaults-file={credentials_file}", target_db]
        with open(sql_file_path, 'r') as sql_file:
            result = subprocess.run(
                mysql_cmd,
                stdin=sql_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        if result.returncode != 0:
            warn(f"{label} execution failed with return code {result.returncode}")
            warn(f"{label} stderr: {result.stderr}")
            report_error("action", f"{label} failed: {result.stderr}")
            return trace_out(False)
        log(f"{label} completed successfully")
        return trace_out(True)
    except Exception as e:
        warn(f"{label} execution failed: {str(e)}")
        report_error("action", f"{label} execution failed: {str(e)}")
        return trace_out(False)


def create_database_if_not_exists(
    db_name: str,
    credentials_file: str,
    label: str
) -> bool:
    """
    Create a database if it doesn't exist using a credentials file.

    Args:
        db_name: Database name to create
        credentials_file: Path to MySQL option file with credentials
        label: Description for logging

    Returns:
        True if successful, False otherwise
    """
    trace_in()

    if is_error():
        return trace_out(False)

    log(f"Creating database if not exists: {db_name}")

    stmt = f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    try:
        result = subprocess.run(
            ["mysql", f"--defaults-file={credentials_file}", "-e", stmt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            warn(f"Failed to create {label}: {result.stderr}")
            report_error("action", f"{label} creation failed: {result.stderr}")
            return trace_out(False)
        log(f"{label} created successfully")
        return trace_out(True)
    except Exception as e:
        warn(f"Failed to create {label}: {str(e)}")
        report_error("action", f"{label} creation failed: {str(e)}")
        return trace_out(False)


def create_mysql_credentials_file(
    root_password: str,
    mysql_tls_enabled: bool = False,
    ssl_ca_path: str = "",
    ssl_verify_mode: int = 2
) -> Optional[str]:
    """
    Create a temporary MySQL credentials file.

    Args:
        root_password: MySQL root password
        mysql_tls_enabled: Whether TLS is enabled
        ssl_ca_path: Path to SSL CA certificate
        ssl_verify_mode: SSL verification mode (0=none, 1=optional, 2=required, 3=verify_identity)

    Returns:
        Path to credentials file, or None on error
    """
    trace_in()

    try:
        opt_file = tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='mysql_', suffix='.cnf')
        opt_file.write(f"[client]\n")
        opt_file.write(f"user=root\n")
        opt_file.write(f"password={root_password}\n")

        if mysql_tls_enabled and ssl_ca_path:
            opt_file.write(f"ssl-ca={ssl_ca_path}\n")
            # Map verify_mode to MySQL ssl-mode
            if ssl_verify_mode == 0:
                opt_file.write(f"ssl-mode=REQUIRED\n")
            elif ssl_verify_mode == 1:
                opt_file.write(f"ssl-mode=REQUIRED\n")
            elif ssl_verify_mode == 2:
                opt_file.write(f"ssl-mode=VERIFY_CA\n")
            elif ssl_verify_mode == 3:
                opt_file.write(f"ssl-mode=VERIFY_IDENTITY\n")
            else:
                opt_file.write(f"ssl-mode=REQUIRED\n")

        opt_file.close()
        os.chmod(opt_file.name, 0o600)

        log(f"Created MySQL credentials file: {opt_file.name}")
        return trace_out(opt_file.name)

    except Exception as e:
        warn(f"Failed to create credentials file: {str(e)}")
        report_error("action", f"Failed to create credentials file: {str(e)}")
        return trace_out(None)
