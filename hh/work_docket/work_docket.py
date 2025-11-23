from __future__ import annotations
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.work.work_page import WorkPage
from hh.page.page_class_registry import register_page_class
from hh.work_docket.work_docket_content import WorkDocketContentMixin
from hh.work_docket.work_docket_validation import WorkDocketValidationMixin

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_work_docket_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('work_docket')
class WorkDocket(WorkDocketValidationMixin, WorkDocketContentMixin, WorkPage):
    """
    A derived WorkPage class for work dockets.
    Extends WorkPage with work docket specific functionality.
    """
    
    def __init__(self, id: int):
        # Call parent constructor (WorkPage initializes status, meta, sort_order, timestamps)
        super().__init__(id)

