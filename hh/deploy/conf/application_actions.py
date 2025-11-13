"""
Application action links - admin/root tier CRUD operations.
Generates the FILE, EDIT, IMAGES menu groups for page management.
"""
from __future__ import annotations
from typing import Optional
from hh.gateway.gateway import get_gateway


def populate_application_action_links(page_id: Optional[int] = None) -> None:
    """
    Populate application action links in the response.
    Requires page_id from page context (seed_data).
    """
    gateway = get_gateway()
    if not gateway or not gateway.response:
        return
    
    # Get page ID from seed_data if not provided
    if page_id is None:
        seed_data = gateway.response.get_seed_data()
        if seed_data and isinstance(seed_data, dict):
            page_obj = seed_data.get('page')
            if isinstance(page_obj, dict):
                page_id = page_obj.get('id')
    
    if page_id is None:
        # No page context, can't generate action links
        return
    
    # FILE group
    gateway.response.add_application_action_link('FILE', f'addPage_{page_id}', 'create')
    gateway.response.add_application_action_link('FILE', f'deletePage_{page_id}', 'delete')
    gateway.response.add_application_action_link('FILE', f'copyPage_{page_id}', 'copy')
    gateway.response.add_application_action_link('FILE', f'movePage_{page_id}', 'move')
    
    # EDIT group
    gateway.response.add_application_action_link('EDIT', f'modifyName_{page_id}', 'name')
    gateway.response.add_application_action_link('EDIT', f'editPageText_{page_id}', 'text')
    gateway.response.add_application_action_link('EDIT', f'pageInfo_{page_id}', 'info')
    gateway.response.add_application_action_link('EDIT', f'pageOptions_{page_id}', 'options')
    
    # IMAGES group
    gateway.response.add_application_action_link('IMAGES', f'uploadImage_{page_id}', 'upload')
    gateway.response.add_application_action_link('IMAGES', f'copyImages_{page_id}', 'copy')
    gateway.response.add_application_action_link('IMAGES', f'moveImages_{page_id}', 'move')
    gateway.response.add_application_action_link('IMAGES', f'sortImages_{page_id}', 'sort')

