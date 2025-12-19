"""
User info display - shows login information for admin/root tiers.
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from hh.gateway.gateway import get_gateway

if TYPE_CHECKING:
    from hh.gateway.response.response_http import ResponseHTTP


def populate_user_info(username: Optional[str] = None) -> None:
    """
    Populate user info in the response.
    If username not provided, attempts to get from DSN or seed_data.
    """
    gateway = get_gateway()
    if not gateway or not gateway.response:
        return
    
    # Type check - set_user_info is only available on ResponseHTTP
    from hh.gateway.response.response_http import ResponseHTTP
    if not isinstance(gateway.response, ResponseHTTP):
        return
    
    # Get username from seed_data if not provided
    if username is None:
        seed_data = gateway.response.get_seed_data()
        if seed_data and isinstance(seed_data, dict):
            # Could get from page context or other seed data
            username = "user"  # Placeholder for now
    
    if not username:
        username = "user"
    
    gateway.response.set_user_info(username)

