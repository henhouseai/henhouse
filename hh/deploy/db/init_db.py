import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.deploy_utils import detect_project_context

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

@register_action('init_db')
@register_command('init_db')
def init_db(args: Optional[List[str]] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    
    # Step 1: Validate required arguments
    root_password = gateway.get_arg('password')
    if not root_password:
        warn("Root password is required for init_db")
        report_error("action", "Root password is required for init_db")
    confirm = gateway.get_arg('confirm')
    if not confirm:
        warn("--confirm flag is required for init_db")
        report_error("action", "--confirm flag is required for init_db")
    
    project_name, project_path = detect_project_context()
    log(f"Starting db initialization for project: {project_name}")
    cache_db_name = f"{project_name}_cache"
    
    # Step 2: Locate init scripts
    init_sql_path = project_path / "hh" / "deploy" / "db" / "init.sql"
    init_cache_sql_path = project_path / "hh" / "deploy" / "db" / "init_cache.sql"
    for path in [init_sql_path, init_cache_sql_path]:
        if not is_error():
            if not path.exists():
                warn(f"Required SQL file not found at: {path}")
                report_error("action", f"SQL file not found at: {path}")
            else:
                log(f"Using SQL file: {path}")
    
    # Step 3: Ensure databases exist
    if not is_error():
        create_db_cmds = [
            f"CREATE DATABASE IF NOT EXISTS `{project_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            f"CREATE DATABASE IF NOT EXISTS `{cache_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        ]
        for stmt in create_db_cmds:
            result = subprocess.run(
                ["mysql", "--user=root", f"--password={root_password}", "-e", stmt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                warn(f"Failed to execute statement '{stmt}': {result.stderr}")
                report_error("backend", f"Database creation failed: {result.stderr}")
                break
    
    # Step 4: Execute init scripts
    def run_sql_script(target_db: str, sql_path: Path, label: str) -> bool:
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
                warn(f"{label} execution failed with return code {result.returncode}")
                warn(f"{label} stderr: {result.stderr}")
                report_error("backend", f"{label} failed: {result.stderr}")
                return False
            log(f"{label} completed successfully")
            return True
        except Exception as e:
            warn(f"{label} execution failed: {str(e)}")
            report_error("backend", f"{label} execution failed: {str(e)}")
            return False
    
    run_sql_script(project_name, init_sql_path, "Main DB initialization")
    run_sql_script(cache_db_name, init_cache_sql_path, "Cache DB initialization")
    
    # Step 4.5: Execute extension schema if it exists
    ext_schema_path = project_path / "ext" / "deploy" / "db" / "schema_ext.sql"
    if ext_schema_path.exists():
        run_sql_script(project_name, ext_schema_path, "Extension schema")
    
    # Step 5: Verify tables were created
    created_tables = []
    cache_tables = []
    if not is_error():
        try:
            created_tables = gateway.conn.read("SHOW TABLES")
            log(f"Main DB tables after initialization: {len(created_tables)}")
        except Exception as e:
            warn(f"Failed to verify main tables: {str(e)}")
            report_error("backend", f"Failed to verify main tables: {str(e)}")
    
    if not is_error():
        try:
            # Use gateway's cache connection (RootConnection provides root access to cache)
            if gateway.conn.cache is None:
                warn("Cache connection not available")
                trace_out()
                return False
            with gateway.conn.cache.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                cache_tables = cursor.fetchall()
                log(f"Cache DB tables after initialization: {len(cache_tables)}")
        except Exception as e:
            warn(f"Failed to verify cache tables: {str(e)}")
            report_error("backend", f"Failed to verify cache tables: {str(e)}")
    
    # Step 6: Prepare response data
    if not is_error():
        try:
            result_data = {
                "project_name": project_name,
                "init_sql_file": str(init_sql_path),
                "cache_sql_file": str(init_cache_sql_path),
                "created_tables": len(created_tables),
                "cache_tables": len(cache_tables),
                "cache_database": cache_db_name,
                "initialization_successful": len(created_tables) > 0 and len(cache_tables) > 0
            }
            gateway.response.set_action_response(success_payload(result_data))
            log(f"Init db completed successfully: {len(created_tables)} tables created")
        except Exception as e:
            warn(f"Failed to prepare response data: {str(e)}")
            report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Init db completed with errors")
        trace_out()
        return False
    log("Init db completed successfully")
    trace_out()
    return True
