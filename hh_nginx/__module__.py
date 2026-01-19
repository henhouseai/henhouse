"""
hh_nginx Module - NGINX Web Server Configuration and SSL Management

Scope:
- NGINX configuration generation and installation
- SSL certificate creation and verification (via Let's Encrypt)
- NGINX configuration testing, restart, and verification
- NGINX configuration removal (during uninstall)
- NGINX reload operations
- NGINX decoy cleanup

This module manages the NGINX web server configuration including SSL certificates,
reverse proxy setup for Flask tiers, and lifecycle operations.
"""

MODULE = {
    'name': 'hh_nginx',
    'description': 'Henhouse Nginx module - web server configuration, SSL certificates, reverse proxy',
    'version': '1.0.0',
    'dependencies': ['hh_srv'],  # Requires server infrastructure
}
