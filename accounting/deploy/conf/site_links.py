"""
Site links configuration - project-specific navigation menu.
Groups listed here will be added to the base SITE_LINKS.
This file defines the site navigation links that appear in the menu sidebar.
"""
from __future__ import annotations
from typing import List, Dict, Any

# Site links configuration
# Each entry defines a group with its header (page_id and text) and list of links
# Example structure:
# {
#     'group': 'home',
#     'header_page_id': 1,
#     'header_text': 'HOME',
#     'links': [
#         {'page_id': 234, 'text': 'SOURCE CODE'},
#         {'page_id': 28, 'text': 'about'},
#     ]
# }
SITE_LINKS: List[Dict[str, Any]] = [
    # Example (commented out):
    # {
    #     'group': 'custom',
    #     'header_page_id': 100,
    #     'header_text': 'CUSTOM',
    #     'links': [
    #         {'page_id': 101, 'text': 'custom page'},
    #     ]
    # },
]



