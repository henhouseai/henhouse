"""
Deployment cleanup whitelist configuration.
Files listed here will be added to the base DEPLOY_WHITELIST and EXTRA_DEPLOY_FILES.
"""
from __future__ import annotations
from typing import List

# Files and folders to preserve in hh/deploy during deployment cleanup (additions to base)
DEPLOY_WHITELIST: List[str] = [
    # Example: 'custom-folder',
]

# Top-level project files to deploy into /srv/{project} (additions to base)
EXTRA_DEPLOY_FILES: List[str] = [
    # Example: 'ext/deploy/custom/client.py',
]


