import subprocess
import shutil
import os
import configparser
import json
import datetime
import socket
from pathlib import Path
from typing import Dict, Any, List, Optional
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error

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

def get_local_network_ips() -> List[str]:
    """Detect local network IP addresses (non-loopback, non-public)."""
    local_ips = []
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
                        # Check if it's a private IP (RFC 1918)
                        parts_ip = ip.split('.')
                        if len(parts_ip) == 4:
                            first_octet = int(parts_ip[0])
                            second_octet = int(parts_ip[1])
                            # Private IP ranges: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
                            if (first_octet == 10 or
                                (first_octet == 172 and 16 <= second_octet <= 31) or
                                (first_octet == 192 and second_octet == 168)):
                                local_ips.append(ip)
    except Exception as e:
        warn(f"Failed to detect local IPs: {e}")
    
    # Fallback: try to get default gateway interface IP
    if not local_ips:
        try:
            result = subprocess.run(['ip', 'route', 'get', '8.8.8.8'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'src' in line:
                        parts = line.split('src')
                        if len(parts) >= 2:
                            ip = parts[1].strip().split()[0]
                            if ip not in local_ips:
                                local_ips.append(ip)
        except Exception:
            pass
    
    return local_ips

def create_nginx_config_local(domain: str, project_name: str, bind_ips: List[str]) -> str:
    """Generate Nginx configuration for local network only (intranet)."""
    trace_in()
    try:
        # Import helpers
        from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
        from hh.deploy.http.nginx_config_helpers import get_server_configs, detect_flask_ports
        
        # Get static locations and summary
        whitelist_result = generate_nginx_static_locations(project_name)
        static_locations = whitelist_result['config'] if isinstance(whitelist_result, dict) else whitelist_result
        whitelist_summary = whitelist_result.get('summary', {}) if isinstance(whitelist_result, dict) else {}

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
        
        # Build config
        config_lines = [
            "# Local-only HTTP configuration (intranet access only)",
            "# Generated by henhouse deploy-http-local system",
            "",
        ]
        
        # Detect media port
        ports = detect_flask_ports(project_name)
        media_port = ports.get('media', 5005)
        
        # Generate server blocks for each bind IP
        servers = get_server_configs(domain, project_name)
        for server in servers:
            for bind_ip in bind_ips:
                block_lines = _generate_local_server_block(
                    server['names'],
                    server['port'],
                    static_locations,
                    server['label'],
                    project_name=project_name,
                    media_port=media_port,
                    bind_ip=bind_ip
                )
                config_lines.extend(block_lines)
        
        config = '\n'.join(config_lines)
        trace_out()
        return config
    except Exception as e:
        warn(f"Failed to generate Nginx config: {e}")
        trace_out()
        return ""

def _generate_local_server_block(server_names: List[str], port: int, static_locations: str,
                                 label: str = "", project_name: str = "henhouse",
                                 media_port: Optional[int] = None, bind_ip: str = "127.0.0.1") -> List[str]:
    """Generate a server block that binds to a specific local IP."""
    from hh.deploy.http.nginx_config_helpers import (
        get_security_headers, get_rate_limiting, get_block_hidden_files,
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
    
    # Add rate limiting
    lines.extend(get_rate_limiting())
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking
    lines.extend(get_block_hidden_files())
    
    # Add authentication for admin/panel subdomains
    # Map port to tier using actual detected ports
    from hh.deploy.http.nginx_config_helpers import detect_flask_ports
    ports = detect_flask_ports(project_name)
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier))
    
    # Add media server proxy
    lines.extend(get_media_server_proxy_block(media_port))
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

def install_nginx_config_local(domain: str, project_name: str, bind_ips: List[str]) -> bool:
    """Create Nginx configuration file bound to local IPs only."""
    trace_in()
    try:
        # Generate configuration
        config_content = create_nginx_config_local(domain, project_name, bind_ips)
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
        if enabled_file.exists():
            enabled_file.unlink()  # Remove existing symlink if present
        enabled_file.symlink_to(config_file)
        log(f"Symlink created: {enabled_file}")
        
        # Test Nginx configuration
        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if test_result.returncode != 0:
            warn(f"Nginx configuration test failed: {test_result.stderr}")
            enabled_file.unlink()
            config_file.unlink()
            trace_out()
            return False
        
        log("Nginx configuration test passed")
        
        # Reload Nginx
        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
        if reload_result.returncode != 0:
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

def detect_project_name() -> str:
    """Detect project name from current directory."""
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            return "henhouse"
        cwd = gateway.os.get_cwd()
        if cwd.startswith('/srv/'):
            parts = cwd.split('/')
            if len(parts) >= 3:
                return parts[2]
        else:
            current_path = Path(cwd)
            while current_path != current_path.parent:
                hh_dir = current_path / 'hh'
                if hh_dir.exists() and hh_dir.is_dir():
                    return current_path.name
                current_path = current_path.parent
        return "henhouse"
    except Exception:
        return "henhouse"

@register_action('http_deploy_local')
@register_command('http_deploy_local')
def http_deploy_local() -> bool:
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

    # Get domain argument
    domain = gateway.get_arg('domain')
    if not domain:
        warn("Domain argument required")
        report_error("action", "Domain argument required")
        trace_out()
        return False
    
    # Enforce .local domain requirement for local-only deployment
    if not domain.endswith('.local'):
        warn("Local deployment requires domain ending in .local")
        report_error("action", "Local deployment requires domain ending in .local")
        trace_out()
        return False
    
    # Detect project name
    project_name = detect_project_name()
    log(f"Project: {project_name}")
    
    # Detect local network IPs
    bind_ips = get_local_network_ips()
    if not bind_ips:
        warn("No local network IPs detected. Falling back to 127.0.0.1")
        bind_ips = ['127.0.0.1']
    
    log(f"Detected local IPs: {', '.join(bind_ips)}")
    log(f"Starting local-only HTTP deployment for domain: {domain}")
    
    # Install Nginx configuration
    config_installed = False
    try:
        if install_nginx_config_local(domain, project_name, bind_ips):
            config_installed = True
            log("Nginx configuration installed successfully")
        else:
            warn("Nginx configuration installation failed")
            report_error("action", "Nginx configuration installation failed")
    except Exception as e:
        warn(f"Failed to install Nginx configuration: {e}")
        report_error("action", f"Failed to install Nginx configuration: {e}")

    # Check Nginx status
    nginx_status = check_nginx_status()

    # Get whitelist summary for display
    from hh.deploy.http.nginx_whitelist import generate_nginx_static_locations
    whitelist_result = generate_nginx_static_locations(project_name)
    whitelist_summary = whitelist_result.get('summary', {}) if isinstance(whitelist_result, dict) else {}

    # Final result
    result = not is_error()
    if result:
        log("Local HTTP deployment completed successfully")
        result_data = {
            "domain": domain,
            "project_name": project_name,
            "config_installed": config_installed,
            "nginx_active": nginx_status.get('is_active', False),
            "bind_ips": bind_ips,
            "port": 80,
            "config_file_path": f"/etc/nginx/sites-available/{domain}",
            "main_domain": domain,
            "subdomains": [f"www.{domain}", f"admin.{domain}", f"panel.{domain}"],
            "whitelist_summary": whitelist_summary,
            "status": "deployed_local",
            "stage": "1_local"
        }
        try:
            _manifest_add_site(project_name, domain, "http_local")
        except Exception as e:
            warn(f"Failed to record site in manifest: {e}")
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Local HTTP deployment encountered problems")

    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    trace_out()
    return result

