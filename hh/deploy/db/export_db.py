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

def _collect_table_info(gateway, db_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Collect table information using gateway.conn.read()."""
    info: List[Dict[str, Any]] = []
    if not gateway or not gateway.conn:
        return info
    
    try:
        # SHOW TABLES returns results with a dynamic column name
        tables = gateway.conn.read("SHOW TABLES")
        for table_row in tables:
            table_name = list(table_row.values())[0]
            count_query = f"SELECT COUNT(*) as count FROM `{table_name}`"
            count_result = gateway.conn.read(count_query)
            row_count = count_result[0]['count'] if count_result else 0
            info.append({
                "table_name": table_name,
                "row_count": row_count
            })
    except Exception as e:
        warn(f"Failed to collect table info: {str(e)}")
    return info

def _collect_cache_table_info(gateway) -> List[Dict[str, Any]]:
    """Collect table information from cache database using gateway.conn.cache."""
    info: List[Dict[str, Any]] = []
    if not gateway or not gateway.conn or not gateway.conn.cache:
        return info
    
    try:
        with gateway.conn.cache.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for table_row in tables:
                table_name = list(table_row.values())[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                count_result = cursor.fetchone()
                row_count = count_result['count'] if count_result else 0
                info.append({
                    "table_name": table_name,
                    "row_count": row_count
                })
    except Exception as e:
        warn(f"Failed to collect cache table info: {str(e)}")
    return info

@register_action('export_db')
@register_command('export_db')
def export_db(args: Optional[List[str]] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    root_password = gateway.get_arg('password')
    if not root_password:
        warn("Root password is required for export_db")
        report_error("action", "Root password is required for export_db")
        trace_out()
        return False
    project_name, project_path = detect_project_context()
    log(f"Starting database export for project: {project_name}")
    dumps_dir = project_path / "database_dumps"
    dumps_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"{project_name}_export_{timestamp}.sql"
    export_filepath = dumps_dir / export_filename
    table_info = []
    log(f"Export file: {export_filepath}")
    
    target_db = gateway.get_arg('database')
    cache_flag = gateway.get_arg('cache')
    if not target_db:
        if cache_flag:
            target_db = f"{project_name}_cache"
        else:
            target_db = project_name
    log(f"Target database for export: {target_db}")
    
    # Step 1: Get table information
    if not is_error():
        try:
            if target_db == project_name:
                table_info = _collect_table_info(gateway)
            else:
                # For cache DB, use gateway.conn.cache (RootConnection provides root access)
                table_info = _collect_cache_table_info(gateway)
            log(f"Table info collection completed: {len(table_info)} tables processed")
        except Exception as e:
            warn(f"Failed to get table information: {str(e)}")
            report_error("backend", f"Failed to get table information: {str(e)}")
    
    # Step 2: Run mysqldump
    if not is_error():
        mysqldump_cmd = [
            "mysqldump",
            f"--user=root",
            f"--password={root_password}",
            "--single-transaction",
            "--skip-add-drop-table",
            "--disable-keys",
            "--extended-insert",
            target_db
        ]
        try:
            with open(export_filepath, 'w') as export_file:
                # Add foreign key disable statements at the beginning
                export_file.write("SET FOREIGN_KEY_CHECKS=0;\n")
                export_file.write("SET UNIQUE_CHECKS=0;\n")
                export_file.write("SET AUTOCOMMIT=0;\n")
                export_file.write("START TRANSACTION;\n")
                
                # Run mysqldump
                result = subprocess.run(
                    mysqldump_cmd,
                    stdout=export_file,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Add foreign key enable statements at the end
                export_file.write("COMMIT;\n")
                export_file.write("SET FOREIGN_KEY_CHECKS=1;\n")
                export_file.write("SET UNIQUE_CHECKS=1;\n")
                export_file.write("SET AUTOCOMMIT=1;\n")
                
            if result.returncode != 0:
                warn(f"mysqldump failed with return code {result.returncode}")
                warn(f"mysqldump stderr: {result.stderr}")
                report_error("backend", f"Database export failed: {result.stderr}")
        except Exception as e:
            warn(f"mysqldump execution failed: {str(e)}")
            report_error("backend", f"mysqldump execution failed: {str(e)}")
    
    # Step 3: Get export size
    if not is_error():
        try:
            export_size = export_filepath.stat().st_size
            log(f"Database export completed: {export_size} bytes")
        except Exception as e:
            warn(f"Failed to get export file size: {str(e)}")
            report_error("backend", f"Failed to get export file size: {str(e)}")
    
    # Step 4: Fix file ownership (optional, non-critical)
    if not is_error() and gateway.files:
        try:
            import os as _os
            current_user = _os.environ.get('SUDO_USER') or _os.environ.get('USER')
            if current_user and gateway.os:
                user_info = gateway.os.get_user_by_name(current_user)
                if user_info:
                    gateway.files.chown(str(export_filepath), user_info['uid'])
                    gateway.files.chown(str(dumps_dir), user_info['uid'])
                    log(f"Fixed ownership of dump file and directory to user: {current_user}")
        except Exception as e:
            warn(f"Failed to fix file ownership: {e}")
    
    # Step 5: Prepare response data
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
                "database": target_db,
                "export_file": str(export_filepath),
                "export_size": export_size,
                "table_count": len(table_info),
                "table_info": formatted_table_data
            }
            gateway.response.set_action_response(success_payload(result_data))
            log(f"Export DB completed successfully: {export_size} bytes")
        except Exception as e:
            warn(f"Failed to prepare response data: {str(e)}")
            report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Export DB completed with errors")
        trace_out()
        return False
    log("Export DB completed successfully")
    trace_out()
    return True