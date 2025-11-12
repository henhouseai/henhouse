# Miscellaneous file whitelist for site deployment
# Files listed here will be deployed to /srv/{project_name}/site/ (top level)
# Paths are relative to project root (above hh/ folder)
from typing import List

MISC_WHITELIST: List[str] = [
    # Miscellaneous files from hh/deploy/site folder
    'hh/deploy/site/favicon.ico',
    'hh/deploy/site/favicon-16x16.png',
    'hh/deploy/site/favicon-32x32.png',
    'hh/deploy/site/apple-touch-icon.png',
    'hh/deploy/site/android-chrome-512x512.png',
    'hh/deploy/site/site.webmanifest'
]

