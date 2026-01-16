# nginx_flask module deployment configuration
from typing import List

# Files and folders to preserve during deployment cleanup
# Full root-level paths for this module
DEPLOY_WHITELIST: List[str] = [
    'nginx_flask/deploy/conf',  # Configuration files
]

# Relative paths to preserve in this module's deploy directory during cleanup
MODULE_DEPLOY_WHITELIST: List[str] = [
    'conf',  # Configuration files
]

# Client files deployed to /srv/{project}
CLIENT_WHITELIST: List[str] = [
    'hh/deploy/flask/http_client.py',
    'hh/deploy/flask/mcp_client.py',
    'hh/deploy/flask/api_client.py',
    'hh/deploy/flask/download_client.py',
]

# App source templates with (app_name, source_path) tuples
APP_WHITELIST: List[tuple] = [
    ('flask', 'hh/deploy/flask/app.py'),
    ('media', 'hh/deploy/flask/media_server.py'),
]