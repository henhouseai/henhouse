"""
CSS file whitelist for self-doc module deployment.
Files listed here will be added to the base CSS_WHITELIST and CSS_ALWAYS_INCLUDE.
Paths are relative to project root (above hh/ folder).
"""
from __future__ import annotations
from typing import List

# CSS files that are always included on every page (additions to base)
CSS_ALWAYS_INCLUDE: List[str] = [
    # Example: 'self_doc/deploy/site/css/custom.css',
]

# Full whitelist of all CSS files that can be included via gateway.add_css_link()
CSS_WHITELIST: List[str] = [
    'self_doc/infographic/infographic-viewer.css',
    # Example: 'self_doc/deploy/site/css/custom-theme.css',
]