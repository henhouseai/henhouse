"""
Upgrade preserve configuration.
Files listed here will be preserved from hh_backup/ during upgrades.
Paths are relative to project root (e.g., "hh/gateway/custom.py").
Use sparingly - preserved files may become incompatible with new Henhouse versions.
"""
from __future__ import annotations
from typing import List

# Files in hh/ to preserve on upgrade (paths relative to project root)
UPGRADE_PRESERVE: List[str] = [
    # Example: 'hh/gateway/custom.py',
    'accounting.md',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/account-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/fee-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/expense-category-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/fiscal-period-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/invoice-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/sale-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/statement-page-data.js',
	'hh/deploy/site/js/ext/deploy/site/ts/page-classes/transfer-page-data.js',
]


