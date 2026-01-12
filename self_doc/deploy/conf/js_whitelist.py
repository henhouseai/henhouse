"""
JavaScript file whitelist for self-doc module deployment.
Files listed here will be added to the base JS_WHITELIST and JS_ALWAYS_INCLUDE.
Paths are relative to project root (above hh/ folder).
"""
from __future__ import annotations
from typing import List

# JavaScript files that are always included on every page (additions to base)
JS_ALWAYS_INCLUDE: List[str] = [
    # Example: 'self_doc/deploy/site/js/custom-init.js',
]

# Full whitelist of all JS files that can be included via gateway.add_js_link()
# Can include both individual files and folders (folders will deploy all .js files recursively, flattened)
JS_WHITELIST: List[str] = [
    'self_doc/infographic/infographic-json.js',
    'self_doc/infographic/infographic-glossary-json.js',
    'self_doc/infographic/infographic-gateway-access-methods-json.js',
    'self_doc/infographic/infographic-gateway-architecture-json.js',
    'self_doc/infographic/infographic-request-response-pipeline-json.js',
    'self_doc/infographic/infographic-http-deployment-architecture-json.js',
    'self_doc/infographic/infographic-project-folder-hierarchy-json.js',
    'self_doc/infographic/infographic-state.js',
    'self_doc/infographic/infographic-glossary.js',
    'self_doc/infographic/infographic-canvas.js',
    'self_doc/infographic/infographic-data.js',
    'self_doc/infographic/infographic-rendering.js',
    'self_doc/infographic/infographic-interaction.js',
    'self_doc/infographic/infographic-main.js',
    # Example: 'self_doc/deploy/site/js/custom-module.js',
]