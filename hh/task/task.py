"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                     Line 50
_get_child_row_field_type()     Line 55
_get_children_query()           Line 60
allow_class_inside()            Line 45
allow_duplicate_names()          Line 35
allow_inside_of()               Line 40
allow_null_names()              Line 30
auto_link_name()                Line 38

"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.work.work_page import WorkPage
from hh.page.page_class_registry import register_page_class
from hh.page.page_registry import get_page

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_task_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('task')
class Task(WorkPage):
    """
    A derived WorkPage class for tasks.
    Extends WorkPage with task specific functionality.
    Tasks can only be inside asks and can only contain steps.
    """
    
    def __init__(self, id: int):
        """Initialize Task by calling parent constructor."""
        # Call parent constructor (WorkPage initializes status, meta, sort_order, timestamps)
        super().__init__(id)
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Tasks allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Tasks allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Tasks do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Tasks can only contain step children."""
        return target_class == 'step'
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Tasks can only be inside asks."""
        return parent_class == 'ask'
    
    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Return query for getting task children (steps), ordered by sort_order."""
        return (
            """
            SELECT pages.id
            FROM pages
            WHERE pages.parent = %s
              AND pages.class = 'step'
            ORDER BY COALESCE(
                CAST(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.sort_order')) AS UNSIGNED),
                0
            )
            """,
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """
        Override to query for task pages (not steps) when called from a parent.
        Uses sort_order for ordering.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return []
        
        # Query for task pages (not steps) - this is for finding task children of a parent
        query = """
            SELECT pages.id
            FROM pages
            WHERE pages.parent = %s
              AND pages.class = 'task'
            ORDER BY COALESCE(
                CAST(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.sort_order')) AS UNSIGNED),
                0
            )
        """
        results = gateway.conn.read(query, [parent_id])
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
            log(f"Loaded {len(children_data)} children for class 'task' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'task' (tile format)")
        
        trace_out()
        return children_data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type based on status for task rows."""
        status = self.status if hasattr(self, 'status') else 'todo'
        return f'task_{status}'
