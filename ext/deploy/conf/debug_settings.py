"""
Debug System Configuration

This file configures debug system behavior including:
- Which tier levels are allowed to use debug flags
- Default values for trace/log/debug modes
- Default filter values (whitelist, graylist, blacklist, debug-limit)

If this file doesn't exist, the system defaults to allowing debug at all tiers
with the hard-coded defaults from hh/gateway/registry/debug.py.
"""
from __future__ import annotations
from typing import List

# Tier levels allowed to activate debug flags
# 1 = guest, 2 = verified, 3 = admin, 4 = root
# Example: [3, 4] means only admin and root can use debugger
# Example: [1, 2, 3, 4] means all tiers can use debugger
ALLOWED_TIERS: List[int] = [3, 4]

# Default debug mode states (enabled/disabled by default)
# These are used during request parsing if no flags are specified
DEFAULT_USE_TRACE: bool = True
DEFAULT_USE_LOG: bool = True
DEFAULT_USE_DEBUG: bool = True

# Default filter values
# Whitelist: patterns to include (["*"] means include everything)
DEFAULT_WHITELIST: List[str] = ["*"]

# Graylist: file patterns to include ([] means include all files)
DEFAULT_GRAYLIST: List[str] = []

# Blacklist: patterns to exclude
DEFAULT_BLACKLIST: List[str] = []

# Debug limit: max messages per folder/file/function combination
DEFAULT_DEBUG_LIMIT: int = 10
