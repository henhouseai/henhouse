"""
ExpenseCategory page class for accounting system.
A simple page class with no additional metadata fields.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.page.page import Page
from hh.page.page_registry import get_page
from hh.page.page_class_registry import register_page_class

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_expense_category_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('expenseCategory')
class ExpenseCategory(Page):
    """
    Expense Category page class for organizing invoices by category.
    """
    
    def __init__(self, id: int):
        """Initialize ExpenseCategory by calling parent constructor."""
        super().__init__(id)
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Expense categories do not allow null names."""
        return False
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Expense categories do not allow duplicate names."""
        return False
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Expense categories auto-link names."""
        return True
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Expense categories can only contain invoices."""
        return target_class == 'invoice'
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Expense categories can be inside pages."""
        return parent_class == 'page'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for expense category section headers."""
        return ['Expense Categories']

    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for expense category pages with default table view.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return []

        query, params = cls._get_children_query(parent_id)
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
            log(f"Loaded {len(children_data)} children for class 'expenseCategory' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'expenseCategory' (tile format)")

        trace_out()
        return children_data

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for expense category children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'expenseCategory' ORDER BY name",
            [parent_id]
        )

    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for expense category rows in table view."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
        }
        trace_out()
        return data

    def _get_display_name(self) -> str:
        """Return formatted display name for expense category."""
        if self.name:
            return self.name

        # Format like legacy: just return the name, fallback to base
        return super()._get_display_name()

    def _get_child_row_field_type(self) -> str:
        """Return field type for expense category rows."""
        return 'expenseCategory'

    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """ExpenseCategory keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge

