# Python file whitelist for site deployment
# Files listed here will be deployed to /srv/{project_name}/site/py/
# Paths are relative to project root (above hh/ folder)
from typing import List

PY_WHITELIST: List[str] = [
    # Python decorator files
    'hh/deploy/site/infographic/infographic.py',
]

