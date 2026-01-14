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
def _initialize_subpage_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('subpage')
class SubPage(Page):
    """
    A page class that allows hierarchical URLs without global links.
    Enables tree-structured paths like /alice/projects/project1

    Key differences from base Page:
    - auto_link_name() = False (no global links - found via parent traversal)
    - allow_duplicate_names() = True (allows same names under different parents)
    """

    def __init__(self, id: int):
        """Initialize SubPage by calling parent constructor."""
        # Call parent constructor (Page automatically extracts metadata fields)
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """SubPages require names (for URL segments)."""
        return False

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """SubPages allow duplicate names under different parents."""
        return True

    @classmethod
    def auto_link_name(cls) -> bool:
        """SubPages don't create global links - found via parent traversal."""
        return False

    def allow_class_inside(self, target_class: str) -> bool:
        """SubPages can contain any page type (same as base Page)."""
        return super().allow_class_inside(target_class)

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """SubPages can be inside any page type."""
        return True

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        return ['Sub-Pages']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, List[Any]]:
        """Return query for getting SubPage children, ordered by name."""
        query = """
            SELECT id, name, link, class, visibility, last_modified, username, comments
            FROM pages
            WHERE parent = %s AND class = 'subpage'
            ORDER BY name
        """
        return query, [parent_id]

    def _get_child_row_field_type(self) -> str:
        """Return field type for SubPage children in table displays."""
        return 'subpage'

    @staticmethod
    def getChildrenOf(parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """Return SubPage children of a parent page with proper display names."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Use SubPage's _get_children_query method
        query, params = SubPage._get_children_query(parent_id)
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
                        # Add display_name (derived field) - this is what was missing!
                        display_name = child_page._get_display_name()
                        child_data['display_name'] = display_name
                        # Add first image for tile rendering
                        images_data = child_page.get_images_data()
                        if images_data and len(images_data) > 0:
                            child_data['images'] = [images_data[0]]  # Just first image
                        else:
                            child_data['images'] = []
                        # Add format metadata
                        child_data['_format'] = 'tile'
                        children_data.append(child_data)

        return children_data