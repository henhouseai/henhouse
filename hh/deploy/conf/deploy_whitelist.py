# Deployment whitelist configuration - base definitions extended by modules
from typing import List

# Files and folders to preserve during deployment cleanup
# Full root-level paths that get aggregated across all modules
DEPLOY_WHITELIST: List[str] = [
    'hh/deploy/cache',
    'hh/deploy/conf',
    'hh/deploy/maint',
    'hh/deploy/deploy_utils.py'
]

# Client files to deploy to /srv/{project} (HTTP clients, maintenance clients, etc.)
# Modules add their own client file paths
CLIENT_WHITELIST: List[str] = []

# App source templates with (app_name, source_path) tuples
# Modules add their own app source definitions
APP_WHITELIST: List[tuple] = []

