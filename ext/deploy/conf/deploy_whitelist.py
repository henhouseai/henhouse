# ext module deployment configuration - extensions to base whitelists
from typing import List

# Files and folders to preserve during deployment cleanup (extensions to base DEPLOY_WHITELIST)
DEPLOY_WHITELIST: List[str] = []

# Client files deployed to /srv/{project} (extensions to base CLIENT_WHITELIST)
CLIENT_WHITELIST: List[str] = []

# App source templates with (app_name, source_path) tuples (extensions to base APP_WHITELIST)
APP_WHITELIST: List[tuple] = []


