"""
Context deployment blacklist configuration.
Items listed here will be removed from the base CONTEXT_WHITELIST.
Items should match exactly as they appear in hh/deploy/conf/context_whitelist.py
"""
from __future__ import annotations
from typing import List

# Context deployment filtering - patterns to remove from base whitelist
CONTEXT_BLACKLIST: List[str] = [
    # Example: 'context',
]


