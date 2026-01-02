"""Common Nginx configuration helpers for HTTP and HTTPS deployments."""
import configparser
from typing import List, Optional
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.users.install import _install_config_path

def get_security_headers() -> List[str]:
    """Return standard security headers for all server blocks."""
    return [
        "    # Security headers",
        '    add_header X-Frame-Options "SAMEORIGIN" always;',
        '    add_header X-Content-Type-Options "nosniff" always;',
        '    add_header X-XSS-Protection "1; mode=block" always;',
        '    add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
        "",
    ]

def get_rate_limiting() -> List[str]:
    """Return rate limiting configuration."""
    return [
        "    # Rate limiting",
        "    limit_req zone=general burst=100 nodelay;",
        "",
    ]

def get_block_hidden_files() -> List[str]:
    """Return location blocks to block hidden files but allow .well-known."""
    return [
        "    # Allow Let's Encrypt ACME challenges",
        "    location /.well-known/acme-challenge/ {",
        "        root /var/www/html;",
        "        try_files $uri =404;",
        "    }",
        "",
        "    # Block hidden files (but allow .well-known)",
        "    location ~ /\\.(?!well-known) {",
        "        deny all;",
        "        access_log off;",
        "        log_not_found off;",
        "    }",
        "",
    ]

def get_auth_block(project_name: str, tier: str, guest_password: Optional[str] = None) -> List[str]:
    """Return HTTP Basic Auth configuration for guest/admin/panel subdomains."""
    if tier not in HENHOUSE_TIERS:
        return []
    
    # Get the tier index to determine which .htpasswd file to use
    try:
        tier_idx = HENHOUSE_TIERS.index(tier)
    except ValueError:
        return []
    
    # Guest tier uses .htpasswd_guest (only if password is provided)
    if tier == 'guest':
        if not guest_password or not guest_password.strip():
            # No password set - public access, no auth
            return []
        htpasswd_file = "/var/www/.htpasswd_guest"
    # Admin tier uses .htpasswd_{tier_name}
    elif tier == 'admin':
        htpasswd_file = f"/var/www/.htpasswd_{tier}"
    # Root tier uses .htpasswd_panel
    elif tier == 'root':
        htpasswd_file = "/var/www/.htpasswd_panel"
    else:
        # No auth for other tiers
        return []
    
    return [
        "    # HTTP Basic Auth",
        f"    auth_basic \"{project_name.title()}\";",
        f"    auth_basic_user_file {htpasswd_file};",
        "",
    ]

def get_media_server_proxy_block(media_port: int) -> List[str]:
    """Return media server proxy_pass configuration for download/stream routes."""
    return [
        "    # Media server routes (downloads and streams)",
        "    # Route all media download/stream requests to dedicated media server",
        "    location ~ ^/(file|img|audio|video)/\\d+/(download|stream)$ {",
        "        client_max_body_size 50M;",
        f"        proxy_pass http://127.0.0.1:{media_port};",
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "        proxy_set_header X-Forwarded-Proto $scheme;",
        "    }",
        "",
    ]

def get_flask_proxy_block(port: int) -> List[str]:
    """Return Flask proxy_pass configuration for a given port."""
    return [
        f"    # Proxy all other requests to Flask app (port {port})",
        "    location / {",
        "        client_max_body_size 50M;",
        f"        proxy_pass http://127.0.0.1:{port};",
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "        proxy_set_header X-Forwarded-Proto $scheme;",
        "    }",
    ]

def generate_server_block(server_names: List[str], port: int, static_locations: str, 
                         label: str = "", extra_blocks: Optional[List[str]] = None, project_name: str = "henhouse", media_port: Optional[int] = None) -> List[str]:
    """Generate a complete Nginx server block.
    
    Args:
        server_names: List of server names for this block
        port: Flask port to proxy to
        static_locations: Pre-formatted static location blocks
        label: Optional comment label for the server block
        extra_blocks: Optional extra configuration blocks to add before proxy
        project_name: Project name for detecting media port (required)
        media_port: Media server port (if None, will be detected from installer manifest)
        
    Returns:
        List of strings for the server block
    
    Raises:
        FileNotFoundError: If installer manifest not found
        ValueError: If installer manifest invalid or missing flask_start_port
    """
    lines = []
    
    # Detect ports from installer manifest
    ports = detect_flask_ports(project_name)
    if media_port is None:
        media_port = ports['media']
    
    # Add label comment if provided
    if label:
        lines.append(f"# {label}")
    
    lines.append("server {")
    lines.append("    listen 80;")
    lines.append("    listen [::]:80;")
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
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier))
    
    # Add any extra blocks (like SSL redirects)
    if extra_blocks:
        lines.extend(extra_blocks)
        lines.append("")
    
    # Add media server proxy (before Flask proxy so it takes precedence)
    lines.extend(get_media_server_proxy_block(media_port))
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

def _load_flask_start_port(project_name: str) -> int:
    """Load flask_start_port from installer manifest. Fails hard if config missing or invalid."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Installer manifest not found: {cfg_path}")
    
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    
    if "install" not in parser:
        raise ValueError(f"Missing [install] section in installer manifest: {cfg_path}")
    
    section = parser["install"]
    flask_start_port_str = section.get("flask_start_port", "").strip()
    
    if not flask_start_port_str:
        raise ValueError(f"Missing flask_start_port in installer manifest: {cfg_path}")
    
    try:
        flask_start_port = int(flask_start_port_str)
    except ValueError:
        raise ValueError(f"Invalid flask_start_port value '{flask_start_port_str}' in installer manifest: {cfg_path}")
    
    return flask_start_port

def detect_flask_ports(project_name: str) -> dict:
    """Detect Flask app ports from installer manifest. Fails hard if config missing or invalid."""
    flask_start_port = _load_flask_start_port(project_name)
    ports = {}
    
    # Calculate ports based on tier index: flask_start_port + tier_index
    for idx, tier in enumerate(HENHOUSE_TIERS):
        ports[tier] = flask_start_port + idx
    
    # Media server port is after all tier apps
    ports['media'] = flask_start_port + len(HENHOUSE_TIERS)
    
    return ports

def get_server_configs(domain: str, project_name: str) -> List[dict]:
    """Get server configuration definitions for a domain.
    
    Args:
        domain: Domain name
        project_name: Project name (required - used to load installer manifest)
    
    Returns list of dicts with:
        - names: List of server names
        - port: Flask port to use
        - label: Display label
    
    Raises:
        FileNotFoundError: If installer manifest not found
        ValueError: If installer manifest invalid or missing flask_start_port
    """
    if not project_name:
        raise ValueError("project_name is required")
    
    ports = detect_flask_ports(project_name)
    
    return [
        {'names': [domain, f'www.{domain}'], 'port': ports['guest'], 'label': 'Main site (Guest)'},
        {'names': [f'admin.{domain}'], 'port': ports['admin'], 'label': 'Admin subdomain'},
        {'names': [f'panel.{domain}'], 'port': ports['root'], 'label': 'Panel subdomain'},
    ]

def get_security_headers_ssl() -> List[str]:
    """Return security headers for HTTPS server blocks (includes HSTS)."""
    return [
        "    # Security headers",
        '    add_header X-Frame-Options "SAMEORIGIN" always;',
        '    add_header X-Content-Type-Options "nosniff" always;',
        '    add_header X-XSS-Protection "1; mode=block" always;',
        '    add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
        '    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;',
        "",
    ]

def generate_http_redirect_block(all_domains: List[str]) -> List[str]:
    """Generate HTTP to HTTPS redirect server block.
    
    Includes exception for Let's Encrypt ACME challenges which must be served on HTTP.
    Automatically includes db and cache subdomains for Henhouse sites.
    """
    # Extract base domain (first domain without www prefix)
    base_domain = all_domains[0] if all_domains else ""
    if base_domain.startswith("www."):
        base_domain = base_domain[4:]
    
    # Add db and cache subdomains if not already present
    extended_domains = list(all_domains)
    db_subdomain = f"db.{base_domain}"
    cache_subdomain = f"cache.{base_domain}"
    
    if db_subdomain not in extended_domains:
        extended_domains.append(db_subdomain)
    if cache_subdomain not in extended_domains:
        extended_domains.append(cache_subdomain)
    
    lines = [
        "# HTTP - redirect to HTTPS (except ACME challenges)",
        "server {",
        "    listen 80;",
        "    listen [::]:80;",
        f"    server_name {' '.join(extended_domains)};",
        "",
        "    # Allow Let's Encrypt ACME challenges (must be on HTTP for webroot validation)",
        "    location /.well-known/acme-challenge/ {",
        "        root /var/www/html;",
        "        try_files $uri =404;",
        "    }",
        "",
        "    # Redirect all other HTTP traffic to HTTPS",
        "    location / {",
        "        return 301 https://$host$request_uri;",
        "    }",
        "}",
        "",
    ]
    return lines

def generate_https_server_block(server_names: List[str], port: int, static_locations: str,
                               certificate_path: str, label: str = "", rate_limit: str = "general",
                               extra_blocks: Optional[List[str]] = None, project_name: str = "henhouse", media_port: Optional[int] = None, guest_password: Optional[str] = None) -> List[str]:
    """Generate a complete Nginx HTTPS server block.
    
    Args:
        server_names: List of server names for this block
        port: Flask port to proxy to
        static_locations: Pre-formatted static location blocks
        certificate_path: Path to SSL certificate directory
        label: Optional comment label for the server block
        rate_limit: Rate limit zone (general or admin)
        extra_blocks: Optional extra configuration blocks to add before proxy
        project_name: Project name for detecting media port (required)
        media_port: Media server port (if None, will be detected from installer manifest)
        
    Returns:
        List of strings for the server block
    
    Raises:
        FileNotFoundError: If installer manifest not found
        ValueError: If installer manifest invalid or missing flask_start_port
    """
    lines = []
    
    # Detect ports from installer manifest
    ports = detect_flask_ports(project_name)
    if media_port is None:
        media_port = ports['media']
    
    # Add label comment if provided
    if label:
        lines.append(f"# HTTPS - {label}")
    
    lines.append("server {")
    lines.append("    listen 443 ssl http2;")
    lines.append("    listen [::]:443 ssl http2;")
    lines.append(f"    server_name {' '.join(server_names)};")
    lines.append("")
    
    # Add SSL certificates
    lines.append("    ssl_certificate {}/fullchain.pem;".format(certificate_path))
    lines.append("    ssl_certificate_key {}/privkey.pem;".format(certificate_path))
    lines.append("")
    
    # Add security headers (includes HSTS)
    lines.extend(get_security_headers_ssl())
    
    # Add rate limiting
    burst = "100" if rate_limit == "admin" else "100"
    lines.append("    # Rate limiting")
    lines.append("    limit_req zone={} burst={} nodelay;".format(rate_limit, burst))
    lines.append("")
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking
    lines.extend(get_block_hidden_files())
    
    # Add authentication for guest/admin/panel subdomains
    # Map port to tier using actual detected ports
    ports = detect_flask_ports(project_name)
    tier = None
    for t, p in ports.items():
        if t != 'media' and port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier, guest_password))
    
    # Add any extra blocks (like auth)
    if extra_blocks:
        lines.extend(extra_blocks)
        lines.append("")
    
    # Add media server proxy (before Flask proxy so it takes precedence)
    lines.extend(get_media_server_proxy_block(media_port))
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

