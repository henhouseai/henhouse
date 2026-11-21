"""Common Nginx configuration helpers for HTTP and HTTPS deployments."""
import configparser
from typing import List, Optional
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.install_helpers_config import get_install_config_path

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

def normalize_allow_ranges(local_allow_block: str) -> List[str]:
    """Turn a comma-separated allow list into valid nginx `allow` values.

    Accepts CIDR (`192.168.1.0/24`, `fd00::/8`), single addresses (`10.0.0.5`, `::1`) and the old
    install config's dotted prefixes (`192.168.1.` -> `192.168.1.0/24`, `10.` -> `10.0.0.0/8`).
    Anything else is dropped, so a bad entry can never produce an `allow` line nginx rejects.
    """
    import ipaddress
    ranges: List[str] = []
    for raw in (local_allow_block or "").split(','):
        entry = raw.strip()
        if not entry:
            continue
        if entry.endswith('.') and '/' not in entry:
            octets = entry.rstrip('.').split('.')
            if 1 <= len(octets) <= 3 and all(o.isdigit() for o in octets):
                entry = '.'.join(octets + ['0'] * (4 - len(octets))) + f"/{8 * len(octets)}"
        try:
            net = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        value = str(net.network_address) if net.num_addresses == 1 else str(net)
        if value not in ranges:
            ranges.append(value)
    return ranges

def get_client_ip_access_control(local_allow_block: str) -> List[str]:
    """
    Generate nginx allow/deny directives for client IP access control.

    Args:
        local_allow_block: Comma-separated ranges (see normalize_allow_ranges), e.g.
                          "192.168.1.0/24,10.0.0.0/8".  127.0.0.1 is always allowed.

    Returns:
        List of nginx directive strings for allow/deny rules.
    """
    lines = [
        "    # Client IP access control (intranet only)",
    ]
    allow_ranges = normalize_allow_ranges(local_allow_block)
    if not any(r.startswith('127.') for r in allow_ranges):
        lines.append("    allow 127.0.0.1;")
    for range_str in allow_ranges:
        lines.append(f"    allow {range_str};")
    lines.append("    deny all;")
    lines.append("")
    return lines

def get_acme_challenge_block(webroot_dir: str = "/var/www/html") -> List[str]:
    """Return the Let's Encrypt ACME challenge location.

    `^~` makes this prefix win over every regex location (hidden-file blocking, static
    whitelist).  `allow all` replaces any server-level allow/deny list (nginx does not merge
    access rules into a location that sets its own), and `auth_basic off` drops any
    server-level Basic Auth, so certbot's HTTP-01 check is never answered with 403 or 401.
    """
    return [
        "    # Let's Encrypt ACME challenges: always reachable, before any deny or auth rule",
        "    location ^~ /.well-known/acme-challenge/ {",
        "        allow all;",
        "        auth_basic off;",
        f"        root {webroot_dir};",
        "        try_files $uri =404;",
        "    }",
        "",
    ]

def get_block_hidden_files(webroot_dir: str = "/var/www/html") -> List[str]:
    """Return location blocks to block hidden files but allow .well-known."""
    return get_acme_challenge_block(webroot_dir) + [
        "    # Block hidden files (but allow .well-known)",
        "    location ~ /\\.(?!well-known) {",
        "        deny all;",
        "        access_log off;",
        "        log_not_found off;",
        "    }",
        "",
    ]

def get_auth_block(project_name: str, tier: str, guest_password: Optional[str] = None, htpasswd_dir: Optional[str] = None) -> List[str]:
    """Return HTTP Basic Auth configuration for guest/admin/panel subdomains."""
    if tier not in HENHOUSE_TIERS:
        return []
    
    # Get the tier index to determine which .htpasswd file to use
    try:
        tier_idx = HENHOUSE_TIERS.index(tier)
    except ValueError:
        return []
    
    # Load htpasswd_dir from install config if not provided
    if htpasswd_dir is None:
        try:
            from hh.deploy.install_helpers_config import load_install_config
            install_config = load_install_config(project_name)
            if install_config:
                htpasswd_dir = install_config.get("htpasswd_dir", "/var/www").strip()
            else:
                htpasswd_dir = "/var/www"
        except Exception:
            htpasswd_dir = "/var/www"  # Default fallback
    
    # Guest tier uses .htpasswd_guest (only if password is provided)
    if tier == 'guest':
        if not guest_password or not guest_password.strip():
            # No password set - public access, no auth
            return []
        htpasswd_file = f"{htpasswd_dir}/.htpasswd_guest"
    # Admin tier uses .htpasswd_{tier_name}
    elif tier == 'admin':
        htpasswd_file = f"{htpasswd_dir}/.htpasswd_{tier}"
    # Root tier uses .htpasswd_panel
    elif tier == 'root':
        htpasswd_file = f"{htpasswd_dir}/.htpasswd_panel"
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
                         label: str = "", extra_blocks: Optional[List[str]] = None, project_name: str = "henhouse", media_port: Optional[int] = None, webroot_dir: str = "/var/www/html") -> List[str]:
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
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking
    lines.extend(get_block_hidden_files(webroot_dir))
    
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
    cfg_path = get_install_config_path(project_name)
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

def generate_http_redirect_block(all_domains: List[str], webroot_dir: str = "/var/www/html") -> List[str]:
    """Generate HTTP to HTTPS redirect server block.

    Includes exception for Let's Encrypt ACME challenges which must be served on HTTP.
    """
    lines = [
        "# HTTP - redirect to HTTPS (except ACME challenges)",
        "server {",
        "    listen 80;",
        "    listen [::]:80;",
        f"    server_name {' '.join(all_domains)};",
        "",
    ]
    lines.extend(get_acme_challenge_block(webroot_dir))
    lines.extend([
        "    # Redirect all other HTTP traffic to HTTPS",
        "    location / {",
        "        return 301 https://$host$request_uri;",
        "    }",
        "}",
        "",
    ])
    return lines

def generate_https_server_block(server_names: List[str], port: int, static_locations: str,
                               certificate_path: str, label: str = "",
                               extra_blocks: Optional[List[str]] = None, project_name: str = "henhouse", media_port: Optional[int] = None, guest_password: Optional[str] = None, webroot_dir: str = "/var/www/html") -> List[str]:
    """Generate a complete Nginx HTTPS server block.
    
    Args:
        server_names: List of server names for this block
        port: Flask port to proxy to
        static_locations: Pre-formatted static location blocks
        certificate_path: Path to SSL certificate directory
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
    
    # Add static file whitelist locations
    lines.append("    # Static file whitelist locations (served directly by Nginx)")
    for line in static_locations.split('\n'):
        lines.append(f"    {line}")
    lines.append("")
    
    # Add hidden file blocking
    lines.extend(get_block_hidden_files(webroot_dir))
    
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

