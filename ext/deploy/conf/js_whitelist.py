"""
JavaScript file whitelist for site deployment.
Files listed here will be added to the base JS_WHITELIST and JS_ALWAYS_INCLUDE.
Paths are relative to project root (above hh/ folder).
"""
from __future__ import annotations
from typing import List

# JavaScript files that are always included on every page (additions to base)
JS_ALWAYS_INCLUDE: List[str] = [
    # Example: 'ext/deploy/site/js/custom-init.js',
]

# Full whitelist of all JS files that can be included via gateway.add_js_link()
# Can include both individual files and folders (folders will deploy all .js files recursively, flattened)
JS_WHITELIST: List[str] = [
	'ext/infographic/',
    # Example: 'ext/deploy/site/js/custom-module.js',
]

