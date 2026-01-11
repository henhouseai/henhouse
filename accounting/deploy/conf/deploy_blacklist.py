"""
Deployment cleanup blacklist configuration.
Items listed here will be removed from the base whitelists.
Items should match exactly as they appear in hh/deploy/conf/deploy_whitelist.py
"""
from __future__ import annotations
from typing import List

# Files and folders to remove from base HH_DEPLOY_WHITELIST
HH_DEPLOY_WHITELIST: List[str] = [
    # Example: 'cache',
]

# Files and folders to remove from base EXT_DEPLOY_WHITELIST
EXT_DEPLOY_WHITELIST: List[str] = [
    # Example: 'custom-folder',
]

# Files to remove from base HH_EXTRA_DEPLOY_FILES
HH_EXTRA_DEPLOY_FILES: List[str] = [
    # Example: 'hh/deploy/flask/http_client.py',
]

# Files to remove from base EXT_EXTRA_DEPLOY_FILES
EXT_EXTRA_DEPLOY_FILES: List[str] = [
    # Example: 'ext/deploy/custom/client.py',
]


