import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.connection.decorators import root_read
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
    
    # Step 1: Get current table information before import
    current_table_info = []
    if not is_error():
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                log(f"SHOW TABLES returned {len(tables)} tables before import")
                for i, table_row in enumerate(tables):
                    table_name = list(table_row.values())[0]
                    log(f"Processing table {i+1}/{len(tables)}: {table_name} (from dict)")
                    count_query = f"SELECT COUNT(*) FROM `{table_name}`"
                    cursor.execute(count_query)
                    count_result = cursor.fetchone()
                    row_count = list(count_result.values())[0]
                    log(f"Table {table_name}: {row_count} rows")
                    current_table_info.append({
                        "table_name": table_name,
                        "row_count": row_count
                    })
            log(f"Current table info collection completed: {len(current_table_info)} tables processed")
        except Exception as e:
            warn(f"Failed to get current table information: {str(e)}")
            report_error("backend", f"Failed to get current table information: {str(e)}")
    
    # Step 2: Run mysql import
    if not is_error():
        mysql_cmd = ["mysql", f"--user=root", f"--password={root_password}", project_name]
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
    final_table_info = []
    if not is_error():
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                log(f"SHOW TABLES returned {len(tables)} tables after import")
                for i, table_row in enumerate(tables):
                    table_name = list(table_row.values())[0]
                    log(f"Processing table {i+1}/{len(tables)}: {table_name} (from dict)")
                    count_query = f"SELECT COUNT(*) FROM `{table_name}`"
                    cursor.execute(count_query)
                    count_result = cursor.fetchone()
                    row_count = list(count_result.values())[0]
                    log(f"Table {table_name}: {row_count} rows")
                    final_table_info.append({
                        "table_name": table_name,
                        "row_count": row_count
                    })
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
