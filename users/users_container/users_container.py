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
def _initialize_users_container_debug():
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

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return section header links for users containers."""
        return ['Users Containers']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, List[Any]]:
        """Return query for getting UsersContainer children, ordered by name."""
        query = """
            SELECT id, name, link, class, visibility, last_modified, username, comments
            FROM pages
            WHERE parent = %s AND class = 'users_container'
            ORDER BY name
        """
        return query, [parent_id]

    def _get_child_row_field_type(self) -> str:
        """Return field type for container in table displays."""
        return 'users_container'

    @staticmethod
    def getChildrenOf(parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """Return users_container children of a parent page."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Use UsersContainer's _get_children_query method
        query, params = UsersContainer._get_children_query(parent_id)
        results = gateway.conn.read(query, params)
        children_data = []

        if view_type == 'table':
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        child_data['field_type'] = child_page._get_child_row_field_type()
                        child_data['_format'] = 'table'
                        children_data.append(child_data)
        else:  # view_type == 'tile'
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        display_name = child_page._get_display_name()
                        child_data['display_name'] = display_name
                        images_data = child_page.get_images_data()
                        if images_data and len(images_data) > 0:
                            child_data['images'] = [images_data[0]]
                        else:
                            child_data['images'] = []
                        child_data['_format'] = 'tile'
                        children_data.append(child_data)

        return children_data
