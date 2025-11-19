import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pymysql
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.connection.decorators import root_read
from hh.gateway.connection.connection import load_dsn
from hh.deploy.utils import detect_project_context
from hh.gateway.error.error_store import report_error, is_error

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

def _collect_table_info(connection) -> List[Dict[str, Any]]:
    info: List[Dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table_row in tables:
            table_name = list(table_row.values())[0]
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count_result = cursor.fetchone()
            row_count = list(count_result.values())[0]
            info.append({
                "table_name": table_name,
                "row_count": row_count
            })
    return info

def _get_target_connection(db_name: str, root_password: str):
    dsn = load_dsn() or {}
    host = dsn.get('host', 'localhost')
    port = dsn.get('port', 3306)
    return pymysql.connect(
        host=host,
        port=port,
        user='root',
        password=root_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )

@root_read
@register_action('import_db')
@register_command('import_db')
def import_db(conn, args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Get required parameters
    root_password = gateway.get_arg('password')
    if not root_password:
        warn("Root password is required for import_db")
        report_error("action", "Root password is required for import_db")
        trace_out()
        return False
    
    filename = gateway.get_arg('filename')
    if not filename:
        warn("Filename is required for import_db")
        report_error("action", "Filename is required for import_db")
        trace_out()
        return False
    
    project_name, project_path = detect_project_context()
    log(f"Starting database import for project: {project_name}")
    
    # Check if file exists
    import_filepath = Path(filename)
    if not import_filepath.exists():
        warn(f"Import file does not exist: {import_filepath}")
        report_error("action", f"Import file does not exist: {import_filepath}")
        trace_out()
        return False
    
    # Get file size
    try:
        file_size = import_filepath.stat().st_size
        log(f"Import file size: {file_size} bytes")
    except Exception as e:
        warn(f"Failed to get import file size: {str(e)}")
        report_error("action", f"Failed to get import file size: {str(e)}")
        trace_out()
        return False
    
    target_db = gateway.get_arg('database')
    cache_flag = gateway.get_arg('cache')
    if not target_db:
        if cache_flag:
            target_db = f"{project_name}_cache"
        else:
            target_db = project_name
    log(f"Target database for import: {target_db}")
    
    # Step 1: Get current table information before import
    current_table_info: List[Dict[str, Any]] = []
    if not is_error():
        try:
            if target_db == project_name:
                current_table_info = _collect_table_info(conn)
            else:
                target_conn = _get_target_connection(target_db, root_password)
                current_table_info = _collect_table_info(target_conn)
                target_conn.close()
            log(f"Current table info collection completed: {len(current_table_info)} tables processed")
        except Exception as e:
            warn(f"Failed to get current table information: {str(e)}")
            report_error("backend", f"Failed to get current table information: {str(e)}")
    
    # Step 2: Run mysql import
    if not is_error():
        mysql_cmd = ["mysql", f"--user=root", f"--password={root_password}", target_db]
        try:
            with open(import_filepath, 'r') as import_file:
                result = subprocess.run(
                    mysql_cmd,
                    stdin=import_file,
                    stderr=subprocess.PIPE,
                    text=True
                )
            if result.returncode != 0:
                warn(f"mysql import failed with return code {result.returncode}")
                warn(f"mysql stderr: {result.stderr}")
                report_error("backend", f"Database import failed: {result.stderr}")
        except Exception as e:
            warn(f"mysql import execution failed: {str(e)}")
            report_error("backend", f"mysql import execution failed: {str(e)}")
    
    # Step 3: Get table information after import
    final_table_info: List[Dict[str, Any]] = []
    if not is_error():
        try:
            if target_db == project_name:
                final_table_info = _collect_table_info(conn)
            else:
                final_conn = _get_target_connection(target_db, root_password)
                final_table_info = _collect_table_info(final_conn)
                final_conn.close()
            log(f"Final table info collection completed: {len(final_table_info)} tables processed")
        except Exception as e:
            warn(f"Failed to get final table information: {str(e)}")
            report_error("backend", f"Failed to get final table information: {str(e)}")
    
    # Step 4: Prepare response data
    try:
        # Format table info as proper table data with columns
        formatted_table_data = []
        if final_table_info:
            # Add header row
            formatted_table_data.append({
                'field_type': 'table_info',
                'label': f'{len(final_table_info)} table{"s" if len(final_table_info) != 1 else ""}',
                'name': 'table_name',
                'row_count': 'row_count'
            })
            # Add data rows
            for table in final_table_info:
                table_name = table.get('table_name', 'Unknown')
                row_count = table.get('row_count', 0)
                formatted_table_data.append({
                    'field_type': 'table_info',
                    'label': '',
                    'name': table_name,
                    'row_count': f"{row_count:,}"
                })
        
        result_data = {
            "project_name": project_name,
            "database": target_db,
            "import_file": str(import_filepath),
            "import_size": file_size,
            "table_count": len(final_table_info),
            "table_info": formatted_table_data,
            "current_table_info": current_table_info,
            "has_errors": is_error()
        }
        gateway.response.set_action_response(success_payload(result_data))
        log(f"Import DB completed: {file_size} bytes, {len(final_table_info)} tables, errors: {is_error()}")
    except Exception as e:
        warn(f"Failed to prepare response data: {str(e)}")
        report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Import DB completed with errors")
        trace_out()
        return False
    log("Import DB completed successfully")
    trace_out()
    return True
