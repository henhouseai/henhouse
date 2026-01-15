"""
Module Blacklist Configuration

Two-tier blacklist system for excluding modules and specific files from discovery.

Aggregation Model: "Dogpile + Subtraction"
- Whitelists pile additively across hh/ and peer modules
- Blacklists subtract from the combined pile
- Blacklist always wins (if something is both whitelisted and blacklisted, it's excluded)

This file supports:
- MODULE_BLACKLIST: Exclude entire modules by name
- FILE_BLACKLIST: Exclude specific files by path
- Meta-blacklisting: Can blacklist items from any source (hh/, peer modules, ext/)
"""

from typing import List

# Module-level blacklist: Exclude entire modules by name
# Example: ['accounting', 'self_doc'] would exclude all files from these modules
MODULE_BLACKLIST: List[str] = ['accounting', 'puzzle', 'example', 'history']

# File-level blacklist: Exclude specific files by path (relative to project root)
# Example: ['hh/gateway/experimental.py', 'accounting/legacy_reports.py']
FILE_BLACKLIST: List[str] = []
