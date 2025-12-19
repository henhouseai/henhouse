"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                     Line 50
_get_child_row_field_type()     Line 55
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
def _initialize_step_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('step')
class Step(WorkPage):
    """
    A derived WorkPage class for steps.
    Extends WorkPage with step specific functionality.
    Steps can only be inside tasks and are leaf nodes (no work page children).
    """
    
    def __init__(self, id: int):
        """Initialize Step by calling parent constructor."""
        # Call parent constructor (WorkPage initializes status, meta, sort_order, timestamps)
        super().__init__(id)
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Steps allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Steps allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Steps do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Steps are leaf nodes - cannot contain work page children."""
        # Steps don't contain other work pages, but might allow regular pages
        # For now, we'll disallow all work page types
        work_page_types = ['work_docket', 'ask', 'task', 'step']
        return target_class not in work_page_types
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Steps can only be inside tasks."""
        return parent_class == 'task'
    
    def _get_child_row_field_type(self) -> str:
        """Return field type based on status for step rows."""
        status = self.status if hasattr(self, 'status') else 'todo'
        return f'step_{status}'
