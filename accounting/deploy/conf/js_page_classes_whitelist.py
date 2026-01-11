"""
JavaScript page class files whitelist for registry generation.
Files listed here will be added to the base JS_PAGE_CLASSES_WHITELIST.
These are filenames from the page-classes/ subfolder.
Paths are relative to page-classes/ folder (e.g., 'custom-page-data.js').
"""
from __future__ import annotations
from typing import List

# Whitelist of page class files that will be registered in page-classes-registry.js
# Files are discovered from ext/deploy/site/js/page-classes/ folder
JS_PAGE_CLASSES_WHITELIST: List[str] = [
    'account-page-data.js',
    'statement-page-data.js',
    'transfer-page-data.js',
    'sale-page-data.js',
    'invoice-page-data.js',
    'fee-page-data.js',
    'fiscal-period-page-data.js',
    'expense-category-page-data.js',
]



