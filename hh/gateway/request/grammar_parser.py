from __future__ import annotations
from typing import List, Optional
from hh.gateway.request.tokenizer import tokenize, TokenizationError
from hh.gateway.request.parser import parse, GrammarError
from hh.gateway.request.semantics import build_request
from hh.gateway.request.request import Request
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

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
        parsed = parse(tokens)  # May return partial result on error
        request = Request(argv, skip_parse=True)  # Skip parse to avoid circular call
        build_request(parsed, request)  # Will work with partial results
        return request
    except TokenizationError as e:
        report_error("request", f"Tokenization error: {e}")
        return None
    except GrammarError as e:
        # This shouldn't happen now since parse() returns partial results instead of raising
        # But keep it for safety
        report_error("request", f"Grammar error: {e}")
        return None
    except Exception as e:
        report_error("request", f"Unexpected error during parsing: {e}")
        return None
