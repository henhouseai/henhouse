import json
import math
from typing import Dict, Any, Union
from hh.tp.tp_decorator_registry import register_tp_decorator
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


@register_tp_decorator('pi')
def pi_decorator(text: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    precision = kwargs.get('arg0', 5)
    try:
        precision_int = int(precision)
    except Exception:
        precision_int = 5
    value = f"{math.pi:.{precision_int}f}"
    return {
        "type": "custom",
        "value": value
    }


@register_tp_decorator('echo')
def echo_decorator(text: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    value = str(kwargs.get('arg0', text))
    return {
        "type": "custom",
        "value": value
    }
