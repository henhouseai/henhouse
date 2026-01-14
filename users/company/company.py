from __future__ import annotations
from typing import Dict, Any, List, Optional
from users.user.user import UserPage
from hh.page.page_class_registry import register_page_class
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_company_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('company')
class CompanyPage(UserPage):
    """
    Page class for company/business accounts.

    Extends UserPage with "Instagram-style upgrade to business account" pattern.
    Inherits all UserPage behavior and validation rules.

    Additional metadata fields (extracted automatically by Page.__init__):
    - company_name: Official company name
    - tax_id: Tax identification number
    - business_type: Type of business
    - (other company-specific fields as needed)
    """

    def __init__(self, id: int):
        """Initialize CompanyPage by calling parent constructor."""
        super().__init__(id)

    # Inherits all validation methods from UserPage:
    # - allow_null_names() = False (must have username)
    # - allow_duplicate_names() = False (unique usernames)
    # - auto_link_name() = True (username becomes URL)
    # - allow_inside_of() restricts to users_container

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return section header links for company pages."""
        return ['Companies']

    def _get_child_row_field_type(self) -> str:
        """Return field type for company pages in table displays."""
        return 'company'

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, List[Any]]:
        """Return query for getting CompanyPage children, ordered by name."""
        query = """
            SELECT id, name, link, class, visibility, last_modified, username, comments
            FROM pages
            WHERE parent = %s AND class = 'company'
            ORDER BY name
        """
        return query, [parent_id]

    @staticmethod
    def getChildrenOf(parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """Return CompanyPage children of a parent page."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Use CompanyPage's _get_children_query method
        query, params = CompanyPage._get_children_query(parent_id)
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
        Return display name for the company.
        Uses company_name metadata if available, falls back to username.
        """
        # Check if company_name was extracted from metadata
        if hasattr(self, 'company_name') and self.company_name:
            return self.company_name
        # Fall back to UserPage display name logic
        return super()._get_display_name()
