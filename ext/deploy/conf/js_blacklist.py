"""
JavaScript file blacklist for site deployment.
Items listed here will be removed from the base JS_WHITELIST and JS_ALWAYS_INCLUDE.
Paths should match exactly as they appear in hh/deploy/conf/js_whitelist.py
"""
from __future__ import annotations
from typing import List

# JavaScript files to remove from base whitelist
JS_BLACKLIST: List[str] = [
    # Example: 'hh/deploy/site/js/some-file.js',
]

# JavaScript files to remove from always-include list
JS_ALWAYS_INCLUDE_BLACKLIST: List[str] = [
    # Example: 'hh/deploy/site/js/seed.js',
]



