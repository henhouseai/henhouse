from __future__ import annotations
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_source_code_file_validation_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class SourceCodeFileValidationMixin:
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Source code files allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Source code files allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Source code files do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Source code files cannot contain any child pages."""
        return False
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Source code files can only be inside pages."""
        return parent_class == 'page'

