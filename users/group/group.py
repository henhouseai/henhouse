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
def _initialize_group_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('group')
class GroupPage(Page):
    """
    Page class for system-wide groups (admins, moderators, etc.).

    Groups have unique names that become their URLs.
    They can only be created inside groups_container pages.

    Metadata fields (extracted automatically by Page.__init__):
    - description: Group description/purpose
    - (other group-specific fields as needed)
    """

    def __init__(self, id: int):
        """Initialize GroupPage by calling parent constructor."""
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """Groups must have names."""
        return False

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Group names must be unique."""
        return False

    @classmethod
    def auto_link_name(cls) -> bool:
        """Group name becomes the URL (global link)."""
        return True

    def allow_class_inside(self, target_class: str) -> bool:
        """Groups can contain standard page types."""
        return True

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Groups can only be created inside groups_container."""
        return parent_class == 'groups_container'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return section header links for group pages."""
        return ['Groups']

    def _get_child_row_field_type(self) -> str:
        """Return field type for group pages in table displays."""
        return 'group'

    def _get_display_name(self) -> str:
        """
        Return display name for the group.
        Uses name field (group name).
        """
        if self.name:
            return self.name
        return f"Group {self.id}"
