"""
Shared helper functions for database import/export operations.

These functions are used by both export_db and import_db hooks to handle
mysqldump and mysql operations with proper credential management.
"""

import os
import subprocess
import tempfile
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


def create_export_directory(project_path: Path, timestamp: str) -> Path:
    """Create timestamped export directory.

    Args:
        project_path: Project root path
        timestamp: Timestamp string (YYYYMMDD_HHMMSS)

    Returns:
        Path to created export directory
    """
    trace_in()

    dumps_dir = project_path / "database_dumps"
    dumps_dir.mkdir(exist_ok=True)

    export_dir = dumps_dir / f"export_{timestamp}"
    export_dir.mkdir(exist_ok=True)

    log(f"Created export directory: {export_dir}")

    return trace_out(export_dir)


def create_temp_cnf_file(root_password: str, mysql_tls_enabled: bool = False,
                         ssl_ca_path: str = "", ssl_verify_mode: int = 2) -> str:
    """Create temporary MySQL credentials file.

    Args:
        root_password: MySQL root password
        mysql_tls_enabled: Whether TLS is enabled
        ssl_ca_path: Path to SSL CA certificate
        ssl_verify_mode: SSL verification mode (0-3)

    Returns:
        Path to temporary .cnf file
    """
    trace_in()

    with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='mysql_', suffix='.cnf') as opt_file:
        opt_file.write(f"[client]\n")
        opt_file.write(f"user=root\n")
        opt_file.write(f"password={root_password}\n")

        if mysql_tls_enabled and ssl_ca_path:
            opt_file.write(f"ssl-ca={ssl_ca_path}\n")

            # Map verify_mode to MySQL ssl-mode
            if ssl_verify_mode == 0:
                opt_file.write(f"ssl-mode=REQUIRED\n")
            elif ssl_verify_mode == 1:
                opt_file.write(f"ssl-mode=REQUIRED\n")
            elif ssl_verify_mode == 2:
                opt_file.write(f"ssl-mode=VERIFY_CA\n")
            elif ssl_verify_mode == 3:
                opt_file.write(f"ssl-mode=VERIFY_IDENTITY\n")
            else:
                opt_file.write(f"ssl-mode=REQUIRED\n")

        opt_file_path = opt_file.name

    os.chmod(opt_file_path, 0o600)
    log(f"Created temporary credentials file: {opt_file_path}")

    return trace_out(opt_file_path)


def cleanup_temp_cnf_file(cnf_path: str) -> None:
    """Remove temporary MySQL credentials file.

    Args:
        cnf_path: Path to temporary .cnf file
    """
    trace_in()

    try:
        if os.path.exists(cnf_path):
            os.unlink(cnf_path)
            log(f"Removed temporary credentials file: {cnf_path}")
    except Exception as e:
        warn(f"Failed to remove temporary credentials file {cnf_path}: {e}")

    trace_out()


def export_database(db_name: str, export_dir: Path, timestamp: str,
                   cnf_file_path: str) -> Dict[str, Any]:
    """Export a database using mysqldump.

    Args:
        db_name: Name of database to export
        export_dir: Directory to write export file
        timestamp: Timestamp string for filename
        cnf_file_path: Path to temporary MySQL credentials file

    Returns:
        Dict with success status, export_path, file_size, and error message if failed
    """
    trace_in()

    export_filename = f"{db_name}_{timestamp}.sql"
    export_filepath = export_dir / export_filename

    mysqldump_cmd = [
        "mysqldump",
        f"--defaults-file={cnf_file_path}",
        "--single-transaction",
        "--skip-add-drop-table",
        "--disable-keys",
        "--extended-insert",
        db_name
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
                warn(f"mysqldump failed for {db_name}: {result.stderr}")
                return trace_out({
                    "success": False,
                    "export_path": str(export_filepath),
                    "error": result.stderr
                })

        file_size = export_filepath.stat().st_size
        log(f"Exported {db_name} to {export_filepath} ({file_size} bytes)")

        return trace_out({
            "success": True,
            "export_path": str(export_filepath),
            "file_size": file_size
        })

    except Exception as e:
        warn(f"Failed to export {db_name}: {str(e)}")
        return trace_out({
            "success": False,
            "export_path": str(export_filepath),
            "error": str(e)
        })


def find_import_file(import_dir: Path, db_prefix: str) -> Optional[str]:
    """Find import file matching database prefix.

    Args:
        import_dir: Directory containing import files
        db_prefix: Database name prefix (e.g., 'main', 'cache')

    Returns:
        Path to matching SQL file, or None if not found
    """
    trace_in()

    pattern = str(import_dir / f"{db_prefix}_*.sql")
    matches = sorted(glob.glob(pattern))

    if not matches:
        warn(f"No import file found matching pattern: {pattern}")
        return trace_out(None)

    # Take first match (alphabetically sorted)
    import_file = matches[0]
    log(f"Found import file for {db_prefix}: {import_file}")

    return trace_out(import_file)


def import_database(db_name: str, sql_file_path: str, cnf_file_path: str) -> Dict[str, Any]:
    """Import a database from SQL file using mysql.

    Args:
        db_name: Name of database to import to
        sql_file_path: Path to SQL file to import
        cnf_file_path: Path to temporary MySQL credentials file

    Returns:
        Dict with success status and error message if failed
    """
    trace_in()

    mysql_cmd = ["mysql", f"--defaults-file={cnf_file_path}", db_name]

    try:
        with open(sql_file_path, 'r') as import_file:
            result = subprocess.run(
                mysql_cmd,
                stdin=import_file,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:
            warn(f"mysql import failed for {db_name}: {result.stderr}")
            return trace_out({
                "success": False,
                "error": result.stderr
            })

        log(f"Imported {sql_file_path} to {db_name}")

        return trace_out({
            "success": True
        })

    except Exception as e:
        warn(f"Failed to import {db_name}: {str(e)}")
        return trace_out({
            "success": False,
            "error": str(e)
        })


def collect_table_info_for_db(gateway, db_type: str) -> List[Dict[str, Any]]:
    """Collect table information for a database.

    Args:
        gateway: Gateway object with database connections
        db_type: 'main' or 'cache'

    Returns:
        List of dicts with table_name and row_count
    """
    trace_in()

    info: List[Dict[str, Any]] = []

    if not gateway or not gateway.conn:
        return trace_out(info)

    try:
        if db_type == 'main':
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

        elif db_type == 'cache':
            if not gateway.conn.cache:
                return trace_out(info)

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

        log(f"Collected table info for {db_type} database: {len(info)} tables")

    except Exception as e:
        warn(f"Failed to collect table info for {db_type}: {str(e)}")

    return trace_out(info)
