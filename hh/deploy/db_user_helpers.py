import configparser
"""
Database user management helper functions.

Shared utilities for creating/removing database users and managing permissions.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from hh.gateway.error.error_store import report_error
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


def read_owner_password(project_name: str, owner: str) -> Optional[str]:
    """
    Read the project owner's DB password from /home/<owner>/.<project>.cnf.

    Install writes this file (user=<owner>, password=password_human_db) for the owner and root CLI.
    """
    config_file = Path(f"/home/{owner}/.{project_name}.cnf")
    if not config_file.exists():
        warn(f"Owner config file not found: {config_file}")
        return None
    parser = configparser.ConfigParser()
    try:
        parser.read(config_file)
        return parser.get('client', 'password', fallback=None)
    except Exception as e:
        warn(f"Failed to read owner config {config_file}: {e}")
        return None


def get_tier_permissions(tier: str) -> List[str]:
    """
    Get database permissions for a given tier.

    Standard tier permissions:
    - guest: SELECT only
    - verified: SELECT, INSERT
    - admin: SELECT, INSERT, UPDATE, DELETE
    - root: Full DDL permissions

    Args:
        tier: The tier name (guest, verified, admin, root)

    Returns:
        List of permission strings

    Raises:
        ValueError: If tier is not recognized
    """
    tier_permissions = {
        'guest': ['SELECT'],
        'verified': ['SELECT', 'INSERT'],
        'admin': ['SELECT', 'INSERT', 'UPDATE', 'DELETE'],
        'root': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'INDEX', 'REFERENCES']
    }

    if tier not in tier_permissions:
        raise ValueError(f"Unknown tier '{tier}'. Valid tiers: {', '.join(tier_permissions.keys())}")

    return tier_permissions[tier]


def read_user_password(project_name: str, tier: str) -> Optional[str]:
    """
    Read password from user's .<project>.cnf file.

    Args:
        project_name: The project name (e.g., 'henhouse')
        tier: The tier name (e.g., 'guest', 'admin')

    Returns:
        Password string if found, None otherwise
    """
    trace_in()
    try:
        username = f"{project_name}_{tier}"
        config_file = Path(f"/home/{username}/.{project_name}.cnf")

        debug(f"Looking for password file: {config_file}")

        if not config_file.exists():
            warn(f"Config file not found for {username}: {config_file}")
            trace_out()
            return None

        debug(f"Config file exists, reading content...")
        with open(config_file, 'r') as f:
            content = f.read()

        # Parse the config file to extract password
        password_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('password='):
                password = line.split('=', 1)[1].strip()
                password_lines.append(password)

        if password_lines:
            # Use the last password found
            password = password_lines[-1]
            log(f"Found password for {username}")
            trace_out()
            return password

        warn(f"No password found in config file for {username}")
        trace_out()
        return None

    except Exception as e:
        warn(f"Failed to read password for {username}: {e}")
        trace_out()
        return None


def create_database_user(conn, username: str, password: str) -> bool:
    """
    Create a database user.

    Args:
        conn: Database connection
        username: Username to create
        password: User password

    Returns:
        True if successful, False otherwise
    """
    trace_in()

    try:
        # Check if user already exists
        with conn.cursor() as cursor:
            cursor.execute("SELECT User FROM mysql.user WHERE User=%s AND host='%%'", (username,))
            result = cursor.fetchone()
            user_exists = result is not None

        if user_exists:
            log(f"Database user {username} already exists, updating password")
            with conn.cursor() as cursor:
                cursor.execute("ALTER USER %s@'%%' IDENTIFIED BY %s", (username, password))
                log(f"Updated password for {username}")
        else:
            # Create user
            with conn.cursor() as cursor:
                cursor.execute("CREATE USER %s@'%%' IDENTIFIED BY %s", (username, password))
                log(f"Created user {username}")

        # Flush privileges
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")

        trace_out()
        return True

    except Exception as e:
        warn(f"Failed to create database user {username}: {e}")
        report_error("action", f"Failed to create database user {username}: {str(e)}")
        trace_out()
        return False


def grant_permissions(conn, username: str, database: str, permissions: List[str]) -> bool:
    """
    Grant permissions to a user on a specific database.

    Args:
        conn: Database connection
        username: Username to grant permissions to
        database: Database name
        permissions: List of permissions to grant (e.g., ['SELECT', 'INSERT'])

    Returns:
        True if successful, False otherwise
    """
    trace_in()

    try:
        for permission in permissions:
            with conn.cursor() as cursor:
                cursor.execute(f"GRANT {permission} ON {database}.* TO %s@'%%'", (username,))
                debug(f"Granted {permission} on {database} to {username}")

        # Flush privileges
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")

        log(f"Granted {', '.join(permissions)} on {database} to {username}")
        trace_out()
        return True

    except Exception as e:
        warn(f"Failed to grant permissions on {database} to {username}: {e}")
        report_error("action", f"Failed to grant permissions: {str(e)}")
        trace_out()
        return False


def revoke_permissions(conn, username: str, database: str, permissions: List[str]) -> bool:
    """
    Revoke permissions from a user on a specific database.

    Args:
        conn: Database connection
        username: Username to revoke permissions from
        database: Database name
        permissions: List of permissions to revoke

    Returns:
        True if successful, False otherwise
    """
    trace_in()

    try:
        for permission in permissions:
            with conn.cursor() as cursor:
                cursor.execute(f"REVOKE {permission} ON {database}.* FROM %s@'%%'", (username,))
                debug(f"Revoked {permission} on {database} from {username}")

        # Flush privileges
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")

        log(f"Revoked {', '.join(permissions)} on {database} from {username}")
        trace_out()
        return True

    except Exception as e:
        warn(f"Failed to revoke permissions on {database} from {username}: {e}")
        trace_out()
        return False


def remove_database_user(conn, username: str) -> bool:
    """
    Remove a database user.

    Args:
        conn: Database connection
        username: Username to remove

    Returns:
        True if successful, False otherwise
    """
    trace_in()

    try:
        # Check if user exists
        with conn.cursor() as cursor:
            cursor.execute("SELECT User FROM mysql.user WHERE User=%s AND host='%%'", (username,))
            result = cursor.fetchone()
            user_exists = result is not None

        if not user_exists:
            log(f"Database user {username} does not exist, skipping removal")
            trace_out()
            return True

        # Drop user
        with conn.cursor() as cursor:
            cursor.execute("DROP USER %s@'%%'", (username,))
            log(f"Dropped user {username}")

        # Flush privileges
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")

        trace_out()
        return True

    except Exception as e:
        warn(f"Failed to remove database user {username}: {e}")
        report_error("action", f"Failed to remove database user {username}: {str(e)}")
        trace_out()
        return False
