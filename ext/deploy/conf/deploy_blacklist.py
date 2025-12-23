"""
Deployment cleanup blacklist configuration.
Items listed here will be removed from the base DEPLOY_WHITELIST and EXTRA_DEPLOY_FILES.
Items should match exactly as they appear in hh/deploy/conf/deploy_whitelist.py
"""
from __future__ import annotations
from typing import List

# Files and folders to remove from base deploy whitelist
DEPLOY_WHITELIST_BLACKLIST: List[str] = [
    # Example: 'cache',
]

# Files to remove from base extra deploy files
EXTRA_DEPLOY_FILES_BLACKLIST: List[str] = [
    # Example: 'hh/deploy/flask/http_client.py',
]


