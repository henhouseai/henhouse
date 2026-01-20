"""
NGINX module installation hooks.

Handles NGINX-specific configuration, domain setup, SSL settings, and htpasswd files.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

# Module-scoped config storage
nginx_config: Dict[str, Any] = {}


@register_module_hook('install_01_template_contribute', 'Contribute NGINX template sections')
def contribute_nginx_template() -> Dict[str, Any]:
    """Contribute NGINX-specific configuration to install template."""
    trace_in()
    from hh.deploy.install_hooks import INSTALL_CONFIG

    if INSTALL_CONFIG["mode"] != "template":
        return trace_out({"status": "skipped"})

    nginx_template = [
        "# HTTP Basic Auth passwords",
        "# Leave htaccess_guest_password blank for public access, set password for private site",
        "htaccess_guest_password = ",
        "htaccess_admin_password = CHANGE_ME",
        "htaccess_panel_password = CHANGE_ME",
        "",
        "# ========================================",
        "# HTTP/NGINX Deployment Settings",
        "# ========================================",
        "# Domain name for web deployment",
        "# For local network deployment (default - configure /etc/hosts on developer box):",
        "domain = example.local",
        "# For public deployment with domain name:",
        "# domain = example.tld",
        "# For local network deployment (IP address):",
        "# domain = 192.168.1.100",
        "",
        "# SSL/TLS Configuration",
        "# SSL enabled (1 = enabled, 0 = disabled)",
        "# For localhost deployment (HTTP-only recommended for initial testing):",
        "ssl_enabled = 0",
        "# For public deployment (HTTPS recommended):",
        "# ssl_enabled = 1",
        "",
        "# SSL Certificate Directories",
        "# Let's Encrypt certificate directory (for public deployments)",
        "ssl_cert_dir_letsencrypt = /etc/letsencrypt/live",
        "# Self-signed certificate directory (for local/testing deployments)",
        "ssl_cert_dir_self_signed = /etc/nginx/ssl",
        "",
        "# Local Deployment Client IP Access Control",
        "# CIDR notation for allowed client IP ranges (comma-separated for multiple ranges)",
        "# Only used for local deployments (.local domains, localhost, or private IP addresses)",
        "# This restricts NGINX to only accept connections from matching client IPs, preventing external access",
        "# Default allows common private network ranges: 192.168.1.0/24 (class C) and 10.0.0.0/8 (class A)",
        "local_allow_block = 192.168.1.0/24,10.0.0.0/8",
        "",
        "# NGINX Configuration Directories",
        "# NGINX sites-available directory (where config files are stored)",
        "nginx_sites_available = /etc/nginx/sites-available",
        "# NGINX sites-enabled directory (where symlinks to enabled sites are stored)",
        "nginx_sites_enabled = /etc/nginx/sites-enabled",
        "# Webroot directory for Let's Encrypt ACME challenges",
        "webroot_dir = /var/www/html",
        "# HTTP Basic Auth htpasswd directory (where .htpasswd files are stored)",
        "htpasswd_dir = /var/www",
        "",
    ]

    INSTALL_CONFIG["template_lines"].extend(nginx_template)
    log(f"hh_nginx: Added {len(nginx_template)} lines to template")
    return trace_out({"status": "success", "lines_contributed": len(nginx_template)})


@register_module_hook('install_05_pre_validate', 'Validate NGINX configuration')
def validate_nginx_config() -> Dict[str, Any]:
    """Validate NGINX-specific configuration."""
    trace_in()
    global nginx_config
    from hh.deploy.install_hooks import INSTALL_CONFIG
    from hh.deploy.install_helpers_config import validate_config_value

    if INSTALL_CONFIG["mode"] != "install":
        return trace_out({"status": "skipped"})

    parsed = INSTALL_CONFIG["parsed_config"]

    # Validate domain
    domain = parsed.get("domain", "").strip()
    if not domain or "example.com" in domain.lower():
        error_msg = "domain must be set to a real value"
        warn(f"hh_nginx: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    # Validate ssl_enabled
    ssl_enabled_str = parsed.get("ssl_enabled", "0").strip()
    ssl_enabled = ssl_enabled_str.lower() in ("true", "1", "yes")

    # Validate htpasswd passwords
    htaccess_admin = parsed.get("htaccess_admin_password", "").strip()
    htaccess_panel = parsed.get("htaccess_panel_password", "").strip()
    htaccess_human = parsed.get("htaccess_human_password", "").strip()

    try:
        validate_config_value("htaccess_admin_password", htaccess_admin)
    except ValueError as e:
        error_msg = str(e)
        warn(f"hh_nginx: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        validate_config_value("htaccess_panel_password", htaccess_panel)
    except ValueError as e:
        error_msg = str(e)
        warn(f"hh_nginx: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        validate_config_value("htaccess_human_password", htaccess_human)
    except ValueError as e:
        error_msg = str(e)
        warn(f"hh_nginx: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    nginx_config["domain"] = domain
    nginx_config["ssl_enabled"] = ssl_enabled
    nginx_config["htaccess_guest_password"] = parsed.get("htaccess_guest_password", "").strip()
    nginx_config["htaccess_admin_password"] = htaccess_admin
    nginx_config["htaccess_panel_password"] = htaccess_panel
    nginx_config["htaccess_human_password"] = htaccess_human
    nginx_config["htpasswd_dir"] = parsed.get("htpasswd_dir", "/var/www").strip()

    log(f"hh_nginx: Validated domain={domain}, ssl_enabled={ssl_enabled}")
    return trace_out({"status": "success", "domain": domain, "ssl_enabled": ssl_enabled})


@register_module_hook('install_30_htpasswd', 'Create HTTP Basic Auth files')
def create_htpasswd_files() -> Dict[str, Any]:
    """Create .htpasswd files for HTTP Basic Authentication."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context
    from hh.deploy.user_accounts import detect_project_owner

    project_name, project_path = detect_project_context()
    if not project_name:
        return trace_out({"status": "error", "error": "Could not detect project name"})

    project_owner = detect_project_owner(project_path)

    # Check if htpasswd command exists
    htpasswd_path = shutil.which('htpasswd')
    if not htpasswd_path:
        error_msg = "htpasswd command not found. Install apache2-utils: sudo apt install apache2-utils"
        warn(f"hh_nginx: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    htpasswd_dir = nginx_config.get("htpasswd_dir", "/var/www")
    guest_password = nginx_config.get("htaccess_guest_password", "")
    admin_password = nginx_config.get("htaccess_admin_password", "")
    panel_password = nginx_config.get("htaccess_panel_password", "")
    human_password = nginx_config.get("htaccess_human_password", "")

    files_created = []

    try:
        # Guest tier (only if password provided)
        if guest_password:
            guest_idx = HENHOUSE_TIERS.index('guest') if 'guest' in HENHOUSE_TIERS else None
            if guest_idx is not None:
                guest_tier = HENHOUSE_TIERS[guest_idx]
                guest_user = f"{project_name}_{guest_tier}"
                htpasswd_file = f"{htpasswd_dir}/.htpasswd_{guest_tier}"

                file_exists = Path(htpasswd_file).exists()
                cmd = ['htpasswd', '-b']
                if not file_exists:
                    cmd.append('-c')
                cmd.extend([htpasswd_file, guest_user, guest_password])

                subprocess.run(cmd, check=True, capture_output=True)
                files_created.append(htpasswd_file)
                log(f"hh_nginx: Created {htpasswd_file}")

        # Admin tier
        admin_idx = HENHOUSE_TIERS.index('admin') if 'admin' in HENHOUSE_TIERS else None
        if admin_idx is not None:
            admin_tier = HENHOUSE_TIERS[admin_idx]
            admin_user = f"{project_name}_{admin_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_{admin_tier}"

            file_exists = Path(htpasswd_file).exists()
            cmd = ['htpasswd', '-b']
            if not file_exists:
                cmd.append('-c')
            cmd.extend([htpasswd_file, admin_user, admin_password])

            subprocess.run(cmd, check=True, capture_output=True)
            files_created.append(htpasswd_file)
            log(f"hh_nginx: Created {htpasswd_file}")

        # Panel tier (root)
        root_idx = HENHOUSE_TIERS.index('root') if 'root' in HENHOUSE_TIERS else None
        if root_idx is not None:
            root_tier = HENHOUSE_TIERS[root_idx]
            root_user = f"{project_name}_{root_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_panel"

            file_exists = Path(htpasswd_file).exists()
            cmd = ['htpasswd', '-b']
            if not file_exists:
                cmd.append('-c')
            cmd.extend([htpasswd_file, root_user, panel_password])

            subprocess.run(cmd, check=True, capture_output=True)
            files_created.append(htpasswd_file)
            log(f"hh_nginx: Created {htpasswd_file}")

        # Human user
        if project_owner and human_password:
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_human"

            file_exists = Path(htpasswd_file).exists()
            cmd = ['htpasswd', '-b']
            if not file_exists:
                cmd.append('-c')
            cmd.extend([htpasswd_file, project_owner, human_password])

            subprocess.run(cmd, check=True, capture_output=True)
            files_created.append(htpasswd_file)
            log(f"hh_nginx: Created {htpasswd_file}")

        return trace_out({
            "status": "success",
            "files_created": files_created,
            "count": len(files_created)
        })

    except Exception as e:
        error_msg = f"Failed to create htpasswd files: {str(e)}"
        warn(f"hh_nginx: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_95_render', 'Render NGINX summary')
def render_nginx_summary() -> Dict[str, Any]:
    """Render NGINX configuration summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - can add NGINX-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
