# Context deployment blacklist configuration
from typing import List

# Context deployment filtering - patterns to ignore during deployment
CONTEXT_BLACKLIST: List[str] = [
    '.git',                # Git repository
    '__pycache__',         # Python cache
    '*.pyc',               # Python compiled files
    '.pytest_cache',       # Test cache
    'node_modules',        # Node modules
    '.env',                # Environment files
    '*.log',                # Log files
    '*-reg.json',          # Registry cache JSON files
    '*.cycle.json',        # Cycle cache JSON files
    'cache.json',          # Cache JSON files
    '*.cache.json',        # Cache JSON files
]
