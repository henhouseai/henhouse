"""
Miscellaneous file whitelist for self-doc module deployment.
Files listed here will be added to the base MISC_WHITELIST.
Paths are relative to project root (above hh/ folder).
"""
from __future__ import annotations
from typing import List

# Miscellaneous files to deploy to /srv/{project_name}/site/ (top level)
MISC_WHITELIST: List[str] = [
    'self_doc/infographic/infographic-viewer.html',
    # Example: 'self_doc/deploy/site/custom-favicon.ico',
]