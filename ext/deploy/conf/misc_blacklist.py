"""
Miscellaneous file blacklist for site deployment.
Items listed here will be removed from the base MISC_WHITELIST.
Paths should match exactly as they appear in hh/deploy/conf/misc_whitelist.py
"""
from __future__ import annotations
from typing import List

# Miscellaneous files to remove from base whitelist
MISC_BLACKLIST: List[str] = [
    # Example: 'hh/deploy/site/favicon.ico',
]

