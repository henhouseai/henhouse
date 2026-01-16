"""
NGINX configuration and deployment helpers.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

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

try:
    _initialize_debug()
except:
    pass



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
        # Change: listen 80 default_server; -> listen {server_ip}:80 default_server;
        # Remove IPv6 listen directive entirely - decoy only handles IPv4
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

        # Test and reload NGINX to activate the decoy
        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if test_result.returncode != 0:
            warn(f"Nginx configuration test failed after decoy creation: {test_result.stderr}")
            trace_out()
            return False
        else:
            log("Nginx configuration test passed after decoy creation")
            # Reload Nginx
            reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
            if reload_result.returncode != 0:
                restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                if restart_result.returncode != 0:
                    warn(f"Failed to reload/restart Nginx after decoy creation: {restart_result.stderr}")
                    trace_out()
                    return False
                else:
                    log("Nginx restarted successfully after decoy creation")
            else:
                log("Nginx reloaded successfully after decoy creation")

        trace_out()
        return True

    except Exception as e:
        warn(f"Failed to create local decoy: {e}")
        trace_out()
        return False

def create_nginx_ssl_config_local(domain: str, project_name: str, local_allow_block: str, server_ip: str, certificate_path: str) -> str:
    """Generate Nginx SSL configuration with client IP access control for local deployments."""
    trace_in()
    try:
        # Load guest password and webroot_dir from install config
        from hh.deploy.users.install import _load_install_config
        guest_password = None
        webroot_dir = "/var/www/html"
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass  # If config can't be loaded, use defaults
        
        # Import helpers
        from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
        from hh.deploy.http.nginx_config_helpers import (
            get_security_headers_ssl, get_block_hidden_files,
            get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
            get_server_configs, detect_flask_ports, generate_http_redirect_block,
            get_client_ip_access_control
        )
        from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
        
        # Get static locations
        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        # Add root-level mappings for files in MISC_WHITELIST
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
        
        # Add HTTP to HTTPS redirect for all domains (with client IP access control)
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
        
        # Detect media port
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        
        # Get server configurations
        servers = get_server_configs(domain, project_name)
        
        # Generate HTTPS blocks for each server (with client IP access control)
        for server in servers:
            block_lines = _generate_local_https_server_block(
                server['names'],
                server['port'],
                static_locations,
                certificate_path,
                server['label'],
                rate_limit="general",  # Not used anymore, but kept for function signature compatibility
                project_name=project_name,
                media_port=media_port,
                server_ip=server_ip,
                local_allow_block=local_allow_block,
                guest_password=guest_password,
                webroot_dir=webroot_dir
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
                                      certificate_path: str, label: str = "", rate_limit: str = "general",  # rate_limit not used
                                      project_name: str = "henhouse", media_port: Optional[int] = None,
                                      server_ip: str = "127.0.0.1",
                                      local_allow_block: str = "192.168.1.0/24,10.0.0.0/8",
                                      guest_password: Optional[str] = None, webroot_dir: str = "/var/www/html") -> List[str]:
    """Generate an HTTPS server block with client IP access control for local deployments."""
    from hh.deploy.http.nginx_config_helpers import (
        get_security_headers_ssl, get_block_hidden_files,
        get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
        get_client_ip_access_control
    )
    from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
    
    lines = []
    
    # Detect media port if not provided
    if media_port is None:
        from hh.deploy.http.nginx_config_helpers import detect_flask_ports
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
    
    # Add label comment if provided
    if label:
        lines.append(f"# {label} (local deployment with client IP access control)")
    
    lines.append("server {")
    lines.append(f"    listen {server_ip}:443 ssl http2;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    
    # Add client IP access control
    lines.extend(get_client_ip_access_control(local_allow_block))
    
    # Add SSL certificates
    lines.append("    ssl_certificate {}/fullchain.pem;".format(certificate_path))
    lines.append("    ssl_certificate_key {}/privkey.pem;".format(certificate_path))
    lines.append("")
    
    # Add security headers (includes HSTS)
    lines.extend(get_security_headers_ssl())
    
    # Rate limiting removed - no zones needed
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        if line.strip():  # Skip empty lines
            lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking (but allow .well-known for Let's Encrypt)
    lines.extend(get_block_hidden_files(webroot_dir))
    
    # Add authentication for guest/admin/panel subdomains
    from hh.deploy.http.nginx_config_helpers import detect_flask_ports
    ports = detect_flask_ports(project_name)
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier, guest_password))
    
    # Add media server proxy
    lines.extend(get_media_server_proxy_block(media_port))
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

def create_nginx_config_local(domain: str, project_name: str, local_allow_block: str, server_ip: str) -> str:
    """Generate Nginx HTTP-only configuration with client IP access control for local deployments."""
    trace_in()
    try:
        # Load guest password and webroot_dir from install config
        from hh.deploy.users.install import _load_install_config
        guest_password = None
        webroot_dir = "/var/www/html"
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass  # If config can't be loaded, use defaults
        
        # Import helpers
        from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
        from hh.deploy.http.nginx_config_helpers import (
            get_security_headers, get_block_hidden_files,
            get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
            get_server_configs, detect_flask_ports
        )
        
        # Get static locations
        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        # Add root-level mappings for files in MISC_WHITELIST
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
            "# Generated by henhouse deploy-http-local system",
            "",
        ]
        
        # Detect media port
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        
        # Get server configurations
        servers = get_server_configs(domain, project_name)
        
        # Generate HTTP blocks for each server (with client IP access control)
        for server in servers:
            block_lines = _generate_local_http_server_block(
                server['names'],
                server['port'],
                static_locations,
                server['label'],
                project_name=project_name,
                media_port=media_port,
                server_ip=server_ip,
                local_allow_block=local_allow_block,
                guest_password=guest_password,
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
    from hh.deploy.http.nginx_config_helpers import (
        get_security_headers, get_block_hidden_files,
        get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
        get_client_ip_access_control
    )
    from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
    
    lines = []
    
    # Detect media port if not provided
    if media_port is None:
        from hh.deploy.http.nginx_config_helpers import detect_flask_ports
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
    
    # Add label comment if provided
    if label:
        lines.append(f"# {label} (local deployment with client IP access control)")
    
    lines.append("server {")
    lines.append(f"    listen {server_ip}:80;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    
    # Add client IP access control
    lines.extend(get_client_ip_access_control(local_allow_block))
    
    # Add security headers
    lines.extend(get_security_headers())
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking
    lines.extend(get_block_hidden_files(webroot_dir))
    
    # Add authentication for admin/panel subdomains
    from hh.deploy.http.nginx_config_helpers import detect_flask_ports
    ports = detect_flask_ports(project_name)
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier, guest_password))
    
    # Add media server proxy
    lines.extend(get_media_server_proxy_block(media_port))
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

def create_nginx_ssl_config(domain: str, project_name: str, certificate_path: Optional[str] = None) -> str:
    """Generate Nginx SSL configuration for the domain and its subdomains (public deployment)."""
    trace_in()
    try:
        # Default certificate path if not specified
        if not certificate_path:
            certificate_path = f"/etc/letsencrypt/live/{domain}"
        
        # Load guest password and webroot_dir from install config
        from hh.deploy.users.install import _load_install_config
        guest_password = None
        webroot_dir = "/var/www/html"
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass  # If config can't be loaded, use defaults
        
        # Import helpers
        from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
        from hh.deploy.http.nginx_config_helpers import (
            generate_https_server_block, detect_flask_ports, 
            generate_http_redirect_block, get_server_configs
        )
        
        # Get static locations
        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        # Add root-level mappings for files in MISC_WHITELIST
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
        
        # Add HTTP to HTTPS redirect for all domains
        all_domains = [domain, f'www.{domain}', f'admin.{domain}', f'panel.{domain}']
        config_lines.extend(generate_http_redirect_block(all_domains, webroot_dir))
        
        # Detect media port
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        
        # Get server configurations
        servers = get_server_configs(domain, project_name)
        
        # Generate HTTPS block for main site (guest tier)
        main_server = servers[0]
        block_lines = generate_https_server_block(
            main_server['names'],
            main_server['port'],
            static_locations,
            certificate_path,
            main_server['label'],
            project_name=project_name,
            media_port=media_port,
            guest_password=guest_password,
            webroot_dir=webroot_dir
        )
        config_lines.extend(block_lines)
        
        # Generate separate HTTPS blocks for admin and panel
        for server in servers[1:]:  # Skip main site (index 0)
            block_lines = generate_https_server_block(
                server['names'],
                server['port'],
                static_locations,
                certificate_path,
                server['label'],
                project_name=project_name,
                media_port=media_port,
                guest_password=guest_password,
                webroot_dir=webroot_dir
            )
            config_lines.extend(block_lines)
        
        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx SSL config: {e}")
        trace_out()
        return ""

def install_nginx_ssl_config(domain: str, project_name: str, certificate_path: Optional[str] = None, nginx_sites_available: Optional[Path] = None, nginx_sites_enabled: Optional[Path] = None) -> bool:
    """Create Nginx SSL configuration file and enable site."""
    trace_in()
    try:
        # Load nginx paths from config if not provided
        if nginx_sites_available is None or nginx_sites_enabled is None:
            from hh.deploy.users.install import _load_install_config
            install_config = _load_install_config(project_name)
            if install_config:
                sec = install_config
                nginx_sites_available_str = sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip()
                nginx_sites_available = Path(nginx_sites_available_str)
                nginx_sites_enabled_str = sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
                nginx_sites_enabled = Path(nginx_sites_enabled_str)
            else:
                nginx_sites_available = Path("/etc/nginx/sites-available")
                nginx_sites_enabled = Path("/etc/nginx/sites-enabled")
        
        # Generate configuration
        config_content = create_nginx_ssl_config(domain, project_name, certificate_path)
        if not config_content:
            warn("Failed to generate SSL configuration")
            trace_out()
            return False
        
        # Write to sites-available (overwrites existing HTTP config)
        config_file = nginx_sites_available / domain
        config_file.write_text(config_content)
        log(f"Nginx SSL config written to: {config_file}")
        
        # Ensure symlink exists in sites-enabled
        enabled_file = nginx_sites_enabled / domain
        if not enabled_file.exists():
            enabled_file.symlink_to(config_file)
            log(f"Symlink created: {enabled_file}")
        else:
            log(f"Symlink already exists: {enabled_file}")
        
        # Test Nginx configuration
        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if test_result.returncode != 0:
            warn(f"Nginx configuration test failed: {test_result.stderr}")
            trace_out()
            return False
        
        log("Nginx SSL configuration test passed")
        
        # Reload Nginx
        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
        if reload_result.returncode != 0:
            # Try restart instead
            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
            if restart_result.returncode != 0:
                warn(f"Failed to reload/restart Nginx: {restart_result.stderr}")
                trace_out()
                return False
            log("Nginx restarted successfully")
        else:
            log("Nginx reloaded successfully")
        
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Failed to install Nginx SSL configuration: {e}")
        trace_out()
        return False

def create_nginx_config(domain: str, project_name: str) -> str:
    """Generate Nginx configuration for the domain and its subdomains (HTTP only - public deployment)."""
    trace_in()
    try:
        # Load webroot_dir from install config
        from hh.deploy.users.install import _load_install_config
        webroot_dir = "/var/www/html"
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                webroot_dir = install_config.get("webroot_dir", "/var/www/html").strip()
        except Exception:
            pass  # If config can't be loaded, use default
        
        # Import helpers
        from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
        from hh.deploy.http.nginx_config_helpers import generate_server_block, get_server_configs, detect_flask_ports
        
        # Get static locations and summary
        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result

        # Add root-level mappings for files in MISC_WHITELIST
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
        
        # Build config using helper functions
        config_lines = [
            "# Stage 1: HTTP-only configuration (Flask + static files only)",
            "",
        ]
        
        # Detect media port
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        
        # Generate server blocks using helper
        servers = get_server_configs(domain, project_name)
        for server in servers:
            block_lines = generate_server_block(
                server['names'], 
                server['port'], 
                static_locations,
                server['label'],
                project_name=project_name,
                media_port=media_port,
                webroot_dir=webroot_dir
            )
            config_lines.extend(block_lines)
        
        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx config: {e}")
        trace_out()
        return ""

def install_nginx_config(domain: str, project_name: str, nginx_sites_available: Optional[Path] = None, nginx_sites_enabled: Optional[Path] = None) -> bool:
    """Create Nginx configuration file and enable site."""
    trace_in()
    try:
        # Load nginx paths from config if not provided
        if nginx_sites_available is None or nginx_sites_enabled is None:
            from hh.deploy.users.install import _load_install_config
            install_config = _load_install_config(project_name)
            if install_config:
                sec = install_config
                nginx_sites_available_str = sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip()
                nginx_sites_available = Path(nginx_sites_available_str)
                nginx_sites_enabled_str = sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
                nginx_sites_enabled = Path(nginx_sites_enabled_str)
            else:
                nginx_sites_available = Path("/etc/nginx/sites-available")
                nginx_sites_enabled = Path("/etc/nginx/sites-enabled")
        
        # Generate configuration
        config_content = create_nginx_config(domain, project_name)
        if not config_content:
            warn("Failed to generate configuration")
            trace_out()
            return False
        
        # Write to sites-available
        config_file = nginx_sites_available / domain
        config_file.write_text(config_content)
        log(f"Nginx config written to: {config_file}")
        
        # Create symlink to sites-enabled
        enabled_file = nginx_sites_enabled / domain
        if not enabled_file.exists():
            enabled_file.symlink_to(config_file)
            log(f"Symlink created: {enabled_file}")
        else:
            log(f"Symlink already exists: {enabled_file}")
        
        # Test Nginx configuration
        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if test_result.returncode != 0:
            warn(f"Nginx configuration test failed: {test_result.stderr}")
            # Clean up bad config
            enabled_file.unlink()
            config_file.unlink()
            trace_out()
            return False
        
        log("Nginx configuration test passed")
        
        # Reload Nginx
        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
        if reload_result.returncode != 0:
            # Try restart instead
            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
            if restart_result.returncode != 0:
                warn(f"Failed to reload/restart Nginx: {restart_result.stderr}")
                trace_out()
                return False
            log("Nginx restarted successfully")
        else:
            log("Nginx reloaded successfully")
        
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Failed to install Nginx configuration: {e}")
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


def deploy_nginx_and_ssl_helper() -> Dict[str, Any]:
    """Deploy NGINX configuration and SSL certificates."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context
    from hh.gateway.error.error_store import is_error

    project_name, current_path = detect_project_context()
    if not project_name:
        warn("nginx_flask helper: Could not detect project name")
        trace_out()
        return {"status": "error", "error": "Could not detect project name"}

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()

    # Get deployment parameters from install config
    from hh.deploy.users.install import _install_config_path
    import configparser
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"nginx_flask helper: Install config not found: {cfg_path}")
        trace_out()
        return {"status": "error", "error": f"Install config not found: {cfg_path}"}

    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"nginx_flask helper: Missing [install] section in {cfg_path}")
        trace_out()
        return {"status": "error", "error": "Missing [install] section in config"}

    sec = parser["install"]
    domain = sec.get("domain", "").strip()
    if not domain:
        warn("nginx_flask helper: No domain configured")
        trace_out()
        return {"status": "error", "error": "No domain configured"}

    ssl_enabled = sec.get("ssl_enabled", "").strip().lower() in ("true", "1", "yes")
    ssl_cert_dir_self_signed = Path("/etc/ssl/self-signed")
    ssl_cert_dir_letsencrypt = Path("/etc/letsencrypt/live")
    nginx_sites_available = Path("/etc/nginx/sites-available")
    nginx_sites_enabled = Path("/etc/nginx/sites-enabled")

    # Detect if local deployment
    is_local = (domain.startswith('192.168.') or
                domain.startswith('10.') or
                (domain.startswith('172.') and len(domain.split('.')) >= 2 and
                 domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))

    # Get local_allow_block if local
    local_allow_block = ""
    if is_local:
        local_allow_block = f"{'.'.join(domain.split('.')[:-1])}.0/24"

    nginx_deployed = False
    certificate_created = False
    server_ip = get_server_ip()
    log(f"nginx_flask helper: Detected server IP: {server_ip}")
    deployment_mode = "https" if ssl_enabled else "http"

    if ssl_enabled:
        log(f"nginx_flask helper: Starting HTTPS deployment for domain: {domain}")
        deployment_mode = "https" if not is_local else "https_local"

        # Check for certificate creation flags
        create_mode = None
        if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
            create_mode = "self-cert"
        elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
            create_mode = "get-cert"
            if is_local:
                warn("nginx_flask helper: Cannot obtain Let's Encrypt certificate for local domain")
                report_error("action", "Cannot obtain Let's Encrypt certificate for local domain")
                trace_out()
                return {"status": "error", "error": "Cannot obtain Let's Encrypt certificate for local domain"}

        # Determine certificate path
        if create_mode == "self-cert":
            certificate_path = ssl_cert_dir_self_signed / domain
        elif create_mode == "get-cert":
            certificate_path = ssl_cert_dir_letsencrypt / domain
        else:
            # Try to detect existing certificate
            letsencrypt_path = ssl_cert_dir_letsencrypt / domain / "fullchain.pem"
            self_signed_path = ssl_cert_dir_self_signed / domain / "fullchain.pem"
            if letsencrypt_path.exists():
                certificate_path = ssl_cert_dir_letsencrypt / domain
                log(f"nginx_flask helper: Found existing Let's Encrypt certificate at {certificate_path}")
            elif self_signed_path.exists():
                certificate_path = ssl_cert_dir_self_signed / domain
                log(f"nginx_flask helper: Found existing self-signed certificate at {certificate_path}")
            else:
                certificate_path = ssl_cert_dir_letsencrypt / domain
                warn(f"nginx_flask helper: Certificate not found")
                report_error("action", f"Certificate not found for domain {domain}")
                trace_out()
                return {"status": "error", "error": f"Certificate not found for domain {domain}"}

        cert_file_path = certificate_path / "fullchain.pem"

        # Create self-signed certificate if needed
        if create_mode == "self-cert":
            log("nginx_flask helper: Creating self-signed certificate...")
            from nginx_flask.deploy.deploy_helpers_ssl import generate_self_signed_certificate, ensure_certificate_exists
            cert_name = domain.replace('.', '_')

            if generate_self_signed_certificate(certificate_path, cert_name, "root", "root"):
                certificate_created = True
                log(f"nginx_flask helper: Self-signed certificate generated at {certificate_path}")

                if cert_file_path.exists():
                    if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                        warn("nginx_flask helper: Certificate verification failed after creation")
                        report_error("action", "Certificate verification failed after creation")
            else:
                warn("nginx_flask helper: Failed to generate self-signed certificate")
                report_error("action", "Failed to generate self-signed certificate")
                trace_out()
                return {"status": "error", "error": "Failed to generate self-signed certificate"}

        # Verify certificate exists
        if create_mode is None and not cert_file_path.exists():
            warn(f"nginx_flask helper: Certificate file not found at {cert_file_path}")
            report_error("action", f"Certificate file not found at {cert_file_path}")
            trace_out()
            return {"status": "error", "error": f"Certificate file not found at {cert_file_path}"}

        # Install NGINX SSL configuration
        log("nginx_flask helper: Installing NGINX SSL configuration...")

        if is_local:
            log(f"nginx_flask helper: Local deployment with access control: {local_allow_block}")
            config_content = create_nginx_ssl_config_local(domain, project_name, local_allow_block, server_ip, str(certificate_path))
            if not config_content:
                warn("nginx_flask helper: Failed to generate local NGINX SSL configuration")
                report_error("action", "Failed to generate local NGINX SSL configuration")
            else:
                # Write config
                config_file = nginx_sites_available / domain
                config_file.write_text(config_content)
                log(f"nginx_flask helper: Local NGINX SSL config written to: {config_file}")

                # Symlink to sites-enabled
                enabled_file = nginx_sites_enabled / domain
                if enabled_file.exists():
                    enabled_file.unlink()
                enabled_file.symlink_to(config_file)
                log(f"nginx_flask helper: Symlink created: {enabled_file}")

                # Test and reload NGINX
                test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                if test_result.returncode != 0:
                    warn(f"nginx_flask helper: Nginx configuration test failed: {test_result.stderr}")
                    report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                else:
                    log("nginx_flask helper: Nginx SSL configuration test passed")
                    reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                    if reload_result.returncode != 0:
                        restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                        if restart_result.returncode != 0:
                            warn(f"nginx_flask helper: Failed to reload/restart Nginx: {restart_result.stderr}")
                            report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                        else:
                            log("nginx_flask helper: Nginx restarted successfully")
                            nginx_deployed = True
                    else:
                        log("nginx_flask helper: Nginx reloaded successfully")
                        nginx_deployed = True

                    # Create decoy server
                    if nginx_deployed:
                        if not create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
                            warn("nginx_flask helper: Failed to create local decoy server")
        else:
            # Public deployment
            if install_nginx_ssl_config(domain, project_name, str(certificate_path), nginx_sites_available, nginx_sites_enabled):
                nginx_deployed = True
                log("nginx_flask helper: NGINX SSL configuration installed successfully")
            else:
                warn("nginx_flask helper: NGINX SSL configuration installation failed")
                report_error("action", "NGINX SSL configuration installation failed")

        # Get Let's Encrypt certificate if needed
        if not is_error() and create_mode == "get-cert":
            log("nginx_flask helper: Obtaining Let's Encrypt certificate...")
            from nginx_flask.deploy.deploy_helpers_ssl import get_certificate_from_letsencrypt, ensure_certificate_exists
            if get_certificate_from_letsencrypt(domain, certificate_path):
                certificate_created = True
                log(f"nginx_flask helper: Let's Encrypt certificate obtained for {domain}")

                if cert_file_path.exists():
                    if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                        warn("nginx_flask helper: Certificate verification failed after creation")
                        report_error("action", "Certificate verification failed after creation")
            else:
                warn("nginx_flask helper: Failed to obtain Let's Encrypt certificate")
                report_error("action", "Failed to obtain Let's Encrypt certificate")

    else:
        # HTTP-only deployment
        log("nginx_flask helper: Installing NGINX HTTP-only configuration...")
        deployment_mode = "http" if not is_local else "http_local"

        if is_local:
            log(f"nginx_flask helper: Local deployment with access control: {local_allow_block}")
            config_content = create_nginx_config_local(domain, project_name, local_allow_block, server_ip)
            if not config_content:
                warn("nginx_flask helper: Failed to generate local NGINX HTTP configuration")
                report_error("action", "Failed to generate local NGINX HTTP configuration")
            else:
                # Write config
                config_file = nginx_sites_available / domain
                config_file.write_text(config_content)
                log(f"nginx_flask helper: Local NGINX HTTP config written to: {config_file}")

                # Symlink to sites-enabled
                enabled_file = nginx_sites_enabled / domain
                if enabled_file.exists():
                    enabled_file.unlink()
                enabled_file.symlink_to(config_file)
                log(f"nginx_flask helper: Symlink created: {enabled_file}")

                # Test and reload NGINX
                test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                if test_result.returncode != 0:
                    warn(f"nginx_flask helper: Nginx configuration test failed: {test_result.stderr}")
                    report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                else:
                    log("nginx_flask helper: Nginx HTTP configuration test passed")
                    reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                    if reload_result.returncode != 0:
                        restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                        if restart_result.returncode != 0:
                            warn(f"nginx_flask helper: Failed to reload/restart Nginx: {restart_result.stderr}")
                            report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                        else:
                            log("nginx_flask helper: Nginx restarted successfully")
                            nginx_deployed = True
                    else:
                        log("nginx_flask helper: Nginx reloaded successfully")
                        nginx_deployed = True

                    # Create decoy server
                    if nginx_deployed:
                        if not create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
                            warn("nginx_flask helper: Failed to create local decoy server")
        else:
            # Public deployment
            if install_nginx_config(domain, project_name, nginx_sites_available, nginx_sites_enabled):
                nginx_deployed = True
                log("nginx_flask helper: NGINX HTTP configuration installed successfully")
            else:
                warn("nginx_flask helper: NGINX HTTP configuration installation failed")
                report_error("action", "NGINX HTTP configuration installation failed")

    # Get final NGINX status
    try:
        nginx_status = check_nginx_status()
        log(f"nginx_flask helper: NGINX status: active={nginx_status.get('is_active', False)}")
    except Exception:
        nginx_status = {'is_active': False, 'enabled_sites': []}

    result = {
        "module": "nginx_flask",
        "action": "deploy_nginx_ssl",
        "nginx_deployed": nginx_deployed,
        "certificate_created": certificate_created,
        "certificate_path": str(certificate_path) if ssl_enabled and 'certificate_path' in locals() else None,
        "deployment_mode": deployment_mode,
        "nginx_active": nginx_status.get('is_active', False),
        "nginx_enabled_sites": nginx_status.get('enabled_sites', []),
        "server_ip": server_ip,
        "local_allow_block": local_allow_block if is_local else None
    }

    trace_out()
    return result
