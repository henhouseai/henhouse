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
    # Infographic JavaScript files (individual files from ext/ folder)
    'ext/infographic/infographic-json.js',
    'ext/infographic/infographic-glossary-json.js',
    'ext/infographic/infographic-gateway-access-methods-json.js',
    'ext/infographic/infographic-gateway-architecture-json.js',
    'ext/infographic/infographic-request-response-pipeline-json.js',
    'ext/infographic/infographic-http-deployment-architecture-json.js',
    'ext/infographic/infographic-project-folder-hierarchy-json.js',
    'ext/infographic/infographic-state.js',
    'ext/infographic/infographic-glossary.js',
    'ext/infographic/infographic-canvas.js',
    'ext/infographic/infographic-data.js',
    'ext/infographic/infographic-rendering.js',
    'ext/infographic/infographic-interaction.js',
    'ext/infographic/infographic-main.js'
]

