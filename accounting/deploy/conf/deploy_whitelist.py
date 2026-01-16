# accounting module deployment configuration
from typing import List

# Files and folders to preserve during deployment cleanup
# Full root-level paths for this module
DEPLOY_WHITELIST: List[str] = [
    'accounting/deploy/conf',  # Configuration files
    'accounting/deploy/maint', # Maintenance tools
    'accounting/deploy/db',    # Database schema and data
]

# Relative paths to preserve in this module's deploy directory during cleanup
MODULE_DEPLOY_WHITELIST: List[str] = [
    'conf',  # Configuration files
    'maint', # Maintenance tools
    'db',    # Database schema and data
]

# Client files deployed to /srv/{project}
CLIENT_WHITELIST: List[str] = []

# App source templates with (app_name, source_path) tuples
APP_WHITELIST: List[tuple] = []


