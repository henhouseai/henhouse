"""
NGINX/Flask site-specific deployment helpers.

These functions are specific to site deployment operations (HTML, JS, CSS, assets)
and are used by the site deployment hooks but are not hooks themselves.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)

try:
    _initialize_debug()
except:
    pass