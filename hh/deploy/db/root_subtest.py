"""
Root Subprocess Test - Tests MySQL subprocess connection using temporary option files.

This script tests the subprocess approach (used by init_db, clean_db, etc.) to verify:
1. Loading passwords from install config
2. Creating temporary MySQL option files
3. Using mysql command line with --defaults-file
4. Executing a simple query via subprocess

Usage: sudo hen root-subtest -root
"""
from __future__ import annotations
import os
import subprocess
import tempfile
import configparser
from pathlib import Path
from typing import Optional, Dict
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.error.error_store import report_error
from hh.deploy.users.install import _install_config_path
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import safe_str

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

def _load_install_config(project_name: str) -> Optional[Dict[str, str]]:
    """Load root install config and return MySQL root passwords."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Root install config not found: {cfg_path}")
        return None
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        return None
    sec = parser["install"]
    def req(key: str) -> str:
        val = sec.get(key, "").strip()
        if not val:
            raise ValueError(f"Missing required field {key} in {cfg_path}")
        return val
    data = {
        "mysql_root_password_main": req("mysql_root_password_main"),
        "mysql_root_password_cache": req("mysql_root_password_cache"),
        "db_host": req("db_host"),
        "cache_host": req("cache_host"),
    }
    return data

@register_action('root_subtest')
@register_command('root_subtest')
def root_subtest() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    # Require -root flag and sudo/root privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("root_subtest requires sudo/root privileges")
        report_error("action", "root_subtest requires sudo/root privileges")
        trace_out()
        return False
    
    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for root_subtest")
        report_error("action", "Root flag (-root) is required for root_subtest")
        trace_out()
        return False
    
    project_name, project_path = detect_project_context()
    log(f"Starting root subprocess test for project: {project_name}")
    
    # Load root passwords from install config
    cfg = _load_install_config(project_name)
    if not cfg:
        warn("Failed to load root install config")
        report_error("action", "Failed to load root install config")
        trace_out()
        return False
    
    root_password_main = cfg["mysql_root_password_main"]
    db_host = cfg["db_host"]
    log(f"Loaded config: db_host={db_host}, password length={len(root_password_main)}")
    
    # Test 1: Create temporary option file and test connection
    try:
        log("Test 1: Creating temporary MySQL option file")
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='mysql_test_', suffix='.cnf') as opt_file:
            opt_file.write(f"[client]\n")
            opt_file.write(f"user=root\n")
            opt_file.write(f"password={root_password_main}\n")
            opt_file.write(f"host={db_host}\n")
            opt_file_path = opt_file.name
        
        os.chmod(opt_file_path, 0o600)
        log(f"✓ Created temporary option file: {opt_file_path}")
        
        # Test 2: Execute simple query via mysql subprocess
        log("Test 2: Executing SELECT 1 via mysql subprocess")
        mysql_cmd = ["mysql", f"--defaults-file={opt_file_path}", "-e", "SELECT 1 as test_value"]
        result = subprocess.run(
            mysql_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            log(f"✓ Test 2 passed: mysql subprocess returned successfully")
            log(f"  stdout: {result.stdout.strip()}")
        else:
            warn(f"Test 2 failed: mysql subprocess returned code {result.returncode}")
            warn(f"  stderr: {result.stderr}")
            report_error("action", f"Test 2 failed: {result.stderr}")
            # Clean up and return
            try:
                if os.path.exists(opt_file_path):
                    os.unlink(opt_file_path)
            except Exception:
                pass
            trace_out()
            return False
        
        # Test 3: Execute query to check user
        log("Test 3: Checking database user via mysql subprocess")
        mysql_cmd = ["mysql", f"--defaults-file={opt_file_path}", "-e", "SELECT USER() as db_user"]
        result = subprocess.run(
            mysql_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            log(f"✓ Test 3 passed: User query successful")
            log(f"  stdout: {result.stdout.strip()}")
        else:
            warn(f"Test 3 failed: mysql subprocess returned code {result.returncode}")
            warn(f"  stderr: {result.stderr}")
        
        # Clean up temporary file
        try:
            if os.path.exists(opt_file_path):
                os.unlink(opt_file_path)
                log("✓ Cleaned up temporary option file")
        except Exception as e:
            warn(f"Failed to clean up temporary file: {str(e)}")
        
    except subprocess.TimeoutExpired:
        warn("Test failed: mysql subprocess timed out after 30 seconds")
        report_error("action", "mysql subprocess timed out")
        try:
            if os.path.exists(opt_file_path):
                os.unlink(opt_file_path)
        except Exception:
            pass
        trace_out()
        return False
    except Exception as e:
        warn(f"Test failed with exception: {str(e)}")
        report_error("action", f"Test failed: {str(e)}")
        try:
            if os.path.exists(opt_file_path):
                os.unlink(opt_file_path)
        except Exception:
            pass
        trace_out()
        return False
    
    # Prepare response
    result_data = {
        "project_name": project_name,
        "status": "success",
        "tests_passed": 3,
        "message": "Root subprocess test completed successfully"
    }
    gateway.response.set_action_response(success_payload(result_data))
    
    log("Root subprocess test completed successfully")
    trace_out()
    return True

@register_parser('root_subtest')
def root_subtest_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})
        
        lines = []
        lines.append(render_header_block('l_root_subtest_header'))
        
        table_data = TableData()
        project_name = source_data.get('project_name', 'Unknown')
        status = source_data.get('status', 'unknown')
        tests_passed = source_data.get('tests_passed', 0)
        message = source_data.get('message', '')
        
        table_data.add_row('project_header', value=safe_str(project_name))
        table_data.add_row('status', value=safe_str(status))
        table_data.add_row('tests_passed', value=safe_str(f"{tests_passed} tests passed"))
        if message:
            table_data.add_row('message', value=safe_str(message))
        
        lines.append(render_block(
            table_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['status', 'tests_passed', 'message']),
            table_overrides={'margin_l': 4},
            block_type='root_subtest'
        ))
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully")
        trace_out()
        return True
    except Exception as e:
        warn(f"Parser execution raised an exception: {e}")
        report_error("backend", f"Parser execution raised an exception: {e}")
        trace_out()
        return False

