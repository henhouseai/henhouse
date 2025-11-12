
import re
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


@register_tp_decorator('precision')
def precision_decorator(text: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    trace_in()
    precision = kwargs.get('arg0', 2)
    try:
        precision_int = int(precision)
    except Exception:
        precision_int = 2
        warn(f"Invalid precision argument, using default: 2")
    
    # Only handle custom type structures
    if not isinstance(text, dict) or text.get('type') != 'custom':
        warn(f"Precision decorator only works with custom type structures")
        trace_out()
        return text if isinstance(text, dict) else {"type": "custom", "value": ""}
    
    if 'value' not in text:
        warn(f"Custom type missing 'value' field")
        trace_out()
        return text
    
    log(f"Precision decorator found custom type with value: {text['value']}")
    try:
        num_value = float(text['value'])
        formatted_value = f"{num_value:.{precision_int}f}"
        result = {
            "type": "custom",
            "value": formatted_value
        }
        log(f"Precision applied: {text['value']} -> {formatted_value}")
        trace_out()
        return result
    except (ValueError, TypeError):
        warn(f"Could not convert value '{text['value']}' to float")
        trace_out()
        return text


@register_tp_decorator('repeat')
def repeat_decorator(text: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    trace_in()
    count = kwargs.get('arg0', 1)
    separator = kwargs.get('arg1', '')
    try:
        count_int = int(count)
    except Exception:
        count_int = 1
        warn(f"Invalid repeat count argument, using default: 1")
    
    # Only handle custom type structures
    if not isinstance(text, dict) or text.get('type') != 'custom':
        warn(f"Repeat decorator only works with custom type structures")
        trace_out()
        return text if isinstance(text, dict) else {"type": "custom", "value": ""}
    
    if 'value' not in text:
        warn(f"Custom type missing 'value' field")
        trace_out()
        return text
    
    log(f"Repeat decorator found custom type with value: {text['value']}")
    original_value = text['value']
    repeated_value = separator.join([str(original_value)] * count_int)
    result = {
        "type": "custom",
        "value": repeated_value
    }
    log(f"Repeat applied: '{original_value}' x{count_int} -> '{repeated_value}'")
    trace_out()
    return result

