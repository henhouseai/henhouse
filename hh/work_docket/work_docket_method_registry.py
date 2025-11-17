from typing import Dict, Callable, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

_work_docket_mixin_method_registry: Dict[str, Dict[str, Any]] = {}

def register_work_docket_mixin_methods(func: Callable) -> Callable:
    methods = func()
    for method_name, config in methods.items():
        _work_docket_mixin_method_registry[method_name] = config
        log(f"({config['decorator']}) -> {method_name}")
    return func


def get_work_docket_method_registry() -> Dict[str, Dict[str, Any]]:
    return _work_docket_mixin_method_registry.copy()


def get_registry_size() -> int:
    return len(_work_docket_mixin_method_registry)

