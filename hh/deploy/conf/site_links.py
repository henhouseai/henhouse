"""
Site links configuration - project-specific navigation menu.
This file defines the site navigation links that appear in the menu sidebar.
"""
from __future__ import annotations
from hh.gateway.gateway import get_gateway


def populate_site_links() -> None:
    """
    Populate site links in the response.
    Groups are created explicitly with names, then links are added to specific groups.
    Passes page_id and link_text - HTML rendering happens in backend.
    """
    gateway = get_gateway()
    if not gateway or not gateway.response:
        return
    
    # Create "home" group with header link
    gateway.response.add_site_link_group('home', 1, 'HOME')
    
    # Add links to "home" group
    gateway.response.add_site_link('home', 234, 'SOURCE CODE')
    gateway.response.add_site_link('home', 28, 'about')
    gateway.response.add_site_link('home', 27, 'INFOGRAPHICS')
    gateway.response.add_site_link('home', 564, 'MCP REQUESTS')

