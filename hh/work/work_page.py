from __future__ import annotations
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import is_error
from hh.page.page import Page
from hh.work.work_page_content import WorkPageContentMixin
from hh.work.work_page_validation import WorkPageValidationMixin

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_work_page_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class WorkPage(WorkPageValidationMixin, WorkPageContentMixin, Page):
    """
    Abstract base class for work entities (work dockets, asks, tasks, steps).
    Provides shared functionality for status, meta, sort_order, and timestamps.
    This class should never be instantiated directly - only inherited from.
    """
    
    def __init__(self, id: int):
        # Call parent constructor first (Page handles gateway, DB load, cache hydration, and automatically extracts metadata fields as attributes)
        super().__init__(id)
        
        # Load and normalize work-specific metadata (moved from _do_init)
        # Page.__init__() already extracted metadata fields (status, meta, sort_order, etc.) as attributes
        # This method normalizes them and sets defaults if needed
        if not is_error() and hasattr(self, 'gateway') and self.gateway and self.gateway.conn:
            # Call the mixin method to load work metadata
            if hasattr(self, '_load_work_metadata'):
                self._load_work_metadata()

