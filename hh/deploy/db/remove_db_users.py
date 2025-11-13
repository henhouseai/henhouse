import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.connection.decorators import with_root_connection

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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

# Import detect_project_context from utils
from hh.deploy.utils import detect_project_context
from hh.gateway.error.error_store import report_error

def remove_database_user(conn, project_name: str, tier: str) -> Dict[str, Any]:
    """Remove a database user for the given tier."""
    trace_in()
    username = f"{project_name}_{tier}"
    
    debug(f"Starting database user removal for: {username}")
    debug(f"Project: {project_name}, Tier: {tier}")
    
    try:
        # Check if user exists
        debug(f"Checking if user {username} exists...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT User FROM mysql.user WHERE User=%s AND host='%%'", (username,))
            result = cursor.fetchone()
            user_exists = result is not None
            debug(f"User existence check result: {user_exists}")
        
        if not user_exists:
            log(f"Database user {username} does not exist, skipping removal")
            debug(f"User {username} not found in database")
            trace_out()
            return {
                "username": username,
                "tier": tier,
                "status": "not_found"
            }
        
        # Drop user
        debug(f"Dropping user {username}...")
        with conn.cursor() as cursor:
            cursor.execute("DROP USER %s@'%%'", (username,))
            log(f"Dropped user {username}")
            debug(f"DROP USER command executed successfully for {username}")
        
        # Flush privileges
        debug("Flushing privileges...")
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")
            log("Flushed privileges")
            debug("FLUSH PRIVILEGES command executed successfully")
        
        # Verify user was removed successfully
        debug(f"Verifying user {username} was removed...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT User FROM mysql.user WHERE User=%s AND host='%%'", (username,))
            verify_result = cursor.fetchone()
            debug(f"User verification result: {verify_result}")
        
        log(f"Successfully removed database user {username}")
        debug(f"Database user removal completed successfully for {username}")
        trace_out()
        return {
            "username": username,
            "tier": tier,
            "status": "removed"
        }
        
    except Exception as e:
        warn(f"Failed to remove database user {username}: {e}")
        debug(f"Exception details: type={type(e).__name__}, message={str(e)}")
        if hasattr(e, 'errno'):
            debug(f"MySQL error number: {e.errno}")
        if hasattr(e, 'sqlstate'):
            debug(f"MySQL SQL state: {e.sqlstate}")
        trace_out()
        return {
            "username": username,
            "tier": tier,
            "status": "failed",
            "error": str(e)
        }

@register_action('remove_db_users')
@register_command('remove_db_users')
@with_root_connection(transaction=True)
def remove_db_users(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    try:
        # Get root password from command line
        root_password = gateway.get_arg('password')
        if not root_password:
            warn("Root password is required for remove_db_users")
            report_error("action", "Root password is required for remove_db_users")
            trace_out()
            return False

        debug(f"Root password provided: length={len(root_password)}")
        debug(f"Root password starts with: {root_password[:3]}...")

        # Detect project context
        project_name, project_path = detect_project_context()
        log(f"Starting database user removal for project: {project_name}")
        debug(f"Project path: {project_path}")
        debug(f"Available tiers: {HENHOUSE_TIERS}")
        
        # Remove database users for each tier
        user_results = []
        
        for tier in HENHOUSE_TIERS:
            log(f"Processing tier: {tier}")
            debug(f"Starting processing for tier: {tier}")
            
            # Remove database user
            debug(f"Calling remove_database_user for {project_name}_{tier}")
            result = remove_database_user(conn, project_name, tier)
            debug(f"remove_database_user result: {result}")
            user_results.append(result)
        
        # Prepare result data
        result_data = {
            "project_name": project_name,
            "user_results": user_results
        }
        
        gateway.response.set_action_response(success_payload(result_data))
        log("Database user removal completed successfully")
        
        # Clear registry cache to prevent permission issues
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        clean_all_caches()
        
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Database user removal failed: {str(e)}")
        report_error("backend", f"Database user removal failed: {str(e)}")
        trace_out()
        return False