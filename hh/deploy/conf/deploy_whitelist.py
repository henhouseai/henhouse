# Deployment cleanup whitelist configuration
from typing import List

# Files and folders to preserve in hh/deploy during deployment cleanup
# These items are temporarily moved out, deploy directory is cleaned, then restored
DEPLOY_WHITELIST: List[str] = [
    'cache',      # Cache cleanup registry and utilities
    'conf',       # Configuration whitelists (CSS/JS includes)
    'utils.py'    # General deployment utilities (used by cache and other modules)
]

# Flask app source file (deployed with tier-specific modifications)
FLASK_APP_SOURCE: str = 'hh/deploy/flask/app.py'

# Top-level project files to deploy into /srv/{project}
# This lets us manage subprocess entrypoints (etc.) declaratively
EXTRA_DEPLOY_FILES: List[str] = [
    'hh/deploy/flask/http_client.py',
    'hh/deploy/flask/mcp_client.py',
]

