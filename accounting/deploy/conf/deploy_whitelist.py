"""
Deployment cleanup whitelist configuration.
Files listed here will be added to the base whitelists.
"""
from __future__ import annotations
from typing import List

# Files and folders to preserve in hh/deploy during deployment cleanup (additions to base HH_DEPLOY_WHITELIST)
HH_DEPLOY_WHITELIST: List[str] = [
    # Example: 'custom-folder',
]

# Files and folders to preserve in ext/deploy during deployment cleanup (additions to base EXT_DEPLOY_WHITELIST)
EXT_DEPLOY_WHITELIST: List[str] = [
    'maint',  # Maintenance tools (migration_daemon, migration_status, etc.)
]

# Top-level project files to deploy into /srv/{project} (additions to base HH_EXTRA_DEPLOY_FILES)
HH_EXTRA_DEPLOY_FILES: List[str] = [
    # Example: 'hh/deploy/custom/client.py',
]

# Top-level project files to deploy into /srv/{project} (additions to base EXT_EXTRA_DEPLOY_FILES)
EXT_EXTRA_DEPLOY_FILES: List[str] = [
    # Example: 'ext/deploy/custom/client.py',
]

# Files and folders to preserve in accounting/deploy during deployment cleanup
# These items are temporarily moved out, the deploy directory is cleaned, then restored
# This field is NOT aggregated across modules - each module controls its own cleanup
MODULE_DEPLOY_WHITELIST: List[str] = [
    'conf',       # Whitelist configurations
    'maint',      # Maintenance tools (migration_daemon, migration_status, etc.)
    'db',         # Database schema and data
]


