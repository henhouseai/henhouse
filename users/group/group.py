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

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, List[Any]]:
        """Return query for getting GroupPage children, ordered by name."""
        query = """
            SELECT id, name, link, class, visibility, last_modified, username, comments
            FROM pages
            WHERE parent = %s AND class = 'group'
            ORDER BY name
        """
        return query, [parent_id]

    @staticmethod
    def getChildrenOf(parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """Return GroupPage children of a parent page."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Use GroupPage's _get_children_query method
        query, params = GroupPage._get_children_query(parent_id)
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

    def _get_display_name(self) -> str:
        """
        Return display name for the group.
        Uses name field (group name).
        """
        if self.name:
            return self.name
        return f"Group {self.id}"
