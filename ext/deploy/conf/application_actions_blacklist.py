"""
Application action links blacklist configuration.
Group names listed here will be removed from the base APPLICATION_ACTIONS.
Matches by the 'group' key in each group dict.
"""
from __future__ import annotations
from typing import List

# Application action groups to remove from base list (by group name)
APPLICATION_ACTIONS_BLACKLIST: List[str] = [
    # Example: 'test',
]


