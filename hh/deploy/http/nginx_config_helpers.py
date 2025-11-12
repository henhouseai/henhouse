"""Common Nginx configuration helpers for HTTP and HTTPS deployments."""
from typing import List
from hh.deploy.users.user_account_suffixes import HENHOUSE_TIERS

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
        "    limit_req zone=general burst=20 nodelay;",
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

def get_auth_block(project_name: str, tier: str) -> List[str]:
    """Return HTTP Basic Auth configuration for admin/panel subdomains."""
    # Only apply auth to admin and root tiers
    if tier not in HENHOUSE_TIERS:
        return []
    
    # Get the tier index to determine which .htpasswd file to use
    try:
        tier_idx = HENHOUSE_TIERS.index(tier)
    except ValueError:
        return []
    
    # Admin tier uses .htpasswd_{tier_name}, root tier uses .htpasswd_panel
    if tier == 'admin':
        htpasswd_file = f"/var/www/.htpasswd_{tier}"
    elif tier == 'root':
        htpasswd_file = "/var/www/.htpasswd_panel"
    else:
        # No auth for other tiers
        return []
    
    return [
        "    # HTTP Basic Auth for admin/panel access",
        f"    auth_basic \"{project_name.title()}\";",
        f"    auth_basic_user_file {htpasswd_file};",
        "",
    ]

def get_flask_proxy_block(port: int) -> List[str]:
    """Return Flask proxy_pass configuration for a given port."""
    return [
        f"    # Proxy all other requests to Flask app (port {port})",
        "    location / {",
        f"        proxy_pass http://127.0.0.1:{port};",
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "        proxy_set_header X-Forwarded-Proto $scheme;",
        "    }",
    ]

def generate_server_block(server_names: List[str], port: int, static_locations: str, 
                         label: str = "", extra_blocks: List[str] = None, project_name: str = "henhouse") -> List[str]:
    """Generate a complete Nginx server block.
    
    Args:
        server_names: List of server names for this block
        port: Flask port to proxy to
        static_locations: Pre-formatted static location blocks
        label: Optional comment label for the server block
        extra_blocks: Optional extra configuration blocks to add before proxy
        
    Returns:
        List of strings for the server block
    """
    lines = []
    
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
    # Map port to tier based on HENHOUSE_TIERS order (default ports: 5001=guest, 5002=verified, 5003=admin, 5004=root)
    default_ports = {tier: 5001 + idx for idx, tier in enumerate(HENHOUSE_TIERS)}
    tier = None
    for t, p in default_ports.items():
        if port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier))
    
    # Add any extra blocks (like SSL redirects)
    if extra_blocks:
        lines.extend(extra_blocks)
        lines.append("")
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

def detect_flask_ports(project_name: str) -> dict:
    """Detect Flask app ports by reading the deployed app files."""
    import re
    ports = {}
    
    for tier in ['guest', 'verified', 'admin', 'root']:
        app_file = f'/srv/{project_name}/{project_name}_{tier}.py'
        try:
            with open(app_file, 'r') as f:
                content = f.read()
            
            # Look for port = XXXX pattern
            match = re.search(r'port\s*=\s*(\d+)', content)
            if match:
                ports[tier] = int(match.group(1))
        except FileNotFoundError:
            # Fall back to default ports if file doesn't exist
            default_ports = {'guest': 5001, 'verified': 5002, 'admin': 5003, 'root': 5004}
            ports[tier] = default_ports[tier]
        except Exception:
            # Fall back to default ports on any error
            default_ports = {'guest': 5001, 'verified': 5002, 'admin': 5003, 'root': 5004}
            ports[tier] = default_ports[tier]
    
    return ports

def get_server_configs(domain: str, project_name: str = None) -> List[dict]:
    """Get server configuration definitions for a domain.
    
    Returns list of dicts with:
        - names: List of server names
        - port: Flask port to use
        - label: Display label
    """
    # Detect actual ports from deployed Flask apps
    if project_name:
        ports = detect_flask_ports(project_name)
    else:
        # Fall back to default ports
        ports = {'guest': 5001, 'verified': 5002, 'admin': 5003, 'root': 5004}
    
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
    """Generate HTTP to HTTPS redirect server block."""
    lines = [
        "# HTTP - redirect to HTTPS",
        "server {",
        "    listen 80;",
        "    listen [::]:80;",
        f"    server_name {' '.join(all_domains)};",
        "    return 301 https://$host$request_uri;",
        "}",
        "",
    ]
    return lines

def generate_https_server_block(server_names: List[str], port: int, static_locations: str,
                               certificate_path: str, label: str = "", rate_limit: str = "general",
                               extra_blocks: List[str] = None, project_name: str = "henhouse") -> List[str]:
    """Generate a complete Nginx HTTPS server block.
    
    Args:
        server_names: List of server names for this block
        port: Flask port to proxy to
        static_locations: Pre-formatted static location blocks
        certificate_path: Path to SSL certificate directory
        label: Optional comment label for the server block
        rate_limit: Rate limit zone (general or admin)
        extra_blocks: Optional extra configuration blocks to add before proxy
        
    Returns:
        List of strings for the server block
    """
    lines = []
    
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
    
    # Add authentication for admin/panel subdomains
    # Map port to tier based on HENHOUSE_TIERS order (default ports: 5001=guest, 5002=verified, 5003=admin, 5004=root)
    default_ports = {tier: 5001 + idx for idx, tier in enumerate(HENHOUSE_TIERS)}
    tier = None
    for t, p in default_ports.items():
        if port == p:
            tier = t
            break
    
    if tier and tier in HENHOUSE_TIERS:
        lines.extend(get_auth_block(project_name, tier))
    
    # Add any extra blocks (like auth)
    if extra_blocks:
        lines.extend(extra_blocks)
        lines.append("")
    
    # Add Flask proxy
    lines.extend(get_flask_proxy_block(port))
    
    lines.append("}")
    lines.append("")
    
    return lines

