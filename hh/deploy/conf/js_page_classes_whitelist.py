# JavaScript page class files whitelist for registry generation
# Files listed here will be included in the generated page-classes-registry.js
# These are filenames from the page-classes/ subfolder (both hh/ and ext/ sources)
# Paths are relative to page-classes/ folder (e.g., 'source-code-file-page-data.js')
from typing import List

# Whitelist of page class files that will be registered in page-classes-registry.js
# Files are discovered from both hh/deploy/site/js/page-classes/ and ext/deploy/site/js/page-classes/
JS_PAGE_CLASSES_WHITELIST: List[str] = [
    'ask-page-data.js',
    'mcp-action-request-page-data.js',
    'mcp-request-page-data.js',
    'step-page-data.js',
    'task-page-data.js',
    'work-docket-page-data.js',
    'work-page-data.js',
]


