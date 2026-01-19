"""
hh_flask Module - Flask Application Deployment and Daemon Management

Scope:
- Flask tier daemon lifecycle (stop, restart)
- Flask tier application deployment (guest, verified, admin, root tiers)
- Media server deployment
- Flask log permissions management

This module manages the deployment and operation of Flask-based application servers
across multiple security tiers, providing independent daemon processes for each tier.
"""

MODULE = {
    'name': 'hh_flask',
    'description': 'Henhouse Flask module - Flask application deployment and daemon management',
    'version': '1.0.0',
    'dependencies': ['hh_srv'],  # Requires server infrastructure
}
