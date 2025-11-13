"""
Site links configuration - project-specific navigation menu.
This file defines the site navigation links that appear in the menu sidebar.
"""
from __future__ import annotations
from typing import List
from hh.gateway.gateway import get_gateway


def populate_site_links() -> None:
    """
    Populate site links in the response.
    Empty string creates a new menu group.
    """
    gateway = get_gateway()
    if not gateway or not gateway.response:
        return
    
    # Site links based on homepage (page 1) children
    gateway.response.add_site_link('<a href="1">HOME</a>')
    gateway.response.add_site_link('')  # New group
    gateway.response.add_site_link('<a href="234">SOURCE CODE</a>')
    gateway.response.add_site_link('<a href="28">about</a>')
    gateway.response.add_site_link('')  # New group
    gateway.response.add_site_link('<a href="27">INFOGRAPHICS</a>')
    gateway.response.add_site_link('')  # New group
    gateway.response.add_site_link('<a href="564">MCP REQUESTS</a>')

