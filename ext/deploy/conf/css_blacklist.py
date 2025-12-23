"""
CSS file blacklist for site deployment.
Items listed here will be removed from the base CSS_WHITELIST and CSS_ALWAYS_INCLUDE.
Paths should match exactly as they appear in hh/deploy/conf/css_whitelist.py
"""
from __future__ import annotations
from typing import List

# CSS files to remove from base whitelist
CSS_BLACKLIST: List[str] = [
    # Example: 'hh/deploy/site/css/site-guest.css',
]

# CSS files to remove from always-include list
CSS_ALWAYS_INCLUDE_BLACKLIST: List[str] = [
    # Example: 'hh/deploy/site/css/site.css',
]

