"""
Application action links - admin/root tier CRUD operations.
Groups listed here will be added to the base APPLICATION_ACTIONS.
Groups are created explicitly with names, then actions are added to specific groups.
Actions have DOM IDs for JavaScript event handlers (no hrefs).
"""
from __future__ import annotations
from typing import List, Dict, Any

# Application action configuration
# Each entry defines a group with its header label and list of actions
# Example structure:
# {
#     'group': 'test',
#     'group_label': 'TEST',
#     'actions': [
#         {'action_id': 'test_one', 'label': 'test one'},
#         {'action_id': 'test_two', 'label': 'test two'},
#     ]
# }
APPLICATION_ACTIONS: List[Dict[str, Any]] = [
    # Example (commented out):
    # {
    #     'group': 'custom',
    #     'group_label': 'CUSTOM',
    #     'actions': [
    #         {'action_id': 'custom_one', 'label': 'custom one'},
    #     ]
    # },
]


