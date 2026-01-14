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
def _initialize_containers_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('users_container')
class UsersContainer(Page):
    """
    Container page for user and company pages.
    Only allows UserPage and CompanyPage children.

    This creates a restricted hierarchy ensuring users/companies
    are only created in designated locations.
    """

    def __init__(self, id: int):
        """Initialize UsersContainer by calling parent constructor."""
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """Containers require names."""
        return False

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Containers allow duplicates (unlikely but allowed)."""
        return True

    @classmethod
    def auto_link_name(cls) -> bool:
        """Containers create global links."""
        return True

    def allow_class_inside(self, target_class: str) -> bool:
        """Only allow user and company pages inside users container."""
        return target_class in ('user', 'company')

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Users containers can be inside any page type."""
        return True

    def _get_child_row_field_type(self) -> str:
        """Return field type for container in table displays."""
        return 'users_container'


@register_page_class('groups_container')
class GroupsContainer(Page):
    """
    Container page for group pages.
    Only allows GroupPage children.

    This creates a restricted hierarchy ensuring groups
    are only created in designated locations.
    """

    def __init__(self, id: int):
        """Initialize GroupsContainer by calling parent constructor."""
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """Containers require names."""
        return False

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Containers allow duplicates (unlikely but allowed)."""
        return True

    @classmethod
    def auto_link_name(cls) -> bool:
        """Containers create global links."""
        return True

    def allow_class_inside(self, target_class: str) -> bool:
        """Only allow group pages inside groups container."""
        return target_class == 'group'

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Groups containers can be inside any page type."""
        return True

    def _get_child_row_field_type(self) -> str:
        """Return field type for container in table displays."""
        return 'groups_container'
