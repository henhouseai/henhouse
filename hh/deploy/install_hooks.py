"""
Core installation hooks with INSTALL_CONFIG global.

This module contains the global INSTALL_CONFIG that other modules can import and contribute to.
"""

import os
import datetime
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error
from hh.deploy.user_accounts import create_user_config_file, create_user_gateway_scripts, create_user_entry_point_scripts, setup_human_user_home, setup_root_user_script, detect_project_owner
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path, load_install_config, validate_config_value, validate_entry_point_script_name

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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

# INTENTIONALLY CROSS-CUTTABLE GLOBAL
# Other modules import and modify this during template/install execution
INSTALL_CONFIG: Dict[str, Any] = {
    "mode": "unknown",           # "template" or "install"
    "project_name": "",
    "project_path": None,
    "config_path": None,
    "template_lines": [],        # For template mode - modules append here
    "parsed_config": {},         # For install mode - loaded from config file
}

# Module-scoped config storage for core settings
core_config: Dict[str, Any] = {}


def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@register_module_hook('install_00_pre_validate', 'Detect installation mode')
def detect_install_mode() -> Dict[str, Any]:
    """Determine if we're in template or install mode."""
    trace_in()

    project_name, project_path = detect_project_context()
    if not project_name:
        error_msg = "Could not detect project name"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    cfg_path = get_install_config_path(project_name)

    INSTALL_CONFIG["project_name"] = project_name
    INSTALL_CONFIG["project_path"] = project_path
    INSTALL_CONFIG["config_path"] = cfg_path

    if not cfg_path.exists():
        # Template mode - config doesn't exist yet
        INSTALL_CONFIG["mode"] = "template"
        log(f"Install mode: template (config not found at {cfg_path})")
        return trace_out({"status": "success", "mode": "template", "project_name": project_name})
    else:
        # Install mode - config exists
        INSTALL_CONFIG["mode"] = "install"
        log(f"Install mode: install (config found at {cfg_path})")
        return trace_out({"status": "success", "mode": "install", "project_name": project_name})


@register_module_hook('install_01_template_contribute', 'Contribute hh core template sections')
def contribute_core_template() -> Dict[str, Any]:
    """Add core framework template sections."""
    trace_in()

    if INSTALL_CONFIG["mode"] != "template":
        return trace_out({"status": "skipped"})

    core_template = [
        "[install]",
        "",
        "# ========================================",
        "# Entry Point Script",
        "# ========================================",
        "# Entry point script name (defaults to hen)",
        "entry_point_script_name = hen",
        "",
        "# ========================================",
        "# Human User Credentials",
        "# ========================================",
        "# Database password for human user",
        "password_human_db = CHANGE_ME",
        "# HTTP Basic Auth password for human user",
        "htaccess_human_password = CHANGE_ME",
        "",
        "# ========================================",
        "# Database Configuration",
        "# ========================================",
        "# Database hosts",
        "# For localhost deployment (default - no changes needed for local testing):",
        "db_host = localhost",
        "cache_host = localhost",
        "# For public deployment with subdomains:",
        "# db_host = db.example.tld",
        "# cache_host = cache.example.tld",
        "",
        "# MySQL root passwords (per DB host)",
        "mysql_root_password_main = CHANGE_ME",
        "mysql_root_password_cache = CHANGE_ME",
        "",
        "# MySQL TLS/SSL Configuration",
        "# TLS enabled (1 = enabled, 0 = disabled)",
        "# For localhost deployment (plain text connections recommended for initial testing):",
        "mysql_tls_enabled = 0",
        "# For public deployment (TLS/SSL recommended):",
        "# mysql_tls_enabled = 1",
        "",
        "# MySQL SSL Certificate Paths",
        "# SSL CA paths (absolute paths, only used if mysql_tls_enabled = 1)",
        "# For localhost deployment (self-signed certificates):",
        "ssl_ca_path = /etc/mysql/ssl/ca.pem",
        "cache_ssl_ca_path = /etc/mysql/ssl/ca.pem",
        "# For public deployment (Let's Encrypt certificates):",
        "# ssl_ca_path = /etc/mysql/ssl/ca.pem",
        "# cache_ssl_ca_path = /etc/mysql/ssl/ca.pem",
        "",
        "# MySQL SSL Directory and Certificate Paths",
        "# MySQL SSL directory (where SSL certificates are stored)",
        "mysql_ssl_dir = /etc/mysql/ssl",
        "# MySQL server certificate path (full path to server certificate)",
        "mysql_server_cert_path = /etc/mysql/ssl/server-cert.pem",
        "# MySQL server key path (full path to server private key)",
        "mysql_server_key_path = /etc/mysql/ssl/server-key.pem",
        "# MySQL configuration file path",
        "mysql_config_path = /etc/mysql/mysql.conf.d/mysqld.cnf",
        "",
    ]

    INSTALL_CONFIG["template_lines"].extend(core_template)
    log(f"hh core: Added {len(core_template)} lines to template")
    return trace_out({"status": "success", "lines_contributed": len(core_template)})


@register_module_hook('install_02_template_write', 'Write install template file')
def write_template_file() -> Dict[str, Any]:
    """Write the aggregated template to disk."""
    trace_in()

    if INSTALL_CONFIG["mode"] != "template":
        return trace_out({"status": "skipped"})

    config_path = INSTALL_CONFIG["config_path"]
    template_lines = INSTALL_CONFIG["template_lines"]

    config_path.write_text("\n".join(template_lines), encoding="utf-8")
    os.chmod(config_path, 0o600)

    log(f"Template created at {config_path}")

    gateway = get_gateway()
    if gateway and gateway.response:
        gateway.response.set_action_response(success_payload({
            "status": "template_created",
            "config_status": "Config Not Found",
            "config_path": str(config_path),
            "template_location": str(config_path),
            "template_created": "Yes",
            "next_steps": "Edit template and rerun install"
        }))

    return trace_out({"status": "success", "template_path": str(config_path)})


@register_module_hook('install_05_pre_validate', 'Validate core configuration')
def validate_core_config() -> Dict[str, Any]:
    """Validate core configuration from install config file."""
    trace_in()
    global core_config

    if INSTALL_CONFIG["mode"] != "install":
        return trace_out({"status": "skipped"})

    project_name = INSTALL_CONFIG["project_name"]

    try:
        cfg = load_install_config(project_name)
    except Exception as e:
        error_msg = f"Install config invalid: {e}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    if not cfg:
        error_msg = "Install config missing"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    # Validate required fields
    for key in (
        "db_host",
        "cache_host",
        "mysql_root_password_main",
        "mysql_root_password_cache",
        "password_human_db",
        "htaccess_human_password",
    ):
        try:
            validate_config_value(key, cfg.get(key, ""))
        except ValueError as e:
            error_msg = str(e)
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

    # Check for existing users in manifest
    manifest_users = cfg.get("manifest_users", {})
    gateway = get_gateway()
    if manifest_users:
        existing_users = []
        for uname in manifest_users.keys():
            try:
                if gateway.os and gateway.os.user_exists(uname):
                    existing_users.append(uname)
            except Exception:
                pass
        if existing_users:
            error_msg = f"Existing install detected (users present): {', '.join(existing_users)}. Uninstall first."
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})
        else:
            error_msg = "Previous install entries found in manifest_users; clear them from the config before reinstall."
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

    # Validate entry point script name
    entry_point_script_name = cfg.get("entry_point_script_name", "hen")
    try:
        validate_entry_point_script_name(entry_point_script_name)
    except Exception as e:
        error_msg = f"Install config invalid: {e}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    # Parse MySQL TLS enabled setting
    mysql_tls_enabled_str = cfg.get("mysql_tls_enabled", "0").strip()
    try:
        mysql_tls_enabled = int(mysql_tls_enabled_str) != 0
    except ValueError:
        mysql_tls_enabled = False

    # Auto-detect ssl_verify_mode based on db_host
    db_host = cfg["db_host"]
    ssl_verify_mode = 0 if db_host in ("localhost", "127.0.0.1") else 3
    log(f"Auto-detected ssl_verify_mode={ssl_verify_mode} based on db_host={db_host}")

    # Store validated config in module global
    core_config.update(cfg)
    core_config["mysql_tls_enabled"] = mysql_tls_enabled
    core_config["ssl_verify_mode"] = ssl_verify_mode

    # Store in INSTALL_CONFIG for other modules
    INSTALL_CONFIG["parsed_config"] = cfg

    log("hh core: Configuration validated successfully")
    return trace_out({"status": "success"})


@register_module_hook('install_45_scripts', 'Create gateway and entry point scripts')
def setup_gateway_scripts() -> Dict[str, Any]:
    """Create user gateway scripts and entry point scripts."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    entry_point_script_name = core_config.get("entry_point_script_name", "hen")

    try:
        # Create user gateway scripts
        create_user_gateway_scripts(project_name, entry_point_script_name)

        # Create user entry point scripts
        create_user_entry_point_scripts(project_name, entry_point_script_name)

        log("hh core: Gateway and entry point scripts created")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to create scripts: {str(e)}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_50_user_env', 'Set up human and root user environments')
def setup_user_environments() -> Dict[str, Any]:
    """Set up human user and root user home directories."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    project_path = INSTALL_CONFIG["project_path"]
    project_owner = detect_project_owner(project_path)
    entry_point_script_name = core_config.get("entry_point_script_name", "hen")
    password_human_db = core_config["password_human_db"]
    db_host = core_config["db_host"]
    ssl_ca_path = core_config["ssl_ca_path"]
    cache_host = core_config["cache_host"]
    cache_ssl_ca_path = core_config["cache_ssl_ca_path"]
    ssl_verify_mode = core_config["ssl_verify_mode"]
    mysql_tls_enabled = core_config["mysql_tls_enabled"]

    try:
        # Set up human user home directory
        setup_human_user_home(project_name, project_path, entry_point_script_name)

        # Create config file for human user with human DB credentials
        if project_owner:
            create_user_config_file(
                project_owner,
                project_name,
                password_human_db,
                db_user=project_owner,
                host=db_host,
                ssl_ca=ssl_ca_path if mysql_tls_enabled else None,
                cache_host=cache_host,
                cache_ssl_ca=cache_ssl_ca_path if mysql_tls_enabled else None,
                ssl_verify_mode=ssl_verify_mode if mysql_tls_enabled else None,
                mysql_tls_enabled=mysql_tls_enabled
            )

        # Set up root user entry point
        setup_root_user_script(project_name, project_path, entry_point_script_name)

        # Create config file for root user with human DB credentials (shared)
        if project_owner:
            create_user_config_file(
                "root",
                project_name,
                password_human_db,
                db_user=project_owner,
                host=db_host,
                ssl_ca=ssl_ca_path if mysql_tls_enabled else None,
                cache_host=cache_host,
                cache_ssl_ca=cache_ssl_ca_path if mysql_tls_enabled else None,
                ssl_verify_mode=ssl_verify_mode if mysql_tls_enabled else None,
                mysql_tls_enabled=mysql_tls_enabled
            )

        log("hh core: Human and root user environments configured")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to setup user environments: {str(e)}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_65_cache_cleanup', 'Clean all caches')
def clean_caches() -> Dict[str, Any]:
    """Clear registry cache to prevent permission issues."""
    trace_in()

    try:
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        clean_all_caches()

        log("hh core: Caches cleaned")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to clean caches: {str(e)}"
        warn(error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_95_render', 'Render installation summary')
def render_install_summary() -> Dict[str, Any]:
    """Render installation summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - parser will aggregate from all modules
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
