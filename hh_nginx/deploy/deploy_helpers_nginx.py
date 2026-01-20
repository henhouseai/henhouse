"""
NGINX configuration and deployment helpers for hh_nginx module.

All the helper functions used by the nginx deployment hooks.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error

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


def get_server_ip() -> str:
    """
    Get the first non-localhost IP address from the server's network interfaces.
    Falls back to 127.0.0.1 if no other IP is found.

    Returns:
        IP address string (e.g., "192.168.1.100")
    """
    trace_in()
    try:
        # Get all network interfaces
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    # Extract IP address (format: inet 192.168.1.100/24)
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip_with_cidr = parts[1]
                        ip = ip_with_cidr.split('/')[0]
                        trace_out()
                        return ip
    except Exception as e:
        warn(f"Failed to detect server IP: {e}")

    # Fallback to localhost
    trace_out()
    return "127.0.0.1"


def create_local_decoy(server_ip: str, nginx_sites_available: Path, nginx_sites_enabled: Path) -> bool:
    """Create a decoy server for local deployments to prevent IP-based access from hijacking local sites."""
    trace_in()
    try:
        default_config_path = Path("/etc/nginx/sites-available/default")
        if not default_config_path.exists():
            warn("Default NGINX config not found, cannot create decoy")
            trace_out()
            return False

        # Read the default configuration
        default_config = default_config_path.read_text()

        # Modify listen directives to use specific IP with default_server
        modified_config = default_config
        modified_config = modified_config.replace(
            "listen 80 default_server;",
            f"listen {server_ip}:80 default_server;"
        )
        # Remove the entire IPv6 listen line to prevent conflicts
        import re
        modified_config = re.sub(r'listen \[::\]:80.*;\s*', '', modified_config)

        # Write the decoy configuration
        decoy_config_path = nginx_sites_available / "decoy"
        decoy_config_path.write_text(modified_config)
        log(f"Decoy NGINX config written to: {decoy_config_path}")

        # Create symlink in sites-enabled
        decoy_enabled_path = nginx_sites_enabled / "decoy"
        if decoy_enabled_path.exists():
            decoy_enabled_path.unlink()
        decoy_enabled_path.symlink_to(decoy_config_path)
        log(f"Decoy symlink created: {decoy_enabled_path}")

        trace_out()
        return True

    except Exception as e:
        warn(f"Failed to create local decoy: {e}")
        trace_out()
        return False


def check_nginx_status() -> Dict[str, Any]:
    """Check current Nginx status."""
    trace_in()
    try:
        status_result = subprocess.run(['systemctl', 'is-active', 'nginx'],
                                       capture_output=True, text=True)
        is_active = status_result.returncode == 0 and status_result.stdout.strip() == 'active'

        # Get enabled sites
        enabled_sites = []
        sites_enabled_dir = Path('/etc/nginx/sites-enabled')
        if sites_enabled_dir.exists():
            for site_file in sites_enabled_dir.iterdir():
                if site_file.is_symlink() or not site_file.suffix:
                    enabled_sites.append(site_file.name)

        result = {
            'is_active': is_active,
            'enabled_sites': enabled_sites
        }
        log(f"Nginx status: active={is_active}, sites={len(enabled_sites)}")
        trace_out()
        return result

    except Exception as e:
        warn(f"Failed to check Nginx status: {e}")
        trace_out()
        return {'is_active': False, 'enabled_sites': []}


# Config generation functions (moved from nginx_flask)

def create_nginx_ssl_config_local(domain: str, project_name: str, local_allow_block: str, server_ip: str, certificate_path: str) -> str:
    """Generate Nginx SSL configuration with client IP access control for local deployments."""
    trace_in()
    try:
        from hh.deploy.install_helpers_config import load_install_config
        guest_password = None
        webroot_dir = "/var/www/html"
        try:
            install_config = load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass

        from .http.nginx_whitelist import generate_nginx_static_locations
        from .http.nginx_config_helpers import (
            get_security_headers_ssl, get_block_hidden_files,
            get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
            get_server_configs, detect_flask_ports, generate_http_redirect_block,
            get_client_ip_access_control
        )
        from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        try:
            from hh.deploy.deploy_utils import load_whitelist_with_extensions
            MISC_WHITELIST = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')
            from pathlib import Path as _P
            misc_blocks = []
            for item in MISC_WHITELIST:
                filename = _P(item).name
                if not filename:
                    continue
                misc_blocks.append(f"""    location /{filename} {{
        alias /srv/{project_name}/site/{filename};
        expires off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}""")
            if misc_blocks:
                static_locations = f"{static_locations}\n\n" + "\n\n".join(misc_blocks)
        except Exception:
            pass

        config_lines = [
            "# Local-only HTTPS configuration (client IP access control, prevents external access)",
            "",
        ]

        all_domains = [domain, f'www.{domain}', f'admin.{domain}', f'panel.{domain}']
        config_lines.append("# HTTP to HTTPS redirect (with client IP access control)")
        config_lines.append("server {")
        config_lines.append(f"    listen {server_ip}:80;")
        config_lines.append(f"    server_name {' '.join(all_domains)};")
        config_lines.append("")
        config_lines.extend(get_client_ip_access_control(local_allow_block))
        config_lines.append("    location / {")
        config_lines.append("        return 301 https://$host$request_uri;")
        config_lines.append("    }")
        config_lines.append("}")
        config_lines.append("")

        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        servers = get_server_configs(domain, project_name)

        for server in servers:
            block_lines = _generate_local_https_server_block(
                server['names'], server['port'], static_locations, certificate_path,
                server['label'], project_name=project_name, media_port=media_port,
                server_ip=server_ip, local_allow_block=local_allow_block,
                guest_password=guest_password, webroot_dir=webroot_dir
            )
            config_lines.extend(block_lines)

        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx SSL config for local deployment: {e}")
        trace_out()
        return ""


def _generate_local_https_server_block(server_names: List[str], port: int, static_locations: str,
                                      certificate_path: str, label: str = "",
                                      project_name: str = "henhouse", media_port: Optional[int] = None,
                                      server_ip: str = "127.0.0.1",
                                      local_allow_block: str = "192.168.1.0/24,10.0.0.0/8",
                                      guest_password: Optional[str] = None, webroot_dir: str = "/var/www/html") -> List[str]:
    """Generate an HTTPS server block with client IP access control for local deployments."""
    from .http.nginx_config_helpers import (
        get_security_headers_ssl, get_block_hidden_files,
        get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
        get_client_ip_access_control, detect_flask_ports
    )
    from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

    lines = []
    if media_port is None:
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)

    if label:
        lines.append(f"# {label} (local deployment with client IP access control)")

    lines.append("server {")
    lines.append(f"    listen {server_ip}:443 ssl http2;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    lines.extend(get_client_ip_access_control(local_allow_block))
    lines.append("    ssl_certificate {}/fullchain.pem;".format(certificate_path))
    lines.append("    ssl_certificate_key {}/privkey.pem;".format(certificate_path))
    lines.append("")
    lines.extend(get_security_headers_ssl())
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        if line.strip():
            lines.append(f"    {line}")
    lines.append("")
    lines.extend(get_block_hidden_files(webroot_dir))

    ports = detect_flask_ports(project_name)
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break

    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier, guest_password))

    lines.extend(get_media_server_proxy_block(media_port))
    lines.extend(get_flask_proxy_block(port))
    lines.append("}")
    lines.append("")
    return lines


def create_nginx_config_local(domain: str, project_name: str, local_allow_block: str, server_ip: str) -> str:
    """Generate Nginx HTTP-only configuration with client IP access control for local deployments."""
    trace_in()
    try:
        from hh.deploy.install_helpers_config import load_install_config
        guest_password = None
        webroot_dir = "/var/www/html"
        try:
            install_config = load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass

        from .http.nginx_whitelist import generate_nginx_static_locations
        from .http.nginx_config_helpers import (
            get_security_headers, get_block_hidden_files,
            get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
            get_server_configs, detect_flask_ports
        )

        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        try:
            from hh.deploy.deploy_utils import load_whitelist_with_extensions
            MISC_WHITELIST = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')
            from pathlib import Path as _P
            misc_blocks = []
            for item in MISC_WHITELIST:
                filename = _P(item).name
                if not filename:
                    continue
                misc_blocks.append(f"""    location /{filename} {{
        alias /srv/{project_name}/site/{filename};
        expires off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}""")
            if misc_blocks:
                static_locations = f"{static_locations}\n\n" + "\n\n".join(misc_blocks)
        except Exception:
            pass

        config_lines = [
            "# Local-only HTTP configuration (client IP access control, intranet access only)",
            "",
        ]

        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        servers = get_server_configs(domain, project_name)

        for server in servers:
            block_lines = _generate_local_http_server_block(
                server['names'], server['port'], static_locations, server['label'],
                project_name=project_name, media_port=media_port, server_ip=server_ip,
                local_allow_block=local_allow_block, guest_password=guest_password,
                webroot_dir=webroot_dir
            )
            config_lines.extend(block_lines)

        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx HTTP config for local deployment: {e}")
        trace_out()
        return ""


def _generate_local_http_server_block(server_names: List[str], port: int, static_locations: str,
                                      label: str = "", project_name: str = "henhouse",
                                      media_port: Optional[int] = None, server_ip: str = "127.0.0.1",
                                      local_allow_block: str = "192.168.1.0/24,10.0.0.0/8",
                                      guest_password: Optional[str] = None, webroot_dir: str = "/var/www/html") -> List[str]:
    """Generate an HTTP server block with client IP access control for local deployments."""
    from .http.nginx_config_helpers import (
        get_security_headers, get_block_hidden_files,
        get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
        get_client_ip_access_control, detect_flask_ports
    )
    from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

    lines = []
    if media_port is None:
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)

    if label:
        lines.append(f"# {label} (local deployment with client IP access control)")

    lines.append("server {")
    lines.append(f"    listen {server_ip}:80;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    lines.extend(get_client_ip_access_control(local_allow_block))
    lines.extend(get_security_headers())
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    lines.extend(get_block_hidden_files(webroot_dir))

    ports = detect_flask_ports(project_name)
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break

    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier, guest_password))

    lines.extend(get_media_server_proxy_block(media_port))
    lines.extend(get_flask_proxy_block(port))
    lines.append("}")
    lines.append("")
    return lines


def create_nginx_ssl_config(domain: str, project_name: str, certificate_path: Optional[str] = None) -> str:
    """Generate Nginx SSL configuration for the domain and its subdomains (public deployment)."""
    trace_in()
    try:
        if not certificate_path:
            certificate_path = f"/etc/letsencrypt/live/{domain}"

        from hh.deploy.install_helpers_config import load_install_config
        guest_password = None
        webroot_dir = "/var/www/html"
        try:
            install_config = load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass

        from .http.nginx_whitelist import generate_nginx_static_locations
        from .http.nginx_config_helpers import (
            generate_https_server_block, detect_flask_ports,
            generate_http_redirect_block, get_server_configs
        )

        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        try:
            from hh.deploy.deploy_utils import load_whitelist_with_extensions
            MISC_WHITELIST = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')
            from pathlib import Path as _P
            misc_blocks = []
            for item in MISC_WHITELIST:
                filename = _P(item).name
                if not filename:
                    continue
                misc_blocks.append(f"""    location /{filename} {{
        alias /srv/{project_name}/site/{filename};
        expires off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}""")
            if misc_blocks:
                static_locations = f"{static_locations}\n\n" + "\n\n".join(misc_blocks)
        except Exception:
            pass

        config_lines = [
            "# Stage 2: HTTPS configuration (after SSL certificates)",
            "",
        ]

        all_domains = [domain, f'www.{domain}', f'admin.{domain}', f'panel.{domain}']
        config_lines.extend(generate_http_redirect_block(all_domains, webroot_dir))

        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        servers = get_server_configs(domain, project_name)

        main_server = servers[0]
        block_lines = generate_https_server_block(
            main_server['names'], main_server['port'], static_locations, certificate_path,
            main_server['label'], project_name=project_name, media_port=media_port,
            guest_password=guest_password, webroot_dir=webroot_dir
        )
        config_lines.extend(block_lines)

        for server in servers[1:]:
            block_lines = generate_https_server_block(
                server['names'], server['port'], static_locations, certificate_path,
                server['label'], project_name=project_name, media_port=media_port,
                guest_password=guest_password, webroot_dir=webroot_dir
            )
            config_lines.extend(block_lines)

        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx SSL config: {e}")
        trace_out()
        return ""


def create_nginx_config(domain: str, project_name: str) -> str:
    """Generate Nginx configuration for the domain and its subdomains (HTTP only - public deployment)."""
    trace_in()
    try:
        from hh.deploy.install_helpers_config import load_install_config
        webroot_dir = "/var/www/html"
        try:
            install_config = load_install_config(project_name)
            if install_config:
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass

        from .http.nginx_whitelist import generate_nginx_static_locations
        from .http.nginx_config_helpers import generate_server_block, get_server_configs, detect_flask_ports

        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        try:
            from hh.deploy.deploy_utils import load_whitelist_with_extensions
            MISC_WHITELIST = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')
            from pathlib import Path as _P
            misc_blocks = []
            for item in MISC_WHITELIST:
                filename = _P(item).name
                if not filename:
                    continue
                misc_blocks.append(f"""    location /{filename} {{
        alias /srv/{project_name}/site/{filename};
        expires off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}""")
            if misc_blocks:
                static_locations = f"{static_locations}\n\n" + "\n\n".join(misc_blocks)
        except Exception:
            pass

        config_lines = [
            "# Stage 1: HTTP-only configuration (Flask + static files only)",
            "",
        ]

        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        servers = get_server_configs(domain, project_name)

        for server in servers:
            block_lines = generate_server_block(
                server['names'], server['port'], static_locations, server['label'],
                project_name=project_name, media_port=media_port, webroot_dir=webroot_dir
            )
            config_lines.extend(block_lines)

        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx config: {e}")
        trace_out()
        return ""
