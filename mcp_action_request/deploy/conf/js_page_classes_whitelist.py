# MCP Request module JavaScript page class files whitelist
from typing import List

# Whitelist of page class files that will be registered in page-classes-registry.js
# Files are discovered from both hh/deploy/site/js/page-classes/ and ext/deploy/site/js/page-classes/
JS_PAGE_CLASSES_WHITELIST: List[str] = [
    'mcp-action-request-page-data.js',
]