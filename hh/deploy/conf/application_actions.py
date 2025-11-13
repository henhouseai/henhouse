"""
Application action links - admin/root tier CRUD operations.
Groups are created explicitly with names, then actions are added to specific groups.
Actions have DOM IDs for JavaScript event handlers (no hrefs).
"""
from __future__ import annotations
from hh.gateway.gateway import get_gateway


def populate_application_action_links(page_id: int = None) -> None:
    """
    Populate application action links in the response.
    Groups are created explicitly with names, then actions are added to specific groups.
    Passes action_id and label - HTML rendering happens in backend.
    """
    gateway = get_gateway()
    if not gateway or not gateway.response:
        return
    
    # Create "test" group with header text
    gateway.response.add_application_action_group('test', 'TEST')
    
    # Add actions to "test" group
    gateway.response.add_application_action_link('test', 'test_one', 'test one')
    gateway.response.add_application_action_link('test', 'test_two', 'test two')
    gateway.response.add_application_action_link('test', 'test_three', 'test three')
    gateway.response.add_application_action_link('test', 'test_four', 'test four')
    gateway.response.add_application_action_link('test', 'test_five', 'test five')
    gateway.response.add_application_action_link('test', 'test_six', 'test six')
    gateway.response.add_application_action_link('test', 'test_seven', 'test seven')

