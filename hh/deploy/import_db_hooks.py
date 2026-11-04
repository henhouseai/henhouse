"""
Framework hooks for import_db command.

Provides pre-validation, database import, cleanup, and rendering hooks.
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path
from hh.deploy.db_import_export_helpers import (
    create_temp_cnf_file,
    cleanup_temp_cnf_file,
    find_import_file,
    import_database,
    collect_table_info_for_db
)
from hh.render.render import TableData, FieldConfig

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

# Global cross-cutting config for import operations
IMPORT_CONFIG: Dict[str, Any] = {}


@register_module_hook('import_db_00_pre_validate', 'Pre-validate and setup import')
def import_db_pre_validate():
    """Pre-validate import_db requirements and validate import directory."""
    trace_in()

    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    # Require -root flag and sudo/root privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("import_db requires sudo/root privileges")
        report_error("action", "import_db requires sudo/root privileges")
        return trace_out({"success": False, "message": "Requires sudo/root privileges"})

    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for import_db")
        report_error("action", "Root flag (-root) is required for import_db")
        return trace_out({"success": False, "message": "Root flag required"})

    # Get import directory
    directory = gateway.get_arg('directory')
    if not directory:
        warn("Directory is required for import_db")
        report_error("action", "Directory is required for import_db")
        return trace_out({"success": False, "message": "Directory required"})

    import_dir = Path(directory)
    if not import_dir.exists() or not import_dir.is_dir():
        warn(f"Import directory does not exist or is not a directory: {import_dir}")
        report_error("action", f"Invalid import directory: {import_dir}")
        return trace_out({"success": False, "message": "Invalid import directory"})

    # Get project context
    project_name, project_path = detect_project_context()
    log(f"Starting database import for project: {project_name}")
    log(f"Import directory: {import_dir}")

    # Load root passwords from install config
    cfg_path = get_install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Root install config not found: {cfg_path}")
        report_error("action", "Failed to load root install config")
        return trace_out({"success": False, "message": "Install config not found"})

    parser = configparser.ConfigParser()
    parser.read(cfg_path)

    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        report_error("action", "Invalid install config")
        return trace_out({"success": False, "message": "Invalid install config"})

    sec = parser["install"]

    # Read TLS settings
    mysql_tls_enabled_str = sec.get("mysql_tls_enabled", "0").strip()
    try:
        mysql_tls_enabled = int(mysql_tls_enabled_str) != 0
    except ValueError:
        mysql_tls_enabled = False

    ssl_ca_path = sec.get("ssl_ca_path", "").strip()
    cache_ssl_ca_path = sec.get("cache_ssl_ca_path", "").strip()

    # Read ssl_verify_mode from root user's .{project}.cnf file
    root_config_path = Path('/root') / f'.{project_name}.cnf'
    ssl_verify_mode = 2  # default
    if root_config_path.exists():
        root_config = configparser.ConfigParser()
        root_config.read(root_config_path)
        if 'client' in root_config:
            try:
                ssl_verify_mode = int(root_config.get('client', 'ssl_verify_mode', fallback='2'))
            except (ValueError, configparser.NoOptionError):
                ssl_verify_mode = 2

    # Create temporary credential files for main and cache
    mysql_root_password_main = sec.get("mysql_root_password_main", "").strip()
    mysql_root_password_cache = sec.get("mysql_root_password_cache", "").strip()

    if not mysql_root_password_main or not mysql_root_password_cache:
        warn("Missing root passwords in install config")
        report_error("action", "Missing root passwords")
        return trace_out({"success": False, "message": "Missing root passwords"})

    temp_cnf_main = create_temp_cnf_file(
        mysql_root_password_main,
        mysql_tls_enabled,
        ssl_ca_path,
        ssl_verify_mode
    )

    temp_cnf_cache = create_temp_cnf_file(
        mysql_root_password_cache,
        mysql_tls_enabled,
        cache_ssl_ca_path,
        ssl_verify_mode
    )

    # Populate cross-cutting config
    IMPORT_CONFIG.update({
        "project_name": project_name,
        "project_path": project_path,
        "import_dir": import_dir,
        "temp_cnf_main": temp_cnf_main,
        "temp_cnf_cache": temp_cnf_cache,
        "mysql_tls_enabled": mysql_tls_enabled,
        "ssl_ca_path": ssl_ca_path,
        "cache_ssl_ca_path": cache_ssl_ca_path,
        "ssl_verify_mode": ssl_verify_mode
    })

    log(f"Import pre-validation completed: {import_dir}")

    return trace_out({
        "success": True,
        "message": "Pre-validation completed",
        "import_dir": str(import_dir)
    })


@register_module_hook('import_db_05_import_cache', 'Import cache database')
def import_cache_database():
    """Import cache database from SQL file."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    project_name = IMPORT_CONFIG.get("project_name")
    import_dir = IMPORT_CONFIG.get("import_dir")
    temp_cnf_cache = IMPORT_CONFIG.get("temp_cnf_cache")

    if not all([project_name, import_dir, temp_cnf_cache]):
        warn("IMPORT_CONFIG not properly initialized")
        report_error("action", "Import config not initialized")
        return trace_out({"success": False, "message": "Config not initialized"})

    cache_db_name = f"{project_name}_cache"

    # Find import file
    import_file = find_import_file(import_dir, "cache")
    if not import_file:
        warn(f"No cache import file found in {import_dir}")
        report_error("action", "Cache import file not found")
        return trace_out({"success": False, "message": "Cache import file not found"})

    # Get table info before import
    gateway = get_gateway()
    table_info_before = collect_table_info_for_db(gateway, 'cache')

    # Import cache database
    result = import_database(cache_db_name, import_file, temp_cnf_cache)

    if not result["success"]:
        report_error("action", f"Failed to import cache database: {result.get('error', 'Unknown error')}")
        return trace_out({"success": False, "message": "Cache import failed"})

    # Get table info after import
    table_info_after = collect_table_info_for_db(gateway, 'cache')

    # Get file size
    file_size = Path(import_file).stat().st_size

    # Store result for rendering
    IMPORT_CONFIG["cache_import"] = {
        "db_name": cache_db_name,
        "import_path": import_file,
        "file_size": file_size,
        "table_count": len(table_info_after),
        "table_info_before": table_info_before,
        "table_info_after": table_info_after
    }

    log(f"Imported cache database: {file_size} bytes, {len(table_info_after)} tables")

    return trace_out({
        "success": True,
        "message": f"Imported {cache_db_name}",
        "import_path": import_file,
        "file_size": file_size
    })


@register_module_hook('import_db_10_import_main', 'Import main database')
def import_main_database():
    """Import main database from SQL file."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    project_name = IMPORT_CONFIG.get("project_name")
    import_dir = IMPORT_CONFIG.get("import_dir")
    temp_cnf_main = IMPORT_CONFIG.get("temp_cnf_main")

    if not all([project_name, import_dir, temp_cnf_main]):
        warn("IMPORT_CONFIG not properly initialized")
        report_error("action", "Import config not initialized")
        return trace_out({"success": False, "message": "Config not initialized"})

    main_db_name = project_name

    # Find import file
    import_file = find_import_file(import_dir, "main")
    if not import_file:
        warn(f"No main import file found in {import_dir}")
        report_error("action", "Main import file not found")
        return trace_out({"success": False, "message": "Main import file not found"})

    # Get table info before import
    gateway = get_gateway()
    table_info_before = collect_table_info_for_db(gateway, 'main')

    # Import main database
    result = import_database(main_db_name, import_file, temp_cnf_main)

    if not result["success"]:
        report_error("action", f"Failed to import main database: {result.get('error', 'Unknown error')}")
        return trace_out({"success": False, "message": "Main import failed"})

    # Get table info after import
    table_info_after = collect_table_info_for_db(gateway, 'main')

    # Get file size
    file_size = Path(import_file).stat().st_size

    # Store result for rendering
    IMPORT_CONFIG["main_import"] = {
        "db_name": main_db_name,
        "import_path": import_file,
        "file_size": file_size,
        "table_count": len(table_info_after),
        "table_info_before": table_info_before,
        "table_info_after": table_info_after
    }

    log(f"Imported main database: {file_size} bytes, {len(table_info_after)} tables")

    return trace_out({
        "success": True,
        "message": f"Imported {main_db_name}",
        "import_path": import_file,
        "file_size": file_size
    })


@register_module_hook('import_db_90_cleanup', 'Cleanup temporary files')
def import_db_cleanup():
    """Remove temporary credential files."""
    trace_in()

    temp_cnf_main = IMPORT_CONFIG.get("temp_cnf_main")
    temp_cnf_cache = IMPORT_CONFIG.get("temp_cnf_cache")

    if temp_cnf_main:
        cleanup_temp_cnf_file(temp_cnf_main)

    if temp_cnf_cache:
        cleanup_temp_cnf_file(temp_cnf_cache)

    log("Import cleanup completed")

    return trace_out({"success": True, "message": "Cleanup completed"})


@register_module_hook('import_db_95_render', 'Render import summary')
def render_import_summary():
    """Contribute import summary info to rendering."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    import_dir = IMPORT_CONFIG.get("import_dir", "")
    main_import = IMPORT_CONFIG.get("main_import", {})
    cache_import = IMPORT_CONFIG.get("cache_import", {})

    # Add import directory row
    table_data.add_row('import_directory', value=str(import_dir))

    # Add main database import info
    if main_import:
        main_size = main_import.get("file_size", 0)
        main_path = Path(main_import.get("import_path", "")).name
        main_tables = main_import.get("table_count", 0)
        table_data.add_row(
            'main_database',
            value=f"{main_path} ({main_size:,} bytes, {main_tables} tables)"
        )

    # Add cache database import info
    if cache_import:
        cache_size = cache_import.get("file_size", 0)
        cache_path = Path(cache_import.get("import_path", "")).name
        cache_tables = cache_import.get("table_count", 0)
        table_data.add_row(
            'cache_database',
            value=f"{cache_path} ({cache_size:,} bytes, {cache_tables} tables)"
        )

    field_config.add_simple(['import_directory', 'main_database', 'cache_database'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })
