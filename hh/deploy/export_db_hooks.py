"""
Framework hooks for export_db command.

Provides pre-validation, database export, cleanup, and rendering hooks.
"""

import os
import configparser
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path
from hh.deploy.db_import_export_helpers import (
    create_export_directory,
    create_temp_cnf_file,
    cleanup_temp_cnf_file,
    export_database,
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

# Global cross-cutting config for export operations
EXPORT_CONFIG: Dict[str, Any] = {}


@register_module_hook('export_db_00_pre_validate', 'Pre-validate and setup export')
def export_db_pre_validate():
    """Pre-validate export_db requirements and create export directory."""
    trace_in()

    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    # Require -root flag and sudo/root privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("export_db requires sudo/root privileges")
        report_error("action", "export_db requires sudo/root privileges")
        return trace_out({"success": False, "message": "Requires sudo/root privileges"})

    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for export_db")
        report_error("action", "Root flag (-root) is required for export_db")
        return trace_out({"success": False, "message": "Root flag required"})

    # Get project context
    project_name, project_path = detect_project_context()
    log(f"Starting database export for project: {project_name}")

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

    # Create timestamp and export directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = create_export_directory(project_path, timestamp)

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
    EXPORT_CONFIG.update({
        "project_name": project_name,
        "project_path": project_path,
        "export_dir": export_dir,
        "timestamp": timestamp,
        "temp_cnf_main": temp_cnf_main,
        "temp_cnf_cache": temp_cnf_cache,
        "mysql_tls_enabled": mysql_tls_enabled,
        "ssl_ca_path": ssl_ca_path,
        "cache_ssl_ca_path": cache_ssl_ca_path,
        "ssl_verify_mode": ssl_verify_mode
    })

    log(f"Export pre-validation completed: {export_dir}")

    return trace_out({
        "success": True,
        "message": "Pre-validation completed",
        "export_dir": str(export_dir)
    })


@register_module_hook('export_db_05_export_cache', 'Export cache database')
def export_cache_database():
    """Export cache database to SQL file."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    project_name = EXPORT_CONFIG.get("project_name")
    export_dir = EXPORT_CONFIG.get("export_dir")
    timestamp = EXPORT_CONFIG.get("timestamp")
    temp_cnf_cache = EXPORT_CONFIG.get("temp_cnf_cache")

    if not all([project_name, export_dir, timestamp, temp_cnf_cache]):
        warn("EXPORT_CONFIG not properly initialized")
        report_error("action", "Export config not initialized")
        return trace_out({"success": False, "message": "Config not initialized"})

    cache_db_name = f"{project_name}_cache"

    # Get table info before export
    gateway = get_gateway()
    table_info = collect_table_info_for_db(gateway, 'cache')

    # Export cache database
    result = export_database(cache_db_name, export_dir, timestamp, temp_cnf_cache)

    if not result["success"]:
        report_error("action", f"Failed to export cache database: {result.get('error', 'Unknown error')}")
        return trace_out({"success": False, "message": "Cache export failed"})

    # Store result for rendering
    EXPORT_CONFIG["cache_export"] = {
        "db_name": cache_db_name,
        "export_path": result["export_path"],
        "file_size": result["file_size"],
        "table_count": len(table_info),
        "table_info": table_info
    }

    log(f"Exported cache database: {result['file_size']} bytes")

    return trace_out({
        "success": True,
        "message": f"Exported {cache_db_name}",
        "export_path": result["export_path"],
        "file_size": result["file_size"]
    })


@register_module_hook('export_db_10_export_main', 'Export main database')
def export_main_database():
    """Export main database to SQL file."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    project_name = EXPORT_CONFIG.get("project_name")
    export_dir = EXPORT_CONFIG.get("export_dir")
    timestamp = EXPORT_CONFIG.get("timestamp")
    temp_cnf_main = EXPORT_CONFIG.get("temp_cnf_main")

    if not all([project_name, export_dir, timestamp, temp_cnf_main]):
        warn("EXPORT_CONFIG not properly initialized")
        report_error("action", "Export config not initialized")
        return trace_out({"success": False, "message": "Config not initialized"})

    main_db_name = project_name

    # Get table info before export
    gateway = get_gateway()
    table_info = collect_table_info_for_db(gateway, 'main')

    # Export main database
    result = export_database(main_db_name, export_dir, timestamp, temp_cnf_main)

    if not result["success"]:
        report_error("action", f"Failed to export main database: {result.get('error', 'Unknown error')}")
        return trace_out({"success": False, "message": "Main export failed"})

    # Store result for rendering
    EXPORT_CONFIG["main_export"] = {
        "db_name": main_db_name,
        "export_path": result["export_path"],
        "file_size": result["file_size"],
        "table_count": len(table_info),
        "table_info": table_info
    }

    log(f"Exported main database: {result['file_size']} bytes")

    return trace_out({
        "success": True,
        "message": f"Exported {main_db_name}",
        "export_path": result["export_path"],
        "file_size": result["file_size"]
    })


@register_module_hook('export_db_90_cleanup', 'Cleanup temporary files')
def export_db_cleanup():
    """Remove temporary credential files and fix ownership."""
    trace_in()

    temp_cnf_main = EXPORT_CONFIG.get("temp_cnf_main")
    temp_cnf_cache = EXPORT_CONFIG.get("temp_cnf_cache")

    if temp_cnf_main:
        cleanup_temp_cnf_file(temp_cnf_main)

    if temp_cnf_cache:
        cleanup_temp_cnf_file(temp_cnf_cache)

    # Fix file ownership (optional, non-critical)
    gateway = get_gateway()
    export_dir = EXPORT_CONFIG.get("export_dir")

    if gateway and gateway.files and export_dir:
        try:
            import os as _os
            current_user = _os.environ.get('SUDO_USER') or _os.environ.get('USER')
            if current_user and gateway.os:
                user_info = gateway.os.get_user_by_name(current_user)
                if user_info:
                    # Change ownership of export directory and all files within
                    gateway.files.chown(str(export_dir), current_user, recursive=True)
                    log(f"Fixed ownership of export directory to user: {current_user}")
        except Exception as e:
            warn(f"Failed to fix file ownership: {e}")

    log("Export cleanup completed")

    return trace_out({"success": True, "message": "Cleanup completed"})


@register_module_hook('export_db_95_render', 'Render export summary')
def render_export_summary():
    """Contribute export summary info to rendering."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    export_dir = EXPORT_CONFIG.get("export_dir", "")
    main_export = EXPORT_CONFIG.get("main_export", {})
    cache_export = EXPORT_CONFIG.get("cache_export", {})

    # Add export directory row
    table_data.add_row('export_directory', value=str(export_dir))

    # Add main database export info
    if main_export:
        main_size = main_export.get("file_size", 0)
        main_path = Path(main_export.get("export_path", "")).name
        main_tables = main_export.get("table_count", 0)
        table_data.add_row(
            'main_database',
            value=f"{main_path} ({main_size:,} bytes, {main_tables} tables)"
        )

    # Add cache database export info
    if cache_export:
        cache_size = cache_export.get("file_size", 0)
        cache_path = Path(cache_export.get("export_path", "")).name
        cache_tables = cache_export.get("table_count", 0)
        table_data.add_row(
            'cache_database',
            value=f"{cache_path} ({cache_size:,} bytes, {cache_tables} tables)"
        )

    field_config.add_simple(['export_directory', 'main_database', 'cache_database'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })
