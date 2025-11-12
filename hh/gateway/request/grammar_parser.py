from __future__ import annotations
from typing import List, Optional
from hh.gateway.request.tokenizer import tokenize, TokenizationError
from hh.gateway.request.parser import parse, GrammarError
from hh.gateway.request.semantics import build_request
from hh.gateway.request.request import Request
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

def parse_request(argv: List[str]) -> Optional[Request]:
    try:
        tokens = tokenize(argv)
        parsed = parse(tokens)
        request = Request(argv)
        build_request(parsed, request)
        return request
    except TokenizationError as e:
        return None
    except GrammarError as e:
        return None
    except Exception as e:
        return None
