# Work module JavaScript page class files whitelist
from typing import List

# Whitelist of page class files that will be registered in page-classes-registry.js
# Files are discovered from both hh/deploy/site/js/page-classes/ and ext/deploy/site/js/page-classes/
JS_PAGE_CLASSES_WHITELIST: List[str] = [
    'ask-page-data.js',
    'step-page-data.js',
    'task-page-data.js',
    'work-docket-page-data.js',
    'work-page-data.js',
]