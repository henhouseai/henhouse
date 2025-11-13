"""
Application action links - admin/root tier CRUD operations.
Dummy/test entries for framework testing.
"""
from __future__ import annotations
from hh.gateway.gateway import get_gateway


def populate_application_action_links(page_id: int = None) -> None:
    """
    Populate application action links in the response.
    Dummy/test entries for now.
    """
    gateway = get_gateway()
    if not gateway or not gateway.response:
        return
    
    # Dummy test entries
    gateway.response.add_application_action_link('TEST', 'test_one', 'test one')
    gateway.response.add_application_action_link('TEST', 'test_two', 'test two')
    gateway.response.add_application_action_link('TEST', 'test_three', 'test three')

