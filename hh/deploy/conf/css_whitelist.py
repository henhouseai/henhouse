# CSS file whitelist for site deployment
# Files listed here will be deployed to /srv/{project_name}/site/css/
# Paths are relative to project root (above hh/ folder)
from typing import List

# CSS files that are always included on every page
CSS_ALWAYS_INCLUDE: List[str] = [
    'hh/deploy/site/css/site.css',
    'hh/deploy/site/css/ansi-colors.css',
    'hh/deploy/site/css/tables.css',
    'hh/deploy/site/css/pygments.css',
]

# Full whitelist of all CSS files that can be included via gateway.add_css_link()
CSS_WHITELIST: List[str] = [
    # CSS files from hh/deploy/site folder
    'hh/deploy/site/css/site.css',
    'hh/deploy/site/css/ansi-colors.css',
    'hh/deploy/site/css/tables.css',
    'hh/deploy/site/css/pygments.css',
    # Infographic CSS files
    'hh/deploy/site/infographic/infographic-viewer.css'
]

