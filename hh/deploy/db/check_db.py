import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.deploy_utils import detect_project_context
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

@register_action('check_db')
@register_command('check_db')
def check_db(args: Optional[List[str]] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    
    root_password = gateway.get_arg('password')
    if not root_password:
        warn("Root password is required for check_db")
        report_error("action", "Root password is required for check_db")
        trace_out()
        return False
    
    project_name, project_path = detect_project_context()
    log(f"Starting database check for project: {project_name}")
    table_info = []
    log(f"Checking database: {project_name}")
    
    # Step 1: Get table information
    if not is_error():
        try:
            # SHOW TABLES returns results with a dynamic column name like 'Tables_in_database'
            tables_result = gateway.conn.read("SHOW TABLES")
            log(f"SHOW TABLES returned {len(tables_result)} tables")
            
            for i, table_row in enumerate(tables_result):
                # Extract table name from the result (column name varies by database)
                table_name = list(table_row.values())[0]
                log(f"Processing table {i+1}/{len(tables_result)}: {table_name} (from dict)")
                
                count_query = f"SELECT COUNT(*) as count FROM `{table_name}`"
                count_result = gateway.conn.read(count_query)
                row_count = count_result[0]['count'] if count_result else 0
                log(f"Table {table_name}: {row_count} rows")
                table_info.append({
                    "table_name": table_name,
                    "row_count": row_count
                })
            log(f"Table info collection completed: {len(table_info)} tables processed")
        except Exception as e:
            warn(f"Failed to get table information: {str(e)}")
            report_error("backend", f"Failed to get table information: {str(e)}")
    
    # Step 2: Prepare response data
    if not is_error():
        try:
            # Format table info as proper table data with columns
            formatted_table_data = []
            if table_info:
                # Add header row
                formatted_table_data.append({
                    'field_type': 'table_info',
                    'label': f'{len(table_info)} table{"s" if len(table_info) != 1 else ""}',
                    'name': 'table_name',
                    'row_count': 'row_count'
                })
                # Add data rows
                for table in table_info:
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
                "table_count": len(table_info),
                "table_info": formatted_table_data
            }
            gateway.response.set_action_response(success_payload(result_data))
            log(f"Check DB completed successfully: {len(table_info)} tables found")
        except Exception as e:
            warn(f"Failed to prepare response data: {str(e)}")
            report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Check DB completed with errors")
        trace_out()
        return False
    log("Check DB completed successfully")
    trace_out()
    return True
