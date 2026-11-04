"""
Database user creation hooks for Henhouse framework.

Creates tier-based database users and manages credential files.
"""

import os
import configparser
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.deploy.db_helpers import create_mysql_credentials_file
from hh.deploy.db_config import DB_CONFIG
from hh.deploy.install_helpers_config import get_install_config_path
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.db_user_helpers import read_user_password, create_database_user
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


@register_module_hook('add_db_users_00_pre_validate', 'Load config and create credential files')
def pre_validate():
    """
    Pre-validation: Load install config and create temporary credential files.

    Also loads the tier list from user_account_suffixes.
    """
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    project_name, project_path = detect_project_context()
    cfg_path = get_install_config_path(project_name)

    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        return trace_out({"success": False, "message": f"Install config not found: {cfg_path}"})

    # Load install config
    parser = configparser.ConfigParser()
    parser.read(cfg_path)

    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        return trace_out({"success": False, "message": "Missing [install] section"})

    sec = parser["install"]

    # Get passwords
    mysql_root_password_main = sec.get("mysql_root_password_main", "").strip()
    mysql_root_password_cache = sec.get("mysql_root_password_cache", "").strip()

    if not mysql_root_password_main or not mysql_root_password_cache:
        warn("Missing MySQL root passwords in config")
        return trace_out({"success": False, "message": "Missing MySQL root passwords"})

    # Get TLS settings
    mysql_tls_enabled_str = sec.get("mysql_tls_enabled", "0").strip()
    try:
        mysql_tls_enabled = int(mysql_tls_enabled_str) != 0
    except ValueError:
        mysql_tls_enabled = False

    ssl_ca_path = sec.get("ssl_ca_path", "").strip()
    cache_ssl_ca_path = sec.get("cache_ssl_ca_path", "").strip()

    # Get ssl_verify_mode from root user's .{project}.cnf file
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

    # Create main DB credentials file
    main_creds_file = create_mysql_credentials_file(
        mysql_root_password_main,
        mysql_tls_enabled,
        ssl_ca_path,
        ssl_verify_mode
    )

    if not main_creds_file:
        return trace_out({"success": False, "message": "Failed to create main credentials file"})

    # Create cache DB credentials file
    cache_creds_file = create_mysql_credentials_file(
        mysql_root_password_cache,
        mysql_tls_enabled,
        cache_ssl_ca_path,
        ssl_verify_mode
    )

    if not cache_creds_file:
        # Clean up main file
        try:
            os.unlink(main_creds_file)
        except Exception:
            pass
        return trace_out({"success": False, "message": "Failed to create cache credentials file"})

    # Load tier list - error if not found (no fallback)
    try:
        from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
    except ImportError as e:
        warn(f"Failed to import HENHOUSE_TIERS: {e}")
        report_error("action", f"Failed to import tier list: {str(e)}")
        return trace_out({"success": False, "message": "Failed to import tier list"})

    # Store in DB_CONFIG for other hooks to access
    DB_CONFIG["project_name"] = project_name
    DB_CONFIG["main_db"] = project_name
    DB_CONFIG["cache_db"] = f"{project_name}_cache"
    DB_CONFIG["main_credentials_file"] = main_creds_file
    DB_CONFIG["cache_credentials_file"] = cache_creds_file
    DB_CONFIG["tier_list"] = HENHOUSE_TIERS

    log(f"Created MySQL credentials files for {project_name}")
    log(f"Loaded tiers: {', '.join(HENHOUSE_TIERS)}")

    return trace_out({
        "success": True,
        "message": "Pre-validation complete",
        "tiers": HENHOUSE_TIERS
    })


@register_module_hook('add_db_users_05_create_users', 'Create tier-based database users')
def create_tier_users():
    """
    Create database users for each tier.

    Users are created but no permissions are granted yet.
    Modules will grant permissions in later phases.
    """
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    conn = gateway.conn.main
    project_name = DB_CONFIG.get("project_name")
    tier_list = DB_CONFIG.get("tier_list", [])

    if not tier_list:
        warn("Tier list not found in DB_CONFIG")
        return trace_out({"success": False, "message": "Tier list not loaded"})

    user_results = []

    for tier in tier_list:
        username = f"{project_name}_{tier}"

        # Read password from user's config file
        password = read_user_password(project_name, tier)
        if not password:
            warn(f"No password found for {username}, skipping")
            user_results.append({
                "tier": tier,
                "username": username,
                "status": "failed",
                "error": "no password"
            })
            continue

        # Create user
        success = create_database_user(conn, username, password)

        user_results.append({
            "tier": tier,
            "username": username,
            "status": "created" if success else "failed"
        })

    return trace_out({
        "success": True,
        "message": f"Created {len([r for r in user_results if r['status'] == 'created'])} tier users",
        "user_results": user_results
    })


@register_module_hook('add_db_users_90_cleanup', 'Remove temporary credential files')
def cleanup_credentials():
    """
    Remove temporary MySQL credential files created during user creation.
    """
    trace_in()

    main_creds_file = DB_CONFIG.get("main_credentials_file")
    cache_creds_file = DB_CONFIG.get("cache_credentials_file")

    cleaned = []

    if main_creds_file:
        try:
            if os.path.exists(main_creds_file):
                os.unlink(main_creds_file)
                cleaned.append(main_creds_file)
                log(f"Removed main credentials file: {main_creds_file}")
        except Exception as e:
            warn(f"Failed to remove main credentials file: {e}")

    if cache_creds_file:
        try:
            if os.path.exists(cache_creds_file):
                os.unlink(cache_creds_file)
                cleaned.append(cache_creds_file)
                log(f"Removed cache credentials file: {cache_creds_file}")
        except Exception as e:
            warn(f"Failed to remove cache credentials file: {e}")

    return trace_out({
        "success": True,
        "message": "Cleaned up credential files",
        "files_removed": cleaned
    })


@register_module_hook('add_db_users_95_render', 'Render database user creation summary')
def render_user_creation():
    """Contribute database user creation info to add_db_users summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    # Add tier users created
    tier_list = DB_CONFIG.get("tier_list", [])
    if tier_list:
        table_data.add_row('tier_users', value=', '.join(tier_list))
        field_config.add_simple(['tier_users'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })
