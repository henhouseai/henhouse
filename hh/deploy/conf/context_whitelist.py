# Context deployment whitelist configuration
from typing import List

# Context deployment filtering - folders that should be deployed for agent visibility
CONTEXT_WHITELIST: List[str] = [
    'context',      # Documentation and context
    'planning',     # Planning documents
	'hh',           # HH source code
	'hen.ps1',      # Top-level PowerShell script
	'hen.py',       # Top-level Python script
	'stage.ps1',    # Top-level PowerShell staging script
	'stage.py',     # Top-level Python staging script
	'mcp_wrapper.py',  # MCP wrapper script for stdio-to-HTTP bridge
	'README.md',     # Project README
	'LICENSE',      # Project license file
	'requirements.txt',  # Python dependencies
]


