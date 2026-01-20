"""
Core installation hooks with INSTALL_CONFIG global.

This module contains the global INSTALL_CONFIG that other modules can import and contribute to.
"""

import os
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.users.access import auto_scan_user_keys, generate_ssh_keys, add_user_key
from hh.deploy.users.user_accounts import create_user_config_file, update_user_paths, create_user_gateway_scripts, create_user_entry_point_scripts, setup_human_user_home, setup_root_user_script, detect_project_owner
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path, load_install_config, validate_config_value, validate_entry_point_script_name
from hh.deploy.install_helpers_manifest import write_manifest_users

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
        "# ========================================",
        "# Application Passwords",
        "# ========================================",
        "# DB user passwords (guest, verified, admin, root)",
        "password_guest = CHANGE_ME",
        "password_verified = CHANGE_ME",
        "password_admin = CHANGE_ME",
        "password_root = CHANGE_ME",
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
        "password_guest",
        "password_verified",
        "password_admin",
        "password_root",
        "htaccess_admin_password",
        "htaccess_panel_password",
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


@register_module_hook('install_10_conflict_check', 'Check for existing users and groups')
def check_user_group_conflicts() -> Dict[str, Any]:
    """Check for existing project setup."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    project_path = INSTALL_CONFIG["project_path"]
    entry_point_script_name = core_config.get("entry_point_script_name", "hen")

    gateway = get_gateway()
    conflicts = []

    try:
        # Check for existing project users
        project_users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in project_users:
            if gateway and gateway.os and gateway.os.user_exists(user):
                conflicts.append(f"user {user}")
                log(f"Found existing user: {user}")

        # Check for existing project groups
        project_groups = [project_name, f"{project_name}_deploy", f"{project_name}_admin"]
        for group in project_groups:
            if gateway and gateway.os and gateway.os.group_exists(group):
                conflicts.append(f"group {group}")
                log(f"Found existing group: {group}")

        if conflicts:
            error_msg = f"Existing setup detected. Please run uninstall first. Found: {', '.join(conflicts)}"
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

        # Check for script conflicts
        project_owner = detect_project_owner(project_path)

        script_conflicts = []
        root_home = Path('/root')
        root_hen = root_home / 'hen'
        root_expected_hen = root_home / entry_point_script_name

        if root_hen.exists() and entry_point_script_name == 'hen':
            script_conflicts.append(f"/root/hen")
        elif root_expected_hen.exists() and entry_point_script_name != 'hen':
            script_conflicts.append(f"/root/{entry_point_script_name}")

        if project_owner:
            human_home = Path(f'/home/{project_owner}')
            human_hen = human_home / 'hen'
            human_expected_hen = human_home / entry_point_script_name

            if human_hen.exists() and entry_point_script_name == 'hen':
                script_conflicts.append(f"/home/{project_owner}/hen")
            elif human_expected_hen.exists() and entry_point_script_name != 'hen':
                script_conflicts.append(f"/home/{project_owner}/{entry_point_script_name}")

        if script_conflicts:
            error_msg = f"Script conflicts detected. Please specify -hen flag with a custom script name. Found conflicts: {', '.join(script_conflicts)}"
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

        log("hh core: No conflicts found")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Error checking for conflicts: {str(e)}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_15_groups', 'Create core groups')
def create_core_groups() -> Dict[str, Any]:
    """Create core groups that users need to be added to."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]

    try:
        log(f"hh core: Setting up core groups: {project_name}")

        # Create project group
        try:
            subprocess.run(['groupadd', project_name], check=True, capture_output=True)
            log(f"Created group: {project_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr.decode():
                log(f"Group {project_name} already exists")
            else:
                raise

        # Create deploy group
        deploy_group_name = f"{project_name}_deploy"
        try:
            subprocess.run(['groupadd', deploy_group_name], check=True, capture_output=True)
            log(f"Created group: {deploy_group_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr.decode():
                log(f"Group {deploy_group_name} already exists")
            else:
                raise

        # Create admin group
        admin_group_name = f"{project_name}_admin"
        try:
            subprocess.run(['groupadd', admin_group_name], check=True, capture_output=True)
            log(f"Created group: {admin_group_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr.decode():
                log(f"Group {admin_group_name} already exists")
            else:
                raise

        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to setup core groups: {str(e)}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_20_users', 'Create tier users')
def create_tier_users() -> Dict[str, Any]:
    """Create fresh tier users with SSH keys and config files."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    project_path = INSTALL_CONFIG["project_path"]

    passwords = [
        core_config["password_guest"],
        core_config["password_verified"],
        core_config["password_admin"],
        core_config["password_root"],
    ]
    db_host = core_config["db_host"]
    ssl_ca_path = core_config["ssl_ca_path"]
    cache_host = core_config["cache_host"]
    cache_ssl_ca_path = core_config["cache_ssl_ca_path"]
    ssl_verify_mode = core_config["ssl_verify_mode"]
    mysql_tls_enabled = core_config["mysql_tls_enabled"]

    gateway = get_gateway()

    # Auto-scan project owner's keys
    project_owner = detect_project_owner(project_path)
    if not project_owner:
        error_msg = "Could not detect project owner"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    auto_scanned_keys: List[str] = []
    if project_owner:
        auto_scanned_keys = auto_scan_user_keys(project_owner)
        log(f"Auto-scanned {len(auto_scanned_keys)} keys from {project_owner}")

    if not auto_scanned_keys:
        error_msg = "No SSH keys found to copy (authorized_keys empty). Aborting install."
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    log("hh core: Creating fresh users")
    user_data = []
    admin_tier = 'admin' if 'admin' in HENHOUSE_TIERS else None

    for idx, tier in enumerate(HENHOUSE_TIERS):
        user = f"{project_name}_{tier}"
        password = passwords[idx]
        try:
            useradd_cmd = ['useradd', '-r', '-s', '/bin/bash', '-m', '-d', f'/home/{user}']
            if tier == admin_tier:
                admin_group_name = f"{project_name}_{admin_tier}"
                useradd_cmd.extend(['-g', admin_group_name])
            useradd_cmd.append(user)
            result = subprocess.run(useradd_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, ['useradd'], result.stdout, result.stderr)

            # SSH-only: lock password
            subprocess.run(['passwd', '-l', user], check=True, capture_output=True)
            gateway.files.chmod(f'/home/{user}', 0o755)

            # All users own their own home directories
            gateway.files.chown(f'/home/{user}', user)

            ssh_keys = generate_ssh_keys(user, project_name)

            # Add auto-scanned keys
            if auto_scanned_keys:
                for key in auto_scanned_keys:
                    add_user_key(user, key)

            # Create project-specific config file
            create_user_config_file(
                user,
                project_name,
                password,
                db_user=user,
                host=db_host,
                ssl_ca=ssl_ca_path if mysql_tls_enabled else None,
                cache_host=cache_host,
                cache_ssl_ca=cache_ssl_ca_path if mysql_tls_enabled else None,
                ssl_verify_mode=ssl_verify_mode if mysql_tls_enabled else None,
                mysql_tls_enabled=mysql_tls_enabled
            )

            # Add users to appropriate groups
            deploy_group_name = f"{project_name}_deploy"
            if user == f"{project_name}_{HENHOUSE_TIERS[-1]}":
                # Highest tier user gets both groups
                try:
                    subprocess.run(['usermod', '-a', '-G', f'{project_name},{deploy_group_name}', user], check=True, capture_output=True)
                    log(f"Added {user} to groups {project_name} and {deploy_group_name}")
                except subprocess.CalledProcessError as e:
                    warn(f"Failed to add {user} to groups: {e.stderr.decode()}")
            else:
                # Lower tier users get only deploy group
                try:
                    subprocess.run(['usermod', '-a', '-G', deploy_group_name, user], check=True, capture_output=True)
                    log(f"Added {user} to deploy group {deploy_group_name}")
                except subprocess.CalledProcessError as e:
                    warn(f"Failed to add {user} to deploy group: {e.stderr.decode()}")

            user_data.append({
                "username": user,
                "status": "created",
                "ssh_keys": ssh_keys,
                "home_directory": f"/home/{user}"
            })
            log(f"Created user: {user}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            warn(f"Failed to create user {user}: {error_msg}")
            user_data.append({
                "username": user,
                "status": "failed",
                "error": error_msg
            })
        except Exception as e:
            warn(f"Failed to create user {user}: {str(e)}")
            user_data.append({
                "username": user,
                "status": "failed",
                "error": str(e)
            })

    # Store user_data for manifest writing later
    core_config["user_data"] = user_data
    core_config["project_owner"] = project_owner

    return trace_out({"status": "success", "users_created": len([u for u in user_data if u.get("status") == "created"])})


@register_module_hook('install_25_user_configs', 'User configuration')
def setup_user_configs() -> Dict[str, Any]:
    """Placeholder - user config creation happens in install_20."""
    trace_in()
    log("hh core: User configs already created in install_20")
    return trace_out({"status": "success"})


@register_module_hook('install_35_project_groups', 'Finalize project group memberships')
def setup_project_group() -> Dict[str, Any]:
    """Add users to groups and set ownership."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    project_path = INSTALL_CONFIG["project_path"]
    project_owner = core_config.get("project_owner")

    try:
        log(f"hh core: Setting up project groups: {project_name}")

        deploy_group_name = f"{project_name}_deploy"
        admin_group_name = f"{project_name}_admin"

        # Add current user to all groups
        current_user = os.getenv('USER', 'root')
        try:
            subprocess.run(['usermod', '-a', '-G', f'{project_name},{deploy_group_name},{admin_group_name}', current_user], check=True, capture_output=True)
            log(f"Added {current_user} to groups {project_name}, {deploy_group_name}, and {admin_group_name}")
        except subprocess.CalledProcessError as e:
            warn(f"Failed to add {current_user} to groups: {e.stderr.decode()}")

        # Add project owner to all groups
        if project_owner and project_owner != current_user:
            try:
                subprocess.run(['usermod', '-a', '-G', f'{project_name},{deploy_group_name},{admin_group_name}', project_owner], check=True, capture_output=True)
                log(f"Added project owner {project_owner} to groups {project_name}, {deploy_group_name}, and {admin_group_name}")
            except subprocess.CalledProcessError as e:
                warn(f"Failed to add project owner {project_owner} to groups: {e.stderr.decode()}")

        # Add www-data to deploy and admin groups
        try:
            subprocess.run(['usermod', '-a', '-G', f'{deploy_group_name},{admin_group_name}', 'www-data'], check=True, capture_output=True)
            log(f"Added www-data to groups {deploy_group_name} and {admin_group_name}")
        except subprocess.CalledProcessError as e:
            log(f"Failed to add www-data to groups (may not exist yet): {e.stderr.decode()}")

        # Add root tier user to admin group
        root_tier = HENHOUSE_TIERS[-1]
        root_user = f"{project_name}_{root_tier}"
        try:
            subprocess.run(['usermod', '-a', '-G', admin_group_name, root_user], check=True, capture_output=True)
            log(f"Added {root_user} to group {admin_group_name}")
        except subprocess.CalledProcessError as e:
            warn(f"Failed to add {root_user} to group {admin_group_name}: {e.stderr.decode()}")

        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to setup project groups: {str(e)}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


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


@register_module_hook('install_50_user_env', 'Set up user environments')
def setup_user_environments() -> Dict[str, Any]:
    """Update user paths and set up home directories."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    project_path = INSTALL_CONFIG["project_path"]
    project_owner = core_config.get("project_owner")
    entry_point_script_name = core_config.get("entry_point_script_name", "hen")
    password_root = core_config["password_root"]
    db_host = core_config["db_host"]
    ssl_ca_path = core_config["ssl_ca_path"]
    cache_host = core_config["cache_host"]
    cache_ssl_ca_path = core_config["cache_ssl_ca_path"]
    ssl_verify_mode = core_config["ssl_verify_mode"]
    mysql_tls_enabled = core_config["mysql_tls_enabled"]

    try:
        # Update user paths
        update_user_paths(project_name)

        # Set up human user home directory
        setup_human_user_home(project_name, project_path, entry_point_script_name)

        # Create config file for human user (admin creds)
        if project_owner:
            create_user_config_file(
                project_owner,
                project_name,
                password_root,
                db_user=f"{project_name}_root",
                host=db_host,
                ssl_ca=ssl_ca_path if mysql_tls_enabled else None,
                cache_host=cache_host,
                cache_ssl_ca=cache_ssl_ca_path if mysql_tls_enabled else None,
                ssl_verify_mode=ssl_verify_mode if mysql_tls_enabled else None,
                mysql_tls_enabled=mysql_tls_enabled
            )

        # Set up root user entry point
        setup_root_user_script(project_name, project_path, entry_point_script_name)

        # Create config file for root user (root creds)
        create_user_config_file(
            "root",
            project_name,
            password_root,
            db_user=f"{project_name}_root",
            host=db_host,
            ssl_ca=ssl_ca_path if mysql_tls_enabled else None,
            cache_host=cache_host,
            cache_ssl_ca=cache_ssl_ca_path if mysql_tls_enabled else None,
            ssl_verify_mode=ssl_verify_mode if mysql_tls_enabled else None,
            mysql_tls_enabled=mysql_tls_enabled
        )

        log("hh core: User environments configured")
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


@register_module_hook('install_70_manifest', 'Write manifest of created users')
def write_manifest() -> Dict[str, Any]:
    """Write manifest of created users to config file."""
    trace_in()

    project_name = INSTALL_CONFIG["project_name"]
    cfg_path = INSTALL_CONFIG["config_path"]
    user_data = core_config.get("user_data", [])

    gateway = get_gateway()

    # Build manifest
    manifest: Dict[str, Dict[str, Any]] = {}
    now = _iso_now()
    for user in user_data:
        if user.get("status") == "created":
            uname = user.get("username", "")
            try:
                if gateway.os:
                    info = gateway.os.get_user_by_name(uname)
                    if info and "uid" in info:
                        manifest[uname] = {"uid": str(info["uid"]), "installed_at": now, "removed_at": None}
            except Exception:
                pass

    if manifest:
        try:
            write_manifest_users(cfg_path, manifest)
            log(f"hh core: Wrote manifest for {len(manifest)} users")
            return trace_out({"status": "success", "users_in_manifest": len(manifest)})
        except Exception as e:
            error_msg = f"Failed to write manifest_users: {e}"
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

    return trace_out({"status": "success", "users_in_manifest": 0})


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
