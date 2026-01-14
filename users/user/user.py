from __future__ import annotations
from typing import Dict, Any, List, Optional
from hh.page.page import Page
from hh.page.page_class_registry import register_page_class
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_user_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('user')
class UserPage(Page):
    """
    Page class for verified users with ~ pages.

    Users have unique usernames that become their URLs.
    They can only be created inside users_container pages.
    They can contain subpages for hierarchical content (/alice/projects).

    Metadata fields (extracted automatically by Page.__init__):
    - display_name: Display name for the user
    - bio: User biography/description
    - website: User website URL
    - (other user-specific fields as needed)
    """

    def __init__(self, id: int):
        """Initialize UserPage by calling parent constructor."""
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """Users must have usernames."""
        return False

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Usernames must be unique."""
        return False

    @classmethod
    def auto_link_name(cls) -> bool:
        """Username becomes the URL (global link)."""
        return True

    def allow_class_inside(self, target_class: str) -> bool:
        """Users can contain subpages and any other standard page types."""
        return True

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Users can only be created inside users_container."""
        return parent_class == 'users_container'

    def _get_child_row_field_type(self) -> str:
        """Return field type for user pages in table displays."""
        return 'user'

    def _get_display_name(self) -> str:
        """
        Return display name for the user.
        Uses display_name metadata if available, falls back to username (name field).
        """
        # Check if display_name was extracted from metadata
        if hasattr(self, 'display_name') and self.display_name:
            return self.display_name
        # Fall back to username
        if self.name:
            return self.name
        # Last resort
        return f"User {self.id}"
