# JavaScript file whitelist for site deployment
# Files listed here will be deployed to /srv/{project_name}/site/js/
# Paths are relative to project root (above hh/ folder)
from typing import List

# JavaScript files that are always included on every page
JS_ALWAYS_INCLUDE: List[str] = [
    'hh/deploy/site/js/hh/deploy/site/ts/seed.js',
    'hh/deploy/site/js/hh/deploy/site/ts/rpc-client.js',
    'hh/deploy/site/js/hh/deploy/site/ts/app.js',
]

# Full whitelist of all JS files that can be included via gateway.add_js_link()
# Can include both individual files and folders (folders will deploy all .js files recursively, flattened)
JS_WHITELIST: List[str] = [
    'hh/deploy/site/js',
]

