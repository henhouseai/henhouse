"""
Site links blacklist configuration.
Group names listed here will be removed from the base SITE_LINKS.
Matches by the 'group' key in each group dict.
"""
from __future__ import annotations
from typing import List

# Site link groups to remove from base list (by group name)
SITE_LINKS_BLACKLIST: List[str] = [
    # Example: 'home',
]

