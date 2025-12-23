"""
Site links configuration - project-specific navigation menu.
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
    {
        'group': 'home',
        'header_page_id': 1,
        'header_text': 'HOME',
        'links': [
            {'page_id': 234, 'text': 'SOURCE CODE'},
            {'page_id': 28, 'text': 'about'},
            {'page_id': 27, 'text': 'INFOGRAPHICS'},
            {'page_id': 564, 'text': 'MCP REQUESTS'},
        ]
    },
    {
        'group': 'about',
        'header_page_id': 28,
        'header_text': 'ABOUT',
        'links': [
            {'page_id': 35, 'text': 'pages'},
            {'page_id': 49, 'text': 'flask daemons'},
        ]
    },
    {
        'group': 'source code',
        'header_page_id': 234,
        'header_text': 'SOURCE CODE',
        'links': [
            {'page_id': 535, 'text': 'context'},
            {'page_id': 235, 'text': 'hh'},
        ]
    },
]

