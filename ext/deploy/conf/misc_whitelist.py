"""
Miscellaneous file whitelist for site deployment.
Files listed here will be added to the base MISC_WHITELIST.
Paths are relative to project root (above hh/ folder).
"""
from __future__ import annotations
from typing import List

# Miscellaneous files to deploy to /srv/{project_name}/site/ (top level)
MISC_WHITELIST: List[str] = [
    # Example: 'ext/deploy/site/custom-favicon.ico',
]

