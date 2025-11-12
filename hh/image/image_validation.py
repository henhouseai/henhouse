from typing import Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_method_registry import register_image_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_image_validation_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_image_mixin_methods
def _register_validation_methods():
    return {
        'validate_caption': {'mixin_method': '_validate_caption', 'decorator': 'read'},
    }

class ImageValidationMixin:
    
    def _validate_caption(self, caption: str) -> bool:
        trace_in()
        log(f"Validating caption: '{caption}' for image {self.id}")
        if len(caption) > 255:
            warn(f"Caption too long: {len(caption)} characters (max 255)")
            log(f"Validation failed: caption too long ({len(caption)} chars)")
            trace_out()
            return False
        if caption and caption.isdigit():
            warn("Caption cannot be all digits")
            log("Validation failed: caption is all digits")
            trace_out()
            return False
        if any(char in caption for char in ['{', '}', '[', ']', ':']):
            warn(f"Caption contains illegal characters: {caption}")
            log("Validation failed: illegal characters")
            trace_out()
            return False
        log(f"Caption validation successful for '{caption}'")
        trace_out()
        return True
