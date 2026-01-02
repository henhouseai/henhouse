import os
import shutil
import subprocess
import configparser
import json
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

from hh.deploy.cache.cache_cleanup_registry import get_cache_directories
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.deploy_utils import ensure_certificate_exists

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.conf.context_blacklist import CONTEXT_BLACKLIST
from hh.deploy.deploy_utils import (
    load_whitelist_with_extensions,
)

def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _install_config_path(project_name: str) -> Path:
    return Path(f"/root/.{project_name}-install.cnf")

def _manifest_add_site(project_name: str, domain: str, mode: str) -> None:
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_sites"):
        parser.add_section("manifest_sites")
    entry = {"domain": domain, "mode": mode, "timestamp": _iso_now()}
    parser.set("manifest_sites", domain, json.dumps(entry, separators=(',', ':')))
    with open(cfg_path, 'w') as f:
        parser.write(f)
    os.chmod(cfg_path, 0o600)

def get_ips_matching_pattern(pattern: str) -> List[str]:
    """
    Get IP addresses on the system that match the given pattern.
    
    Args:
        pattern: IP pattern like "192.168.1." (matches all 192.168.1.x) or "192.168.1.100" (specific IP)
    
    Returns:
        List of matching IP addresses found on the system
    """
    trace_in()
    matching_ips = []
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
                        
                        # Check if IP matches pattern
                        if pattern.endswith('.'):
                            # Pattern like "192.168.1." - match all IPs starting with that prefix
                            if ip.startswith(pattern):
                                matching_ips.append(ip)
                        else:
                            # Specific IP pattern - exact match
                            if ip == pattern:
                                matching_ips.append(ip)
    except Exception as e:
        warn(f"Failed to get IPs matching pattern {pattern}: {e}")
    
    # Fallback: if no matches and pattern is specific IP, return it anyway (user might know what they're doing)
    if not matching_ips and not pattern.endswith('.'):
        matching_ips.append(pattern)
        log(f"No matching IPs found for pattern {pattern}, using pattern as-is")
    
    trace_out()
    return matching_ips

def create_nginx_ssl_config_local(domain: str, project_name: str, bind_ips: List[str], certificate_path: str) -> str:
    """Generate Nginx SSL configuration bound to specific local IPs only."""
    trace_in()
    try:
        # Load guest password from install config
        from hh.deploy.users.install import _load_install_config
        guest_password = None
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
        except Exception:
            pass  # If config can't be loaded, guest_password stays None (public access)
        
        # Import helpers
        from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
        from hh.deploy.http.nginx_config_helpers import (
            get_security_headers_ssl, get_block_hidden_files,
            get_auth_block, get_media_server_proxy_block, get_flask_proxy_block,
            get_server_configs, detect_flask_ports, generate_http_redirect_block
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
            "# Local-only HTTPS configuration (bound to specific IPs, prevents external access)",
            "",
        ]
        
        # Add HTTP to HTTPS redirect for all domains (bound to same IPs)
        all_domains = [domain, f'www.{domain}', f'admin.{domain}', f'panel.{domain}']
        for bind_ip in bind_ips:
            config_lines.append(f"# HTTP to HTTPS redirect (bound to {bind_ip})")
            config_lines.append("server {")
            config_lines.append(f"    listen {bind_ip}:80;")
            config_lines.append(f"    server_name {' '.join(all_domains)};")
            config_lines.append("")
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
        
        # Generate HTTPS blocks for each server, bound to each IP
        for server in servers:
            for bind_ip in bind_ips:
                block_lines = _generate_local_https_server_block(
                    server['names'],
                    server['port'],
                    static_locations,
                    certificate_path,
                    server['label'],
                    rate_limit="general",  # Not used anymore, but kept for function signature compatibility
                    project_name=project_name,
                    media_port=media_port,
                    bind_ip=bind_ip,
                    guest_password=guest_password
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
                                      bind_ip: str = "127.0.0.1",
                                      guest_password: Optional[str] = None) -> List[str]:
    """Generate an HTTPS server block that binds to a specific local IP."""
    from hh.deploy.http.nginx_config_helpers import (
        get_security_headers_ssl, get_block_hidden_files,
        get_auth_block, get_media_server_proxy_block, get_flask_proxy_block
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
        lines.append(f"# {label} (bound to {bind_ip})")
    
    lines.append("server {")
    lines.append(f"    listen {bind_ip}:443 ssl http2;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    
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
    lines.extend(get_block_hidden_files())
    
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

def create_nginx_config_local(domain: str, project_name: str, bind_ips: List[str]) -> str:
    """Generate Nginx HTTP-only configuration bound to specific local IPs only."""
    trace_in()
    try:
        # Load guest password from install config
        from hh.deploy.users.install import _load_install_config
        guest_password = None
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
        except Exception:
            pass  # If config can't be loaded, guest_password stays None (public access)
        
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
            "# Local-only HTTP configuration (intranet access only)",
            "# Generated by henhouse deploy-http-local system",
            "",
        ]
        
        # Detect media port
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        
        # Get server configurations
        servers = get_server_configs(domain, project_name)
        
        # Generate HTTP blocks for each server, bound to each IP
        for server in servers:
            for bind_ip in bind_ips:
                block_lines = _generate_local_http_server_block(
                    server['names'],
                    server['port'],
                    static_locations,
                    server['label'],
                    project_name=project_name,
                    media_port=media_port,
                    bind_ip=bind_ip,
                    guest_password=guest_password
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
                                      media_port: Optional[int] = None, bind_ip: str = "127.0.0.1",
                                      guest_password: Optional[str] = None) -> List[str]:
    """Generate an HTTP server block that binds to a specific local IP."""
    from hh.deploy.http.nginx_config_helpers import (
        get_security_headers, get_block_hidden_files,
        get_auth_block, get_media_server_proxy_block, get_flask_proxy_block
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
        lines.append(f"# {label} (bound to {bind_ip})")
    
    lines.append("server {")
    lines.append(f"    listen {bind_ip}:80;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    
    # Add security headers
    lines.extend(get_security_headers())
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking
    lines.extend(get_block_hidden_files())
    
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
        
        # Load guest password from install config
        from hh.deploy.users.install import _load_install_config
        guest_password = None
        try:
            install_config = _load_install_config(project_name)
            if install_config:
                guest_password = install_config.get("htaccess_guest_password", "").strip() or None
        except Exception:
            pass  # If config can't be loaded, guest_password stays None (public access)
        
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
        config_lines.extend(generate_http_redirect_block(all_domains))
        
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
            guest_password=guest_password
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
                guest_password=guest_password
            )
            config_lines.extend(block_lines)
        
        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx SSL config: {e}")
        trace_out()
        return ""

def install_nginx_ssl_config(domain: str, project_name: str, certificate_path: Optional[str] = None) -> bool:
    """Create Nginx SSL configuration file and enable site."""
    trace_in()
    try:
        # Generate configuration
        config_content = create_nginx_ssl_config(domain, project_name, certificate_path)
        if not config_content:
            warn("Failed to generate SSL configuration")
            trace_out()
            return False
        
        # Write to sites-available (overwrites existing HTTP config)
        config_file = Path(f'/etc/nginx/sites-available/{domain}')
        config_file.write_text(config_content)
        log(f"Nginx SSL config written to: {config_file}")
        
        # Ensure symlink exists in sites-enabled
        enabled_file = Path(f'/etc/nginx/sites-enabled/{domain}')
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
                media_port=media_port
            )
            config_lines.extend(block_lines)
        
        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx config: {e}")
        trace_out()
        return ""

def install_nginx_config(domain: str, project_name: str) -> bool:
    """Create Nginx configuration file and enable site."""
    trace_in()
    try:
        # Generate configuration
        config_content = create_nginx_config(domain, project_name)
        if not config_content:
            warn("Failed to generate configuration")
            trace_out()
            return False
        
        # Write to sites-available
        config_file = Path(f'/etc/nginx/sites-available/{domain}')
        config_file.write_text(config_content)
        log(f"Nginx config written to: {config_file}")
        
        # Create symlink to sites-enabled
        enabled_file = Path(f'/etc/nginx/sites-enabled/{domain}')
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

from hh.deploy.conf.deploy_whitelist import (
    FLASK_APP_SOURCE,
    MEDIA_SERVER_SOURCE,
    MAINTENANCE_APP_SOURCE,
)
from hh.deploy.flask.flask_start import run_flask_start
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.maintenance.maintenance_start import run_maintenance_start
from hh.deploy.maintenance.maintenance_stop import run_maintenance_stop
from hh.deploy.users.install import _install_config_path

@register_action('deploy')
@register_command('deploy')
def deploy() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Check if running in deployed Unix environment with privileges
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False

    # Detect project context
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            break
        current_path = current_path.parent
    else:
        project_name = Path.cwd().name
        current_path = Path.cwd()
    
    # Load whitelists with extension support
    CONTEXT_WHITELIST = load_whitelist_with_extensions('context_whitelist', 'CONTEXT_WHITELIST')
    JS_WHITELIST = load_whitelist_with_extensions('js_whitelist', 'JS_WHITELIST')
    JS_PAGE_CLASSES_WHITELIST = load_whitelist_with_extensions('js_page_classes_whitelist', 'JS_PAGE_CLASSES_WHITELIST')
    CSS_WHITELIST = load_whitelist_with_extensions('css_whitelist', 'CSS_WHITELIST')
    MISC_WHITELIST = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')
    HH_DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'HH_DEPLOY_WHITELIST')
    EXT_DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'EXT_DEPLOY_WHITELIST')
    HH_EXTRA_DEPLOY_FILES = load_whitelist_with_extensions('deploy_whitelist', 'HH_EXTRA_DEPLOY_FILES')
    EXT_EXTRA_DEPLOY_FILES = load_whitelist_with_extensions('deploy_whitelist', 'EXT_EXTRA_DEPLOY_FILES')
    
    # Load deployment configuration from install config
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        report_error("action", f"Install config not found: {cfg_path}")
        trace_out()
        return False
    
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        report_error("action", f"Missing [install] section in {cfg_path}")
        trace_out()
        return False
    
    sec = parser["install"]
    
    # Get starting port
    start_port_arg = gateway.get_arg('start_port')
    if start_port_arg:
        start_port = int(start_port_arg)
    else:
        port_str = sec.get("flask_start_port", "5001").strip()
        try:
            start_port = int(port_str)
        except ValueError:
            start_port = 5001
    
    # Get domain (required for HTTP deployment)
    domain = sec.get("domain", "").strip()
    if not domain:
        warn("Domain not set in install config")
        report_error("action", "Domain not set in install config")
        trace_out()
        return False
    
    # Get SSL enabled setting (required in config, defaults to 1)
    ssl_enabled_str = sec.get("ssl_enabled", "1").strip()
    try:
        ssl_enabled = int(ssl_enabled_str) != 0
    except ValueError:
        ssl_enabled = True  # Default to enabled if invalid value
        warn(f"Invalid ssl_enabled value '{ssl_enabled_str}', defaulting to 1 (enabled)")
    
    # Get SSL certificate directories
    ssl_cert_dir_letsencrypt_str = sec.get("ssl_cert_dir_letsencrypt", "/etc/letsencrypt/live").strip()
    ssl_cert_dir_letsencrypt = Path(ssl_cert_dir_letsencrypt_str)
    ssl_cert_dir_self_signed_str = sec.get("ssl_cert_dir_self_signed", "/etc/nginx/ssl").strip()
    ssl_cert_dir_self_signed = Path(ssl_cert_dir_self_signed_str)
    
    # Get local allow block (IP pattern for local deployments)
    local_allow_block = sec.get("local_allow_block", "192.168.1.").strip()
    
    # Determine certificate path based on certificate type (will be set later based on create_mode)
    # For Let's Encrypt: {ssl_cert_dir_letsencrypt}/{domain}/
    # For self-signed: {ssl_cert_dir_self_signed}/{domain}/
    certificate_path: Optional[Path] = None
    
    # Determine if local deployment
    is_local = (domain.endswith('.local') or 
                domain.lower() in ['localhost', '127.0.0.1'] or
                domain.startswith('127.') or
                domain.startswith('192.168.') or
                domain.startswith('10.') or
                (domain.startswith('172.') and len(domain.split('.')) >= 2 and 
                 domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))
    
    source = current_path
    dest = Path("/srv") / project_name
    log(f"Deploying from {source} to {dest} (starting port: {start_port}, domain: {domain}, local: {is_local})")

    # Stop running daemons prior to deployment
    if not is_error():
        try:
            log("Stopping maintenance daemon prior to deployment")
            run_maintenance_stop(project_name)
            log("Stopping Flask daemons prior to deployment")
            run_flask_stop(project_name)
        except Exception as e:  # noqa: BLE001
            warn(f"Failed to stop daemons before deployment: {e}")
            report_error("backend", f"Failed to stop daemons before deployment: {e}")

    # Preserve git folder by temporarily moving it out, then restore after cleanup
    git_dir = dest / 'git'
    temp_git_path = dest.parent / f'{project_name}_git'
    git_preserved = False
    if not is_error():
        try:
            if git_dir.exists():
                if temp_git_path.exists():
                    shutil.rmtree(temp_git_path)
                    log(f"Removed existing temporary git directory: {temp_git_path}")
                shutil.move(str(git_dir), str(temp_git_path))
                git_preserved = True
                log(f"Temporarily moved git directory to: {temp_git_path}")
            else:
                log("No git directory found to preserve")
        except Exception as e:
            warn(f"Failed to preserve git directory: {e}")
            report_error("backend", f"Failed to preserve git directory: {e}")

    # Sterilize deployment directory (remove everything except preserved git)
    if not is_error():
        try:
            if dest.exists():
                # Remove all contents
                for item in dest.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        log(f"Removed: {item}")
                    except Exception as e:
                        warn(f"Failed to remove {item}: {e}")
                log(f"Sterilized deployment directory: {dest}")
            else:
                dest.mkdir(parents=True, exist_ok=True)
                log(f"Created deployment directory: {dest}")
        except Exception as e:
            warn(f"Failed to sterilize deployment directory: {e}")
            report_error("backend", f"Failed to sterilize deployment directory: {e}")

    # Restore git folder
    if not is_error() and git_preserved:
        try:
            if temp_git_path.exists():
                shutil.move(str(temp_git_path), str(git_dir))
                log(f"Restored git directory: {git_dir}")
            else:
                warn(f"Temporary git directory not found: {temp_git_path}")
        except Exception as e:
            warn(f"Failed to restore git directory: {e}")
            report_error("backend", f"Failed to restore git directory: {e}")

    # Deploy main code
    if not is_error():
        hh_source = source / 'hh'
        hh_dest = dest / 'hh'
        code_deployed = False
        try:
            shutil.copytree(hh_source, hh_dest)
            code_deployed = True
            log(f"Deployed code: {hh_source} -> {hh_dest}")
        except Exception as e:
            warn(f"Failed to deploy code: {e}")
            report_error("backend", f"Failed to deploy code: {e}")

    # Deploy ext folder (if it exists)
    if not is_error():
        ext_source = source / 'ext'
        ext_dest = dest / 'ext'
        ext_code_deployed = False
        try:
            if ext_source.exists() and ext_source.is_dir():
                shutil.copytree(ext_source, ext_dest)
                ext_code_deployed = True
                log(f"Deployed ext code: {ext_source} -> {ext_dest}")
            else:
                log("Ext folder not found, skipping ext deployment")
        except Exception as e:
            warn(f"Failed to deploy ext code: {e}")
            report_error("backend", f"Failed to deploy ext code: {e}")

    # Clean ext/deploy directory but preserve whitelisted items (if ext/ was deployed)
    if not is_error() and ext_code_deployed:
        ext_deploy_dir = dest / 'ext' / 'deploy'
        ext_preserved_items = {}  # Map of item_name -> (source_path, temp_path)
        ext_deployment_cleaned = False
        try:
            if ext_deploy_dir.exists():
                # Temporarily move whitelisted items out
                for item_name in EXT_DEPLOY_WHITELIST:
                    item_path = ext_deploy_dir / item_name
                    if item_path.exists():
                        temp_path = dest / f".{project_name}_ext_{item_name.replace('/', '_').replace('.', '_')}_tmp"
                        
                        # Clean up existing temp if it exists
                        if temp_path.exists():
                            if temp_path.is_dir():
                                shutil.rmtree(temp_path)
                            else:
                                temp_path.unlink()
                        
                        # Move item to temp location
                        shutil.move(str(item_path), str(temp_path))
                        ext_preserved_items[item_name] = (item_path, temp_path)
                        log(f"Temporarily moved ext/{item_name}: {item_path} -> {temp_path}")

                # Remove entire ext/deploy directory contents
                shutil.rmtree(ext_deploy_dir)
                log(f"Removed ext/deploy directory: {ext_deploy_dir}")

                # Recreate ext/deploy directory and restore preserved items
                ext_deploy_dir.mkdir(parents=True, exist_ok=True)
                for item_name, (original_path, temp_path) in ext_preserved_items.items():
                    if temp_path.exists():
                        restored_path = ext_deploy_dir / item_name
                        shutil.move(str(temp_path), str(restored_path))
                        log(f"Restored ext/{item_name}: {restored_path}")

                ext_deployment_cleaned = True
            else:
                log("ext/deploy directory not found, skipping ext/deploy cleanup")
        except Exception as e:
            warn(f"Failed to clean ext/deploy directory while preserving whitelisted items: {e}")
            report_error("backend", f"Failed to clean ext/deploy directory while preserving whitelisted items: {e}")

    # Clean deployment directory but preserve whitelisted items
    if not is_error():
        deploy_dir = dest / 'hh' / 'deploy'
        preserved_items = {}  # Map of item_name -> (source_path, temp_path)
        deployment_cleaned = False
        try:
            # Temporarily move whitelisted items out
            for item_name in HH_DEPLOY_WHITELIST:
                item_path = deploy_dir / item_name
                if item_path.exists():
                    temp_path = dest / f".{project_name}_{item_name.replace('/', '_').replace('.', '_')}_tmp"
                    
                    # Clean up existing temp if it exists
                    if temp_path.exists():
                        if temp_path.is_dir():
                            shutil.rmtree(temp_path)
                        else:
                            temp_path.unlink()
                    
                    # Move item to temp location
                    shutil.move(str(item_path), str(temp_path))
                    preserved_items[item_name] = (item_path, temp_path)
                    log(f"Temporarily moved {item_name}: {item_path} -> {temp_path}")

            # Remove entire deploy directory contents
            if deploy_dir.exists():
                shutil.rmtree(deploy_dir)
                log(f"Removed deploy directory: {deploy_dir}")

            # Recreate deploy directory and restore preserved items
            deploy_dir.mkdir(parents=True, exist_ok=True)
            for item_name, (original_path, temp_path) in preserved_items.items():
                if temp_path.exists():
                    restored_path = deploy_dir / item_name
                    shutil.move(str(temp_path), str(restored_path))
                    log(f"Restored {item_name}: {restored_path}")

            deployment_cleaned = True
        except Exception as e:
            warn(f"Failed to clean deploy directory while preserving whitelisted items: {e}")
            report_error("backend", f"Failed to clean deploy directory while preserving whitelisted items: {e}")

    # Clean cache files
    if not is_error():
        cache_cleaned = {
            'pycache_dirs': 0,
            'pyc_files': 0,
            'cache_files': 0,
            'cache_dirs': 0
        }
        try:
            # Remove __pycache__ directories
            for pycache_dir in dest.rglob('__pycache__'):
                shutil.rmtree(pycache_dir)
                cache_cleaned['pycache_dirs'] += 1
                log(f"Removed __pycache__ directory: {pycache_dir}")
            
            # Remove .pyc files
            for pyc_file in dest.rglob('*.pyc'):
                pyc_file.unlink()
                cache_cleaned['pyc_files'] += 1
                log(f"Removed .pyc file: {pyc_file}")
            
            # Remove cache files
            cache_patterns = ['*-reg.json', '*.cycle.json', 'cache.json', '*.cache']
            for pattern in cache_patterns:
                for cache_file in dest.rglob(pattern):
                    cache_file.unlink()
                    cache_cleaned['cache_files'] += 1
                    log(f"Removed cache file: {cache_file}")
            
            # Remove .cache directories
            for cache_dir in dest.rglob('.cache'):
                shutil.rmtree(cache_dir)
                cache_cleaned['cache_dirs'] += 1
                log(f"Removed .cache directory: {cache_dir}")
            
            log(f"Cache cleanup complete: {cache_cleaned['pycache_dirs']} __pycache__ dirs, {cache_cleaned['pyc_files']} .pyc files, {cache_cleaned['cache_files']} cache files, {cache_cleaned['cache_dirs']} .cache dirs")
        except Exception as e:
            warn(f"Failed to clean cache files: {e}")
            report_error("backend", f"Failed to clean cache files: {e}")

    # Deploy Flask app with tier suffixes
    if not is_error():
        flask_deployed = []
        try:
            app_source = source / FLASK_APP_SOURCE
            if app_source.exists():
                for i, tier in enumerate(HENHOUSE_TIERS):
                    app_name = f'{project_name}_{tier}.py'
                    app_dest = dest / app_name
                    
                    # Read the app.py content
                    with open(app_source, 'r') as f:
                        content = f.read()
                    
                    # Replace the port with the tier-specific port
                    port = start_port + i
                    content = content.replace('port = int(os.getenv(\'PORT\', 5000))', f'port = {port}')
                    
                    # Replace the log file path with tier-specific path
                    log_file = f'/srv/{project_name}/logs/flask_{project_name}_{tier}.log'
                    content = content.replace('LOG_FILE = os.getenv(\'LOG_FILE\',', f'LOG_FILE = \'{log_file}\'  # LOG_FILE = os.getenv(\'LOG_FILE\',')
                    
                    # Write the modified content
                    with open(app_dest, 'w') as f:
                        f.write(content)
                    
                    flask_deployed.append(app_name)
                    log(f"Deployed Flask app: {app_name} (port {port})")
                log(f"Flask deployment complete: {len(flask_deployed)} instances")
            else:
                log("Flask app.py not found, skipping Flask deployment")
        except Exception as e:
            warn(f"Failed to deploy Flask apps: {e}")
            report_error("backend", f"Failed to deploy Flask apps: {e}")

    # Deploy media server Flask app
    if not is_error():
        try:
            media_source = source / MEDIA_SERVER_SOURCE
            if media_source.exists():
                media_dest = dest / f'{project_name}_media.py'
                
                # Read the media_server.py content
                with open(media_source, 'r') as f:
                    content = f.read()
                
                # Replace the port with media server port (after all tier apps)
                media_port = start_port + len(HENHOUSE_TIERS)
                content = content.replace('port = int(os.getenv(\'PORT\', 5000))', f'port = {media_port}')
                
                # Replace the log file path with media server path
                log_file = f'/srv/{project_name}/logs/flask_{project_name}_media.log'
                content = content.replace('LOG_FILE = os.getenv(\'LOG_FILE\',', f'LOG_FILE = \'{log_file}\'  # LOG_FILE = os.getenv(\'LOG_FILE\',')
                
                # Write the modified content
                with open(media_dest, 'w') as f:
                    f.write(content)
                
                log(f"Deployed Media Server Flask app: {project_name}_media.py (port {media_port})")
            else:
                log("Media server media_server.py not found, skipping media server deployment")
        except Exception as e:
            warn(f"Failed to deploy media server: {e}")
            report_error("backend", f"Failed to deploy media server: {e}")

    # Deploy maintenance worker script
    if not is_error():
        try:
            maint_source = source / MAINTENANCE_APP_SOURCE
            if maint_source.exists():
                maint_dest = dest / f'{project_name}_maintenance.py'
                content = maint_source.read_text()
                content = content.replace('__PROJECT_NAME__', project_name)
                with open(maint_dest, 'w') as f:
                    f.write(content)
                log(f"Deployed maintenance worker: {maint_dest}")
            else:
                log("Maintenance worker template not found, skipping deployment")
        except Exception as e:
            warn(f"Failed to deploy maintenance worker: {e}")
            report_error("backend", f"Failed to deploy maintenance worker: {e}")
    
    # Deploy EXT maintenance workers (e.g., migration_worker.py)
    if not is_error():
        try:
            ext_maint_dir = source / "ext" / "deploy" / "maintenance"
            if ext_maint_dir.exists():
                for worker_file in ext_maint_dir.glob("*_worker.py"):
                    daemon_name = worker_file.stem.replace("_worker", "")
                    maint_dest = dest / f'{project_name}_maintenance_{daemon_name}.py'
                    content = worker_file.read_text()
                    # No replacement needed for EXT workers (they find project root themselves)
                    with open(maint_dest, 'w') as f:
                        f.write(content)
                    log(f"Deployed EXT maintenance worker: {maint_dest} (from {worker_file.name})")
        except Exception as e:
            warn(f"Failed to deploy EXT maintenance workers: {e}")
            report_error("backend", f"Failed to deploy EXT maintenance workers: {e}")

    flask_restart_info = {}
    maintenance_restart_info = {}

    # Deploy extra top-level files (config-driven)
    if not is_error():
        try:
            for rel_path in HH_EXTRA_DEPLOY_FILES:
                src = source / rel_path
                if src.exists():
                    dst = dest / src.name
                    shutil.copy2(src, dst)
                    log(f"Deployed HH extra file: {rel_path}")
                else:
                    log(f"HH extra deploy file not found: {rel_path}")
            for rel_path in EXT_EXTRA_DEPLOY_FILES:
                src = source / rel_path
                if src.exists():
                    dst = dest / src.name
                    shutil.copy2(src, dst)
                    log(f"Deployed EXT extra file: {rel_path}")
                else:
                    log(f"EXT extra deploy file not found: {rel_path}")
        except Exception as e:
            warn(f"Failed to deploy extra files: {e}")
            report_error("backend", f"Failed to deploy extra files: {e}")

    # Deploy context folders and files
    if not is_error():
        context_deployed = []
        site_deployed = []
        try:
            for item_str in CONTEXT_WHITELIST:
                source_item = source / item_str
                if source_item.exists():
                    dest_item = dest / 'context' / item_str
                    if source_item.is_dir():
                        # Handle directories
                        if dest_item.exists():
                            shutil.rmtree(dest_item)
                        shutil.copytree(source_item, dest_item, ignore=should_ignore_context_path)
                        context_deployed.append(item_str)
                        log(f"Deployed context folder: {item_str} -> context/{item_str}")
                    elif source_item.is_file():
                        # Handle files
                        dest_item.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_item, dest_item)
                        context_deployed.append(item_str)
                        log(f"Deployed context file: {item_str} -> context/{item_str}")
                    else:
                        log(f"Context item is neither file nor directory: {item_str}")
                else:
                    log(f"Context item not found: {item_str}")
            log(f"Context deployment complete: {len(context_deployed)} items")
        except Exception as e:
            warn(f"Failed to deploy context folders: {e}")
            report_error("backend", f"Failed to deploy context folders: {e}")

    # Deploy site folders (js, css, misc)
    if not is_error():
        try:
            site_dest = dest / 'site'
            if site_dest.exists():
                shutil.rmtree(site_dest)
                log(f"Cleared existing site directory: {site_dest}")
            site_dest.mkdir(parents=True, exist_ok=True)
            
            js_count = 0
            css_count = 0
            misc_count = 0
            
            # Deploy JS files
            js_dest = site_dest / 'js'
            js_dest.mkdir(exist_ok=True)
            for js_item in JS_WHITELIST:
                source_item = source / js_item
                if source_item.exists():
                    if source_item.is_dir():
                        # If it's a directory, deploy all .js files in it (preserving subfolder structure)
                        for js_file in source_item.rglob('*.js'):
                            # Calculate relative path from source_item to preserve subfolder structure
                            relative_path = js_file.relative_to(source_item)
                            dest_js = js_dest / relative_path
                            # Create parent directories if they don't exist
                            dest_js.parent.mkdir(parents=True, exist_ok=True)
                            if dest_js.exists():
                                dest_js.unlink()
                            shutil.copy2(js_file, dest_js)
                            site_deployed.append(f"js/{relative_path.as_posix()}")
                            js_count += 1
                            log(f"Deployed JS file from folder: {js_file} -> site/js/{relative_path.as_posix()}")
                    else:
                        # If it's a file, deploy it directly to js root
                        dest_js = js_dest / source_item.name
                        if dest_js.exists():
                            dest_js.unlink()
                        shutil.copy2(source_item, dest_js)
                        site_deployed.append(f"js/{source_item.name}")
                        js_count += 1
                        log(f"Deployed JS file: {js_item} -> site/js/{source_item.name}")
                else:
                    log(f"JS file/folder not found: {js_item}")
            
            # Generate page-classes-registry.js
            if not is_error():
                try:
                    log("Generating page-classes-registry.js")
                    
                    def kebab_to_pascal(kebab: str) -> str:
                        """Convert kebab-case to PascalCase (e.g., 'source-code-file' -> 'SourceCodeFile')."""
                        parts = kebab.split('-')
                        return ''.join(word.capitalize() for word in parts)
                    
                    def kebab_to_snake(kebab: str) -> str:
                        """Convert kebab-case to snake_case (e.g., 'source-code-file' -> 'source_code_file')."""
                        return kebab.replace('-', '_')
                    
                    # Collect page class files from both hh/ and ext/ page-classes/ folders
                    # Process whitelist and check if files exist in either location
                    # Store relative paths from registry file location (hh/deploy/site/ts/) to page-classes files
                    page_class_files: List[str] = []
                    
                    # Registry file will be at: source/hh/deploy/site/js/hh/deploy/site/ts/page-classes-registry.js
                    # So we calculate relative paths from: source/hh/deploy/site/js/hh/deploy/site/ts/
                    registry_file_dir = source / 'hh' / 'deploy' / 'site' / 'js' / 'hh' / 'deploy' / 'site' / 'ts'
                    hh_page_classes_dir = source / 'hh' / 'deploy' / 'site' / 'js' / 'hh' / 'deploy' / 'site' / 'ts' / 'page-classes'
                    ext_page_classes_dir = source / 'hh' / 'deploy' / 'site' / 'js' / 'ext' / 'deploy' / 'site' / 'ts' / 'page-classes'
                    
                    # Check if ext/ directory exists (not an error if missing)
                    ext_dir_exists = ext_page_classes_dir.exists() and ext_page_classes_dir.is_dir()
                    if not ext_dir_exists:
                        log(f"Extension page-classes directory not found: {ext_page_classes_dir} (this is normal if ext/ folder doesn't exist)")
                    
                    for filename in JS_PAGE_CLASSES_WHITELIST:
                        # Check hh/ first
                        hh_file = hh_page_classes_dir / filename
                        if hh_file.exists() and hh_file.is_file():
                            # Calculate relative path from registry file directory (hh/deploy/site/ts/)
                            relative_path = hh_file.relative_to(registry_file_dir)
                            relative_path_str = str(relative_path).replace('\\', '/')
                            if relative_path_str not in page_class_files:
                                page_class_files.append(relative_path_str)
                                log(f"Found page class file in hh/: {relative_path_str}")
                        elif ext_dir_exists:
                            # Check ext/ if not found in hh/ and ext/ directory exists
                            ext_file = ext_page_classes_dir / filename
                            if ext_file.exists() and ext_file.is_file():
                                # Calculate relative path from registry file directory (hh/deploy/site/ts/)
                                # Need to go up to js/ level, then into ext/ path
                                # From: hh/deploy/site/ts/ -> Up 4 levels to js/ -> Then ext/deploy/site/ts/page-classes/
                                relative_path = ext_file.relative_to(registry_file_dir.parent.parent.parent.parent)
                                relative_path_str = str(relative_path).replace('\\', '/')
                                if relative_path_str not in page_class_files:
                                    page_class_files.append(relative_path_str)
                                    log(f"Found page class file in ext/: {relative_path_str}")
                            else:
                                # File not found in either location - log but don't error
                                log(f"Page class file not found (whitelisted but missing): {filename}")
                        else:
                            # File not found in hh/ and ext/ doesn't exist - log but don't error
                            log(f"Page class file not found in hh/ and ext/ not available: {filename}")
                    
                    # Generate registry file
                    if page_class_files:
                        registry_lines: List[str] = []
                        registry_lines.append("// Auto-generated during deployment - do not edit manually")
                        registry_lines.append("")
                        
                        # Generate imports
                        import_lines: List[str] = []
                        registry_entries: List[str] = []
                        
                        for relative_path_str in sorted(page_class_files):
                            # Extract filename from relative path for base_name conversion
                            filename = os.path.basename(relative_path_str)
                            # Remove .js extension and -page-data suffix
                            base_name = filename.replace('.js', '')
                            if base_name.endswith('-page-data'):
                                base_name = base_name[:-10]  # Remove '-page-data'
                            
                            # Convert to snake_case for class name (matches actual export names)
                            class_name = kebab_to_snake(base_name) + '_page_data'
                            
                            # Convert to snake_case for registry key
                            registry_key = kebab_to_snake(base_name)
                            
                            # Generate import using full relative path (preserves nested structure)
                            # For hh/ files: relative_path_str is already correct (e.g., "page-classes/ask-page-data.js")
                            # For ext/ files: relative_path_str is from js/ level, need to add ../../../../ prefix
                            if relative_path_str.startswith('ext/'):
                                # Ext file: go up 4 levels from registry file (hh/deploy/site/ts/) to js/, then into ext/
                                import_path = f"../../../../{relative_path_str}"
                            else:
                                # Hh file: already relative to registry file directory
                                import_path = f"./{relative_path_str}"
                            import_lines.append(f"import {{ {class_name} }} from '{import_path}';")
                            
                            # Generate registry entry
                            registry_entries.append(f"  '{registry_key}': {class_name},")
                        
                        registry_lines.extend(import_lines)
                        registry_lines.append("")
                        registry_lines.append("export const PAGE_CLASS_REGISTRY = {")
                        registry_lines.extend(registry_entries)
                        registry_lines.append("};")
                        
                        # Write registry file to placeholder location in deployment destination (overwrites compiled placeholder)
                        registry_file = dest / 'site' / 'js' / 'hh' / 'deploy' / 'site' / 'ts' / 'page-classes-registry.js'
                        registry_content = '\n'.join(registry_lines) + '\n'
                        try:
                            registry_file.write_text(registry_content, encoding='utf-8')
                        except Exception as e:
                            warn(f"Failed to write page-classes-registry.js: {e}")
                            raise
                        site_deployed.append("js/hh/deploy/site/ts/page-classes-registry.js")
                        log(f"Generated page-classes-registry.js with {len(page_class_files)} page classes")
                    else:
                        log("No page class files found in whitelist, skipping registry generation")
                        
                except Exception as e:  # noqa: BLE001
                    log(f"Failed to generate page-classes-registry.js: {e}")
                    # Don't error out - registry generation is optional
            
            # Deploy CSS files
            css_dest = site_dest / 'css'
            css_dest.mkdir(exist_ok=True)
            for css_file in CSS_WHITELIST:
                source_css = source / css_file
                if source_css.exists():
                    dest_css = css_dest / source_css.name
                    if dest_css.exists():
                        dest_css.unlink()
                    shutil.copy2(source_css, dest_css)
                    site_deployed.append(f"css/{source_css.name}")
                    css_count += 1
                    log(f"Deployed CSS file: {css_file} -> site/css/{source_css.name}")
                else:
                    log(f"CSS file not found: {css_file}")
            
            # Deploy misc files (top level in site/)
            for misc_file in MISC_WHITELIST:
                source_misc = source / misc_file
                if source_misc.exists():
                    if source_misc.is_dir():
                        # Copy entire directory
                        dest_misc = site_dest / source_misc.name
                        if dest_misc.exists():
                            shutil.rmtree(dest_misc)
                        shutil.copytree(source_misc, dest_misc)
                        site_deployed.append(misc_file)
                        misc_count += 1
                        log(f"Deployed misc directory: {misc_file} -> site/{source_misc.name}")
                    else:
                        # Copy single file
                        dest_misc = site_dest / source_misc.name
                        if dest_misc.exists():
                            dest_misc.unlink()
                        shutil.copy2(source_misc, dest_misc)
                        site_deployed.append(misc_file)
                        misc_count += 1
                        log(f"Deployed misc file: {misc_file} -> site/{source_misc.name}")
                else:
                    log(f"Misc file not found: {misc_file}")
            
            log(f"Site deployment complete: {len(site_deployed)} items (JS: {js_count}, CSS: {css_count}, MISC: {misc_count})")
        except Exception as e:
            warn(f"Failed to deploy site folders: {e}")
            report_error("backend", f"Failed to deploy site folders: {e}")

    # Set ownership and permissions
    if not is_error():
        ownership_set = False
        try:
            project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
            user_info = gateway.os.get_user_by_name(project_highest_user)
            if not user_info:
                raise ValueError(f"User not found: {project_highest_user}")
            project_highest_uid = user_info["uid"]
            deploy_group_name = f"{project_name}_deploy"
            
            subprocess.run(['chown', '-R', f'{project_highest_uid}:{deploy_group_name}', str(dest)], check=True)
            subprocess.run(['find', str(dest), '-type', 'd', '-exec', 'chmod', '750', '{}', ';'], check=True)
            subprocess.run(['find', str(dest), '-type', 'f', '-exec', 'chmod', '640', '{}', ';'], check=True)
            
            # Fix git directory permissions
            git_dir = dest / 'git'
            if git_dir.exists():
                subprocess.run(['chown', '-R', f'{project_highest_uid}:{project_name}', str(git_dir)], check=True)
                subprocess.run(['find', str(git_dir), '-type', 'd', '-exec', 'chmod', '770', '{}', ';'], check=True)
                subprocess.run(['find', str(git_dir), '-type', 'f', '-exec', 'chmod', '660', '{}', ';'], check=True)
                log(f"Set git directory permissions: {project_highest_user}:{project_name}")
            
            ownership_set = True
            log(f"Set ownership and permissions: {project_highest_user}:{deploy_group_name}")
        except Exception as e:
            warn(f"Failed to set ownership and permissions: {e}")
            report_error("backend", f"Failed to set ownership and permissions: {e}")

    # Set up cache permissions
    if not is_error():
        cache_permissions_set = False
        try:
            project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
            user_info = gateway.os.get_user_by_name(project_highest_user)
            if not user_info:
                raise ValueError(f"User not found: {project_highest_user}")
            project_highest_uid = user_info["uid"]
            deploy_group_name = f"{project_name}_deploy"
            
            cache_dirs = [dest / cache_dir for cache_dir in get_cache_directories()]
            
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    gateway.files.chmod(str(cache_dir), 0o2775)
                    log(f"Set cache directory permissions: {cache_dir}")
                else:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    gateway.files.chmod(str(cache_dir), 0o2775)
                    log(f"Created cache directory with group write: {cache_dir}")
                
                # Set ownership so all tier users can write via group permissions
                subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(cache_dir)], check=True)
                log(f"Set cache directory ownership: {cache_dir} -> {project_highest_user}:{deploy_group_name}")
            
            cache_permissions_set = True
            log("Cache directory permissions set successfully")
        except Exception as e:
            warn(f"Failed to set up cache permissions: {e}")
            report_error("backend", f"Failed to set up cache permissions: {e}")

    # Set up logs directory for Flask daemons
    if not is_error():
        logs_permissions_set = False
        try:
            logs_dir = dest / 'logs'
            if logs_dir.exists():
                shutil.rmtree(logs_dir)
                log(f"Cleared existing logs directory: {logs_dir}")
            logs_dir.mkdir(parents=True, exist_ok=True)
            gateway.files.chmod(str(logs_dir), 0o2775)
            
            # Set ownership so Flask daemons can write logs
            project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
            user_info = gateway.os.get_user_by_name(project_highest_user)
            if not user_info:
                raise ValueError(f"User not found: {project_highest_user}")
            project_highest_uid = user_info["uid"]
            deploy_group_name = f"{project_name}_deploy"
            subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(logs_dir)], check=True)
            
            log(f"Created fresh logs directory with group write: {logs_dir}")
            log(f"Set logs directory ownership: {project_highest_user}:{deploy_group_name}")
            
            logs_permissions_set = True
            log("Logs directory permissions set successfully")
        except Exception as e:
            warn(f"Failed to set up logs permissions: {e}")
            report_error("backend", f"Failed to set up logs permissions: {e}")

    # Restart daemons after permissions/logs are in place
    if not is_error():
        try:
            log("Starting Flask daemons after deployment")
            flask_restart_info = run_flask_start(project_name, start_port)
            log("Starting maintenance daemon after deployment")
            maintenance_restart_info = run_maintenance_start(project_name)
            log(f"Daemon restart summary: Flask={flask_restart_info.get('summary')}, Maintenance={maintenance_restart_info.get('status')}")
        except Exception as e:  # noqa: BLE001
            warn(f"Failed to restart daemons after deployment: {e}")
            report_error("backend", f"Failed to restart daemons after deployment: {e}")

    # Step: HTTP/SSL Deployment (NGINX setup and certificate management)
    nginx_deployed = False
    certificate_created = False
    bind_ips = []
    deployment_mode = "https"  # Track deployment mode for manifest
    if not is_error():
        try:
            if ssl_enabled:
                log(f"Starting HTTPS deployment for domain: {domain}")
                deployment_mode = "https" if not is_local else "https_local"
            else:
                log(f"Starting HTTP-only deployment for domain: {domain}")
                deployment_mode = "http" if not is_local else "http_local"
            
            # Import NGINX helpers
            from hh.deploy.http.nginx_config_helpers import detect_flask_ports
            
            if ssl_enabled:
            
                # SSL deployment path
                # Check for certificate creation flags
                create_mode = None
                if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
                    create_mode = "self-cert"
                elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
                    create_mode = "get-cert"
                    if is_local:
                        warn("Cannot obtain Let's Encrypt certificate for local domain")
                        warn(f"Domain '{domain}' is detected as local - use -self-cert flag instead")
                        report_error("action", "Cannot obtain Let's Encrypt certificate for local domain")
                        trace_out()
                        return False
                
                    # Determine certificate path based on certificate type
                if create_mode == "self-cert":
                    certificate_path = ssl_cert_dir_self_signed / domain
                elif create_mode == "get-cert":
                    certificate_path = ssl_cert_dir_letsencrypt / domain
                else:
                    # Try to detect existing certificate (check both locations)
                    letsencrypt_path = ssl_cert_dir_letsencrypt / domain / "fullchain.pem"
                    self_signed_path = ssl_cert_dir_self_signed / domain / "fullchain.pem"
                    if letsencrypt_path.exists():
                        certificate_path = ssl_cert_dir_letsencrypt / domain
                        log(f"Found existing Let's Encrypt certificate at {certificate_path}")
                    elif self_signed_path.exists():
                        certificate_path = ssl_cert_dir_self_signed / domain
                        log(f"Found existing self-signed certificate at {certificate_path}")
                    else:
                        # Default to Let's Encrypt location if no certificate found
                        certificate_path = ssl_cert_dir_letsencrypt / domain
                        warn(f"Certificate not found at either {letsencrypt_path} or {self_signed_path}")
                        warn("Use -self-cert flag to generate self-signed certificate, or -get-cert flag to obtain Let's Encrypt certificate")
                        report_error("action", f"Certificate not found for domain {domain}")
                        trace_out()
                        return False
                
                # Determine certificate file path
                # NGINX always expects fullchain.pem and privkey.pem
                cert_file_path = certificate_path / "fullchain.pem"
                
                # For self-signed certificates, create the certificate BEFORE setting up NGINX
                # (NGINX config test requires the certificate file to exist)
                if create_mode == "self-cert":
                    log("Creating self-signed certificate before NGINX setup...")
                    from hh.deploy.deploy_utils import generate_self_signed_certificate
                    cert_name = domain.replace('.', '_')  # Use domain as cert name base
                    cert_owner_user = "root"
                    cert_owner_group = "root"
                    
                    if generate_self_signed_certificate(certificate_path, cert_name, cert_owner_user, cert_owner_group):
                        certificate_created = True
                        log(f"Self-signed certificate generated at {certificate_path}")
                        
                        # Verify certificate exists and fix permissions if needed
                        if cert_file_path.exists():
                            if not ensure_certificate_exists(
                                cert_path=str(cert_file_path),
                                cert_owner_user="root",
                                cert_owner_group="root",
                                create_mode=None  # Don't create, just verify/fix
                            ):
                                warn("Certificate verification failed after creation")
                                report_error("action", "Certificate verification failed after creation")
                    else:
                        warn("Failed to generate self-signed certificate")
                        report_error("action", "Failed to generate self-signed certificate")
                        trace_out()
                        return False
            
                # Verify certificate exists (for existing certificates or after self-signed creation)
                if create_mode is None and not cert_file_path.exists():
                    warn(f"Certificate file not found at {cert_file_path}")
                    report_error("action", f"Certificate file not found at {cert_file_path}")
                    trace_out()
                    return False
                
                # Set up NGINX with SSL configuration (pointing to certificate path)
                # For self-signed: certificate already exists
                # For Let's Encrypt: cert doesn't exist yet, but NGINX needs to be running for ACME challenge
                log("Installing NGINX SSL configuration...")
                
                if is_local:
                    # For local deployments, bind to specific IPs to prevent external access
                    bind_ips = get_ips_matching_pattern(local_allow_block)
                    if not bind_ips:
                        warn(f"No IPs found matching pattern '{local_allow_block}'")
                        warn("Falling back to 127.0.0.1 for local deployment")
                        bind_ips = ['127.0.0.1']
                    
                    log(f"Local deployment: binding to IPs: {', '.join(bind_ips)}")
                    
                    # Generate local SSL config
                    config_content = create_nginx_ssl_config_local(domain, project_name, bind_ips, str(certificate_path))
                    if not config_content:
                        warn("Failed to generate local NGINX SSL configuration")
                        report_error("action", "Failed to generate local NGINX SSL configuration")
                    else:
                        # Write to sites-available
                        config_file = Path(f'/etc/nginx/sites-available/{domain}')
                        config_file.write_text(config_content)
                        log(f"Local NGINX SSL config written to: {config_file}")
                        
                        # Ensure symlink exists in sites-enabled
                        enabled_file = Path(f'/etc/nginx/sites-enabled/{domain}')
                        if enabled_file.exists():
                            enabled_file.unlink()
                        enabled_file.symlink_to(config_file)
                        log(f"Symlink created: {enabled_file}")
                        
                        # Test Nginx configuration
                        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                        if test_result.returncode != 0:
                            warn(f"Nginx configuration test failed: {test_result.stderr}")
                            report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                        else:
                            log("Nginx SSL configuration test passed")
                            
                            # Reload Nginx
                            reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                            if reload_result.returncode != 0:
                                restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                                if restart_result.returncode != 0:
                                    warn(f"Failed to reload/restart Nginx: {restart_result.stderr}")
                                    report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                                else:
                                    log("Nginx restarted successfully")
                                    nginx_deployed = True
                            else:
                                log("Nginx reloaded successfully")
                                nginx_deployed = True
                else:
                    # For public deployments, use standard SSL config (binds to all interfaces)
                    if install_nginx_ssl_config(domain, project_name, str(certificate_path)):
                        nginx_deployed = True
                        log("NGINX SSL configuration installed successfully")
                    else:
                        warn("NGINX SSL configuration installation failed")
                        report_error("action", "NGINX SSL configuration installation failed")
                
                # Now get Let's Encrypt certificate if needed (NGINX is running, which is required for ACME challenge)
                # Note: Self-signed certificates are already created above, before NGINX setup
                if not is_error() and create_mode == "get-cert":
                    log("Obtaining Let's Encrypt certificate (NGINX must be running for ACME challenge)...")
                    from hh.deploy.deploy_utils import get_certificate_from_letsencrypt
                    if get_certificate_from_letsencrypt(domain, certificate_path):
                        certificate_created = True
                        log(f"Let's Encrypt certificate obtained for {domain}")
                        
                        # Verify certificate exists and fix permissions if needed
                        if cert_file_path.exists():
                            if not ensure_certificate_exists(
                                cert_path=str(cert_file_path),
                                cert_owner_user="root",
                                cert_owner_group="root",
                                create_mode=None  # Don't create, just verify/fix
                            ):
                                warn("Certificate verification failed after creation")
                                report_error("action", "Certificate verification failed after creation")
                    else:
                        warn("Failed to obtain Let's Encrypt certificate")
                        report_error("action", "Failed to obtain Let's Encrypt certificate")
            
            else:
                # HTTP-only deployment path
                log("Installing NGINX HTTP-only configuration...")
                
                if is_local:
                    # For local deployments, bind to specific IPs to prevent external access
                    bind_ips = get_ips_matching_pattern(local_allow_block)
                    if not bind_ips:
                        warn(f"No IPs found matching pattern '{local_allow_block}'")
                        warn("Falling back to 127.0.0.1 for local deployment")
                        bind_ips = ['127.0.0.1']
                    
                    log(f"Local deployment: binding to IPs: {', '.join(bind_ips)}")
                    
                    # Generate local HTTP config
                    config_content = create_nginx_config_local(domain, project_name, bind_ips)
                    if not config_content:
                        warn("Failed to generate local NGINX HTTP configuration")
                        report_error("action", "Failed to generate local NGINX HTTP configuration")
                    else:
                        # Write to sites-available
                        config_file = Path(f'/etc/nginx/sites-available/{domain}')
                        config_file.write_text(config_content)
                        log(f"Local NGINX HTTP config written to: {config_file}")
                        
                        # Ensure symlink exists in sites-enabled
                        enabled_file = Path(f'/etc/nginx/sites-enabled/{domain}')
                        if enabled_file.exists():
                            enabled_file.unlink()
                        enabled_file.symlink_to(config_file)
                        log(f"Symlink created: {enabled_file}")
                        
                        # Test Nginx configuration
                        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                        if test_result.returncode != 0:
                            warn(f"Nginx configuration test failed: {test_result.stderr}")
                            report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                        else:
                            log("Nginx HTTP configuration test passed")
                            
                            # Reload Nginx
                            reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                            if reload_result.returncode != 0:
                                restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                                if restart_result.returncode != 0:
                                    warn(f"Failed to reload/restart Nginx: {restart_result.stderr}")
                                    report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                                else:
                                    log("Nginx restarted successfully")
                                    nginx_deployed = True
                            else:
                                log("Nginx reloaded successfully")
                                nginx_deployed = True
                else:
                    # For public deployments, use standard HTTP config (binds to all interfaces)
                    if install_nginx_config(domain, project_name):
                        nginx_deployed = True
                        log("NGINX HTTP configuration installed successfully")
                    else:
                        warn("NGINX HTTP configuration installation failed")
                        report_error("action", "NGINX HTTP configuration installation failed")
            
            # Check NGINX status
            nginx_status = check_nginx_status()
            log(f"NGINX status: active={nginx_status.get('is_active', False)}")
            
        except Exception as e:
            warn(f"Failed to deploy HTTP/SSL configuration: {e}")
            report_error("action", f"Failed to deploy HTTP/SSL configuration: {e}")

    # Final result
    result = not is_error()
    if result:
        log("Deployment completed successfully")
        
        # Get NGINX status if available
        nginx_status_data = {}
        if 'nginx_status' in locals():
            nginx_status_data = nginx_status
        else:
            try:
                nginx_status_data = check_nginx_status()
            except Exception:
                pass
        
        # Add to manifest
        try:
            _manifest_add_site(project_name, domain, deployment_mode)
        except Exception as e:
            warn(f"Failed to record site in manifest: {e}")
        
        result_data = {
            "project_name": project_name,
            "source": str(source),
            "destination": str(dest),
            "domain": domain,
            "is_local": is_local,
            "ssl_enabled": ssl_enabled,
            "deployment_mode": deployment_mode,
            "code_deployed": code_deployed,
            "deployment_cleaned": deployment_cleaned,
            "cache_cleaned": cache_cleaned,
            "flask_deployed": flask_deployed,
            "context_deployed": context_deployed,
            "site_deployed": site_deployed,
            "js_count": js_count if 'js_count' in locals() else 0,
            "css_count": css_count if 'css_count' in locals() else 0,
            "misc_count": misc_count if 'misc_count' in locals() else 0,
            "ownership_set": ownership_set,
            "cache_permissions_set": cache_permissions_set,
            "logs_permissions_set": logs_permissions_set,
            "flask_restart": flask_restart_info,
            "maintenance_restart": maintenance_restart_info,
            "nginx_deployed": nginx_deployed,
            "certificate_created": certificate_created,
            "certificate_path": str(certificate_path) if ssl_enabled and 'certificate_path' in locals() else None,
            "nginx_active": nginx_status_data.get('is_active', False),
            "nginx_enabled_sites": nginx_status_data.get('enabled_sites', []),
            "bind_ips": bind_ips if is_local else [],
            "status": "deployed"
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Deployment encountered problems")

    # Clear registry cache to prevent permission issues
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return result


def cleanup_old_deployment() -> None:
    # Get project name dynamically
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            break
        current_path = current_path.parent
    else:
        project_name = Path.cwd().name
    
    users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
    
    dest = Path(f'/srv/{project_name}')
    if dest.exists():
        log(f"Removing old deployment: {dest}")
        shutil.rmtree(dest)
    for user in users:
        user_home = Path(f'/home/{user}')
        gateway_script = user_home / 'gateway.py'
        if gateway_script.exists():
            log(f"Removing gateway.py for {user}")
            gateway_script.unlink()
        hh_script = user_home / 'hh'
        if hh_script.exists():
            log(f"Removing hh script for {user}")
            hh_script.unlink()




def deploy_context_folders(source: Path, dest: Path) -> None:
    """Deploy context folders and files for agent visibility."""
    trace_in()
    try:
        log("Deploying context folders and files")
        
        # Load context whitelist with extension support
        CONTEXT_WHITELIST = load_whitelist_with_extensions('context_whitelist', 'CONTEXT_WHITELIST')
        
        # Deploy whitelisted context items (folders and files) with blacklist filtering
        for item in CONTEXT_WHITELIST:
            source_item = source / item
            if source_item.exists():
                dest_item = dest / 'context' / item
                if source_item.is_dir():
                    # Handle directories
                    log(f"Deploying context folder: {item} -> context/{item}")
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(source_item, dest_item, ignore=should_ignore_context_path)
                elif source_item.is_file():
                    # Handle files
                    log(f"Deploying context file: {item} -> context/{item}")
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_item, dest_item)
                else:
                    log(f"Context item is neither file nor directory: {item}")
            else:
                log(f"Context item not found: {item}")
        
        log("Context deployment complete")
    except Exception as e:
        warn(f"Context deployment failed: {str(e)}")
        raise
    finally:
        trace_out()

def should_ignore_context_path(directory: str, files: List[str]) -> List[str]:
    """Determine which files/folders to ignore for context deployment."""
    ignored = []
    
    for item in files:
        item_path = Path(directory) / item
        
        # Check if any part of the path matches blacklist
        for blacklist_pattern in CONTEXT_BLACKLIST:
            if matches_blacklist_pattern(item_path, blacklist_pattern):
                ignored.append(item)
                break
    
    return ignored

def matches_blacklist_pattern(path: Path, pattern: str) -> bool:
    """Check if a path matches a blacklist pattern."""
    # Convert pattern to Path for comparison
    pattern_path = Path(pattern)
    
    # Check if any part of the path matches
    for part in path.parts:
        if part == pattern_path.name or part == pattern_path.stem:
            return True
    
    # Check if the full path contains the pattern
    if pattern in str(path):
        return True
    
    # Check for wildcard patterns
    if '*' in pattern:
        import fnmatch
        if fnmatch.fnmatch(str(path), pattern):
            return True
    
    return False

def setup_deployment_ownership_and_permissions(project_name: str) -> None:
    """Set ownership and permissions for deployed code (copied from init.py)."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            warn("Gateway or ProcessManager not available")
            trace_out()
            return
        
        # Set ownership of deployment directory to project highest level user with deploy group AFTER deployment
        srv_project = Path("/srv") / project_name
        if srv_project.exists():
            try:
                project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
                user_info = gateway.os.get_user_by_name(project_highest_user)
                if not user_info:
                    warn(f"User not found: {project_highest_user}")
                    trace_out()
                    return
                project_highest_uid = user_info["uid"]
                deploy_group_name = f"{project_name}_deploy"
                subprocess.run(['chown', '-R', f'{project_highest_uid}:{deploy_group_name}', str(srv_project)], check=True)
                
                # Set secure permissions: directories 750, files 640
                subprocess.run(['find', str(srv_project), '-type', 'd', '-exec', 'chmod', '750', '{}', ';'], check=True)
                subprocess.run(['find', str(srv_project), '-type', 'f', '-exec', 'chmod', '640', '{}', ';'], check=True)
                
                # Fix git directory permissions: owner can write, group can read and write
                git_dir = srv_project / 'git'
                if git_dir.exists():
                    subprocess.run(['chown', '-R', f'{project_highest_uid}:{project_name}', str(git_dir)], check=True)
                    subprocess.run(['find', str(git_dir), '-type', 'd', '-exec', 'chmod', '770', '{}', ';'], check=True)
                    subprocess.run(['find', str(git_dir), '-type', 'f', '-exec', 'chmod', '660', '{}', ';'], check=True)
                    log(f"Set git directory permissions: {project_highest_user}:{project_name} (owner:rw, group:rw)")
                
                log(f"Set ownership and permissions: {project_highest_user}:{deploy_group_name} (owner:rw, group:r)")
            except Exception as e:
                warn(f"Failed to set ownership and permissions: {str(e)}")
    except Exception as e:
        warn(f"Failed to setup deployment ownership and permissions: {str(e)}")
    finally:
        trace_out()