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
	'source-code-file-page-data.js',
    # Example: 'custom-page-data.js',
]



