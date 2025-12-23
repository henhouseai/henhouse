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
# Can include both individual files and folders (folders will deploy all .js files recursively, flattened)
JS_WHITELIST: List[str] = [
    # Deploy entire js folder (all .js files will be deployed flat to site/js/)
    'hh/deploy/site/js',
    # Deploy ext/ js folder if it exists (user extensions)
    'ext/deploy/site/js',
    # Infographic JavaScript files (individual files from different folder)
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

