"""
Root Connection Test - Tests RootConnection module directly.

This script tests the RootConnection module to verify it can:
1. Load passwords from install config
2. Connect to MySQL database using RootConnection
3. Execute a simple query

Usage: sudo hen root-test -root
"""
from __future__ import annotations
import os
from typing import Optional
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.error.error_store import report_error

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

@register_action('root_test')
@register_command('root_test')
def root_test() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    # Require -root flag and sudo/root privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("root_test requires sudo/root privileges")
        report_error("action", "root_test requires sudo/root privileges")
        trace_out()
        return False
    
    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for root_test")
        report_error("action", "Root flag (-root) is required for root_test")
        trace_out()
        return False
    
    project_name, project_path = detect_project_context()
    log(f"Starting root connection test for project: {project_name}")
    
    # Check if RootConnection was initialized
    if not gateway.conn:
        warn("No connection available - RootConnection not initialized")
        report_error("action", "No connection available")
        trace_out()
        return False
    
    if not gateway.conn.main:
        warn("Main database connection not available")
        report_error("action", "Main database connection not available")
        trace_out()
        return False
    
    # Test 1: Simple SELECT query
    try:
        log("Test 1: Executing SELECT 1")
        result = gateway.conn.read("SELECT 1 as test_value")
        if result and len(result) > 0:
            test_value = result[0].get('test_value')
            log(f"✓ Test 1 passed: SELECT 1 returned {test_value}")
        else:
            warn("Test 1 failed: No result returned")
            report_error("action", "Test 1 failed: No result returned")
            trace_out()
            return False
    except Exception as e:
        warn(f"Test 1 failed with exception: {str(e)}")
        report_error("action", f"Test 1 failed: {str(e)}")
        trace_out()
        return False
    
    # Test 2: Check current user
    try:
        log("Test 2: Checking current database user")
        result = gateway.conn.read("SELECT USER() as db_user")
        if result and len(result) > 0:
            db_user = result[0].get('db_user')
            log(f"✓ Test 2 passed: Connected as {db_user}")
        else:
            warn("Test 2 failed: No user result returned")
            report_error("action", "Test 2 failed: No user result returned")
            trace_out()
            return False
    except Exception as e:
        warn(f"Test 2 failed with exception: {str(e)}")
        report_error("action", f"Test 2 failed: {str(e)}")
        trace_out()
        return False
    
    # Test 3: Check current database
    try:
        log("Test 3: Checking current database")
        result = gateway.conn.read("SELECT DATABASE() as db_name")
        if result and len(result) > 0:
            db_name = result[0].get('db_name')
            log(f"✓ Test 3 passed: Connected to database {db_name}")
        else:
            warn("Test 3 failed: No database result returned")
            report_error("action", "Test 3 failed: No database result returned")
            trace_out()
            return False
    except Exception as e:
        warn(f"Test 3 failed with exception: {str(e)}")
        report_error("action", f"Test 3 failed: {str(e)}")
        trace_out()
        return False
    
    # Test 4: Check cache connection if available
    if gateway.conn.cache:
        try:
            log("Test 4: Testing cache connection")
            with gateway.conn.cache.cursor() as cursor:
                cursor.execute("SELECT 1 as test_value")
                result = cursor.fetchone()
                if result and result.get('test_value') == 1:
                    log("✓ Test 4 passed: Cache connection works")
                else:
                    warn("Test 4 failed: Cache connection returned unexpected result")
        except Exception as e:
            warn(f"Test 4 failed with exception: {str(e)}")
    else:
        log("Test 4 skipped: Cache connection not available")
    
    # Prepare response
    result_data = {
        "project_name": project_name,
        "status": "success",
        "tests_passed": 3,
        "message": "Root connection test completed successfully"
    }
    gateway.response.set_action_response(success_payload(result_data))
    
    log("Root connection test completed successfully")
    trace_out()
    return True

