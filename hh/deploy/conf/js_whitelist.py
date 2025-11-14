# JavaScript file whitelist for site deployment
# Files listed here will be deployed to /srv/{project_name}/site/js/
# Paths are relative to project root (above hh/ folder)
from typing import List

# JavaScript files that are always included on every page
JS_ALWAYS_INCLUDE: List[str] = [
    'hh/deploy/site/js/seed.js',
    'hh/deploy/site/js/rpc-client.js',
    'hh/deploy/site/js/app.js',
]

# Full whitelist of all JS files that can be included via gateway.add_js_link()
JS_WHITELIST: List[str] = [
    # JavaScript files from hh/deploy/site folder
    'hh/deploy/site/js/seed.js',
    'hh/deploy/site/js/rpc-client.js',
    'hh/deploy/site/js/app.js',
    'hh/deploy/site/js/page-manager.js',
    'hh/deploy/site/js/page-data-factory.js',
    'hh/deploy/site/js/page-data.js',
    'hh/deploy/site/js/source-code-file-page-data.js',
    'hh/deploy/site/js/mcp-request-page-data.js',
    'hh/deploy/site/js/mcp-action-page-data.js',
    'hh/deploy/site/js/page-data-derived.js',
    # Overlay system JavaScript files (deployed flat to site/js/)
    'hh/deploy/site/js/overlay-manager.js',
    'hh/deploy/site/js/overlay.js',
    'hh/deploy/site/js/overlay-backdrop.js',
    'hh/deploy/site/js/overlay-window.js',
    'hh/deploy/site/js/overlay-header.js',
    'hh/deploy/site/js/overlay-content.js',
    # Infographic JavaScript files
    'hh/deploy/site/infographic/infographic-json.js',
    'hh/deploy/site/infographic/infographic-glossary-json.js',
    'hh/deploy/site/infographic/infographic-gateway-access-methods-json.js',
    'hh/deploy/site/infographic/infographic-gateway-architecture-json.js',
    'hh/deploy/site/infographic/infographic-request-response-pipeline-json.js',
    'hh/deploy/site/infographic/infographic-http-deployment-architecture-json.js',
    'hh/deploy/site/infographic/infographic-project-folder-hierarchy-json.js',
    'hh/deploy/site/infographic/infographic-state.js',
    'hh/deploy/site/infographic/infographic-glossary.js',
    'hh/deploy/site/infographic/infographic-canvas.js',
    'hh/deploy/site/infographic/infographic-data.js',
    'hh/deploy/site/infographic/infographic-rendering.js',
    'hh/deploy/site/infographic/infographic-interaction.js',
    'hh/deploy/site/infographic/infographic-main.js'
]

