import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pymysql
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.connection.decorators import root_read
from hh.gateway.connection.connection import load_dsn
from hh.deploy.utils import detect_project_context

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

@root_read
@register_action('clean_db')
@register_command('clean_db')
def clean_db(conn, args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Step 1: Validate required arguments
    root_password = gateway.get_arg('password')
    if not root_password:
        warn("Root password is required for clean_db")
        report_error("action", "Root password is required for clean_db")
    confirm = gateway.get_arg('confirm')
    if not confirm:
        warn("--confirm flag is required for clean_db")
        report_error("action", "--confirm flag is required for clean_db")
    
    project_name, project_path = detect_project_context()
    log(f"Starting db cleanup for project: {project_name}")
    cache_db_name = f"{project_name}_cache"
    
    # Step 2: Locate clean scripts
    clean_sql_path = project_path / "hh" / "deploy" / "db" / "clean.sql"
    clean_cache_sql_path = project_path / "hh" / "deploy" / "db" / "clean_cache.sql"
    for path in [clean_sql_path, clean_cache_sql_path]:
        if not is_error():
            if not path.exists():
                warn(f"Required SQL file not found at: {path}")
                report_error("action", f"SQL file not found at: {path}")
            else:
                log(f"Using SQL file: {path}")
    
    def run_clean_script(target_db: str, sql_path: Path, label: str) -> bool:
        if is_error():
            return False
        try:
            mysql_cmd = ["mysql", "--user=root", f"--password={root_password}", target_db]
            with open(sql_path, 'r') as sql_file:
                result = subprocess.run(
                    mysql_cmd,
                    stdin=sql_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            if result.returncode != 0:
                warn(f"{label} failed with return code {result.returncode}")
                warn(f"{label} stderr: {result.stderr}")
                report_error("backend", f"{label} failed: {result.stderr}")
                return False
            log(f"{label} completed successfully")
            return True
        except Exception as e:
            warn(f"{label} execution failed: {str(e)}")
            report_error("backend", f"{label} execution failed: {str(e)}")
            return False
    
    # Step 3: Execute clean scripts
    run_clean_script(project_name, clean_sql_path, "Main DB cleanup")
    run_clean_script(cache_db_name, clean_cache_sql_path, "Cache DB cleanup")
    
    # Step 4: Verify tables were dropped
    remaining_tables = []
    cache_remaining_tables = []
    if not is_error():
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                remaining_tables = cursor.fetchall()
                log(f"Remaining tables after cleanup (main): {len(remaining_tables)}")
        except Exception as e:
            warn(f"Failed to verify main table cleanup: {str(e)}")
            report_error("backend", f"Failed to verify main table cleanup: {str(e)}")
    
    if not is_error():
        try:
            dsn = load_dsn() or {}
            host = dsn.get('host', 'localhost')
            port = dsn.get('port', 3306)
            cache_conn = pymysql.connect(
                host=host,
                port=port,
                user='root',
                password=root_password,
                database=cache_db_name,
                cursorclass=pymysql.cursors.DictCursor
            )
            with cache_conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                cache_remaining_tables = cursor.fetchall()
                log(f"Remaining tables after cleanup (cache): {len(cache_remaining_tables)}")
            cache_conn.close()
        except Exception as e:
            warn(f"Failed to verify cache table cleanup: {str(e)}")
            report_error("backend", f"Failed to verify cache table cleanup: {str(e)}")
    
    # Step 5: Prepare response data
    if not is_error():
        try:
            result_data = {
                "project_name": project_name,
                "clean_sql_file": str(clean_sql_path),
                "clean_cache_sql_file": str(clean_cache_sql_path),
                "remaining_tables": len(remaining_tables),
                "cache_remaining_tables": len(cache_remaining_tables),
                "cleanup_successful": len(remaining_tables) == 0 and len(cache_remaining_tables) == 0
            }
            gateway.response.set_action_response(success_payload(result_data))
            log(f"Clean db completed successfully: {len(remaining_tables)} tables remaining")
        except Exception as e:
            warn(f"Failed to prepare response data: {str(e)}")
            report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Clean db completed with errors")
        trace_out()
        return False
    log("Clean db completed successfully")
    trace_out()
    return True
