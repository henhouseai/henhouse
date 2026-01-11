"""
Context deployment whitelist configuration.
Items listed here will be added to the base CONTEXT_WHITELIST.
"""
from __future__ import annotations
from typing import List

# Context deployment filtering - folders that should be deployed for agent visibility (additions to base)
CONTEXT_WHITELIST: List[str] = [
    # Example: 'custom-docs',
]


