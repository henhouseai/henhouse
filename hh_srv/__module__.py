"""
hh_srv Module - Server Infrastructure and Deployment Base

Scope:
- Deployment configuration pre-validation
- JS/CSS/Misc whitelist loading
- Directory sterilization (removing deployment directory contents)
- Cache cleanup (cleaning pycache files from deployment directory)
- Client files deployment (CLIENT_WHITELIST items to deployment directory)
- Site directory preparation
- Site files deployment (CSS, JS, misc files)
- Base permissions (deployment directory ownership and permissions)
- Cache directory permissions
- Site file permissions
- Manifest management (adding deployed sites to manifest with SSL mode)
- Deployment file removal (during uninstall)
- Manifest clearing (during uninstall)

This module provides the foundational server infrastructure for deployment operations,
managing files, directories, and permissions for the deployed application.
"""

MODULE = {
    'name': 'hh_srv',
    'description': 'Henhouse Server module - base deployment infrastructure, file operations, permissions',
    'version': '1.0.0',
    'dependencies': [],  # Base infrastructure, no dependencies
}
