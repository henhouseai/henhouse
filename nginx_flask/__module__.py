"""
NGINX/Flask Module - Web Serving Subsystem

Provides Flask application deployment, NGINX reverse proxy configuration,
and SSL certificate management for Henhouse projects.

This module will contain:
- Flask tier app templates and deployment
- Media server Flask app
- NGINX configuration generation (HTTP and HTTPS)
- SSL certificate utilities (self-signed and Let's Encrypt)
- Action scripts for Flask and NGINX management
"""

MODULE = {
    "name": "nginx_flask",
    "version": "1.0.0",
    "description": "Web serving subsystem - Flask apps, NGINX config, SSL certificates",
    "dependencies": []
}
