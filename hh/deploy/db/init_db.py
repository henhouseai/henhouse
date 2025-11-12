import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.connection.decorators import root_read
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
@register_action('init_db')
@register_command('init_db')
def init_db(conn, args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
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
    
    # Step 2: Locate init.sql file
    init_sql_path = project_path / "hh" / "deploy" / "db" / "init.sql"
    if not is_error():
        if not init_sql_path.exists():
            warn(f"init.sql file not found at: {init_sql_path}")
            report_error("action", f"init.sql file not found at: {init_sql_path}")
        else:
            log(f"Using init.sql file: {init_sql_path}")
    
    # Step 3: Execute init.sql script
    if not is_error():
        try:
            mysql_cmd = ["mysql", f"--user=root", f"--password={root_password}", project_name ]
            with open(init_sql_path, 'r') as sql_file:
                result = subprocess.run(
                    mysql_cmd,
                    stdin=sql_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            if result.returncode != 0:
                warn(f"mysql execution failed with return code {result.returncode}")
                warn(f"mysql stderr: {result.stderr}")
                report_error("backend", f"DB initialization failed: {result.stderr}")
            else:
                log("DB initialization completed successfully")
        except Exception as e:
            warn(f"mysql execution failed: {str(e)}")
            report_error("backend", f"mysql execution failed: {str(e)}")
    
    # Step 4: Verify tables were created
    created_tables = []
    if not is_error():
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                created_tables = cursor.fetchall()
                log(f"Tables created after initialization: {len(created_tables)}")
        except Exception as e:
            warn(f"Failed to verify table creation: {str(e)}")
            report_error("backend", f"Failed to verify table creation: {str(e)}")
    
    # Step 5: Prepare response data
    if not is_error():
        try:
            result_data = {
                "project_name": project_name,
                "init_sql_file": str(init_sql_path),
                "created_tables": len(created_tables),
                "initialization_successful": len(created_tables) > 0
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
