from __future__ import annotations
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_work_docket_validation_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class WorkDocketValidationMixin:
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Work dockets allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Work dockets allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Work dockets do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Work dockets can contain any child pages."""
        return True
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Work dockets can be inside any page."""
        return True

