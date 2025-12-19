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
from hh.work.work_page import WorkPage
from hh.page.page_class_registry import register_page_class

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
    
    def _get_child_row_field_type(self) -> str:
        """Return field type based on status for task rows."""
        status = self.status if hasattr(self, 'status') else 'todo'
        return f'task_{status}'
