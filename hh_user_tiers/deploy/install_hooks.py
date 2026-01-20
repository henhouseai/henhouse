"""
Tier user system installation hooks.

Handles creation and management of guest, verified, admin, and root tier users.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh_user_tiers.deploy.access import auto_scan_user_keys, generate_ssh_keys, add_user_key
from hh.deploy.user_accounts import create_user_config_file, update_user_paths, detect_project_owner
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import validate_config_value

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

# Module-scoped config storage for tier user settings
tier_config: Dict[str, Any] = {}


@register_module_hook('install_01_template_contribute', 'Contribute tier user template sections')
def contribute_tier_template() -> Dict[str, Any]:
    """Add tier user password sections to template."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    if INSTALL_CONFIG["mode"] != "template":
        return trace_out({"status": "skipped"})

    tier_template = [
        "# ========================================",
        "# Tier User Passwords",
        "# ========================================",
        "# DB user passwords (guest, verified, admin, root)",
        "password_guest = CHANGE_ME",
        "password_verified = CHANGE_ME",
        "password_admin = CHANGE_ME",
        "password_root = CHANGE_ME",
        "",
    ]

    INSTALL_CONFIG["template_lines"].extend(tier_template)
    log(f"hh_user_tiers: Added {len(tier_template)} lines to template")
    return trace_out({"status": "success", "lines_contributed": len(tier_template)})


@register_module_hook('install_05_pre_validate', 'Validate tier user configuration')
def validate_tier_config() -> Dict[str, Any]:
    """Validate tier user passwords from install config file."""
    trace_in()
    global tier_config
    from hh.deploy.install_hooks import INSTALL_CONFIG

    if INSTALL_CONFIG["mode"] != "install":
        return trace_out({"status": "skipped"})

    parsed = INSTALL_CONFIG["parsed_config"]

    # Validate tier user passwords
    for key in ("password_guest", "password_verified", "password_admin", "password_root"):
        try:
            validate_config_value(key, parsed.get(key, ""))
        except ValueError as e:
            error_msg = str(e)
            warn(f"hh_user_tiers: {error_msg}")
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

    # Store validated config in module global
    tier_config["password_guest"] = parsed["password_guest"]
    tier_config["password_verified"] = parsed["password_verified"]
    tier_config["password_admin"] = parsed["password_admin"]
    tier_config["password_root"] = parsed["password_root"]

    # Also store DB config from core
    tier_config["db_host"] = parsed.get("db_host", "localhost")
    tier_config["ssl_ca_path"] = parsed.get("ssl_ca_path", "")
    tier_config["cache_host"] = parsed.get("cache_host", "localhost")
    tier_config["cache_ssl_ca_path"] = parsed.get("cache_ssl_ca_path", "")

    # Parse MySQL TLS enabled setting
    mysql_tls_enabled_str = parsed.get("mysql_tls_enabled", "0").strip()
    try:
        mysql_tls_enabled = int(mysql_tls_enabled_str) != 0
    except ValueError:
        mysql_tls_enabled = False
    tier_config["mysql_tls_enabled"] = mysql_tls_enabled

    # Auto-detect ssl_verify_mode based on db_host
    db_host = tier_config["db_host"]
    ssl_verify_mode = 0 if db_host in ("localhost", "127.0.0.1") else 3
    tier_config["ssl_verify_mode"] = ssl_verify_mode

    log("hh_user_tiers: Tier user configuration validated successfully")
    return trace_out({"status": "success"})


@register_module_hook('install_10_conflict_check', 'Check for existing users and groups')
def check_user_group_conflicts() -> Dict[str, Any]:
    """Check for existing project setup."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    project_name = INSTALL_CONFIG["project_name"]

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
            warn(f"hh_user_tiers: {error_msg}")
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

        log("hh_user_tiers: No conflicts found")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Error checking for conflicts: {str(e)}"
        warn(f"hh_user_tiers: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_15_groups', 'Create core groups')
def create_core_groups() -> Dict[str, Any]:
    """Create core groups that users need to be added to."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    project_name = INSTALL_CONFIG["project_name"]

    try:
        log(f"hh_user_tiers: Setting up core groups: {project_name}")

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
        warn(f"hh_user_tiers: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_20_users', 'Create tier users')
def create_tier_users() -> Dict[str, Any]:
    """Create fresh tier users with SSH keys and config files."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    project_name = INSTALL_CONFIG["project_name"]
    project_path = INSTALL_CONFIG["project_path"]

    passwords = [
        tier_config["password_guest"],
        tier_config["password_verified"],
        tier_config["password_admin"],
        tier_config["password_root"],
    ]
    db_host = tier_config["db_host"]
    ssl_ca_path = tier_config["ssl_ca_path"]
    cache_host = tier_config["cache_host"]
    cache_ssl_ca_path = tier_config["cache_ssl_ca_path"]
    ssl_verify_mode = tier_config["ssl_verify_mode"]
    mysql_tls_enabled = tier_config["mysql_tls_enabled"]

    gateway = get_gateway()

    # Auto-scan project owner's keys
    project_owner = detect_project_owner(project_path)
    if not project_owner:
        error_msg = "Could not detect project owner"
        warn(f"hh_user_tiers: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    auto_scanned_keys: List[str] = []
    if project_owner:
        auto_scanned_keys = auto_scan_user_keys(project_owner)
        log(f"Auto-scanned {len(auto_scanned_keys)} keys from {project_owner}")

    if not auto_scanned_keys:
        error_msg = "No SSH keys found to copy (authorized_keys empty). Aborting install."
        warn(f"hh_user_tiers: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    log("hh_user_tiers: Creating fresh users")
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
    tier_config["user_data"] = user_data
    tier_config["project_owner"] = project_owner

    return trace_out({"status": "success", "users_created": len([u for u in user_data if u.get("status") == "created"])})


@register_module_hook('install_25_user_configs', 'User configuration')
def setup_user_configs() -> Dict[str, Any]:
    """Placeholder - user config creation happens in install_20."""
    trace_in()
    log("hh_user_tiers: User configs already created in install_20")
    return trace_out({"status": "success"})


@register_module_hook('install_35_project_groups', 'Finalize project group memberships')
def setup_project_group() -> Dict[str, Any]:
    """Add users to groups and set ownership."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    project_name = INSTALL_CONFIG["project_name"]
    project_owner = tier_config.get("project_owner")

    try:
        log(f"hh_user_tiers: Setting up project groups: {project_name}")

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
        warn(f"hh_user_tiers: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_50_tier_env', 'Set up tier user environments')
def setup_tier_environments() -> Dict[str, Any]:
    """Update user paths for tier users."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    project_name = INSTALL_CONFIG["project_name"]

    try:
        # Update user paths (adds tier users to sudoers)
        update_user_paths(project_name)

        log("hh_user_tiers: Tier user environments configured")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to setup tier user environments: {str(e)}"
        warn(f"hh_user_tiers: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_70_manifest', 'Write manifest of tier users')
def write_tier_manifest() -> Dict[str, Any]:
    """Write manifest of created tier users to config file."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG
    from hh.deploy.install_helpers_manifest import write_manifest_users
    import datetime

    project_name = INSTALL_CONFIG["project_name"]
    cfg_path = INSTALL_CONFIG["config_path"]
    user_data = tier_config.get("user_data", [])

    gateway = get_gateway()

    # Build manifest
    manifest: Dict[str, Dict[str, Any]] = {}
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
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
            log(f"hh_user_tiers: Wrote manifest for {len(manifest)} users")
            return trace_out({"status": "success", "users_in_manifest": len(manifest)})
        except Exception as e:
            error_msg = f"Failed to write manifest_users: {e}"
            warn(f"hh_user_tiers: {error_msg}")
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

    return trace_out({"status": "success", "users_in_manifest": 0})


@register_module_hook('install_95_render', 'Render tier user summary')
def render_tier_summary() -> Dict[str, Any]:
    """Render tier user installation summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - parser will aggregate from all modules
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
