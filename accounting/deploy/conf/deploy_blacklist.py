# accounting module deployment blacklist configuration
# Items listed here will be removed from the corresponding base whitelists
from typing import List

# Files and folders to remove from base DEPLOY_WHITELIST
DEPLOY_WHITELIST: List[str] = []

# Client files to remove from base CLIENT_WHITELIST
CLIENT_WHITELIST: List[str] = []

# App sources to remove from base APP_WHITELIST (by exact tuple match)
APP_WHITELIST: List[tuple] = []


