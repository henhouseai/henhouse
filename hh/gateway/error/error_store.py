from __future__ import annotations
import threading
from typing import List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
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

class ErrorType(Enum):
    REQUEST = "request"
    REGISTRY = "registry" 
    ACTION = "action"
    BACKEND = "backend"
    DEBUG = "debug"
    CONNECTION = "connection"
    JSON = "json"
    SYNTAX = "syntax"
    LINK_RESOLUTION = "link_resolution"
    CACHE_REFRESH = "cache_refresh"

@dataclass
class ErrorEntry:
    error_type: ErrorType
    content: Union[str, Dict[str, Any]]
    timestamp: float = None

class GlobalErrorStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._errors: List[ErrorEntry] = []
    
    def add_error(self, error_type: str, content: Union[str, Dict[str, Any]]):
        with self._lock:
            trace_in()
            import time
            log(f"Adding error to global store - type: {error_type}, content: {content}")
            try:
                error_type_enum = ErrorType(error_type)
            except ValueError:
                warn(f"Unknown error type '{error_type}', defaulting to REGISTRY")
                error_type_enum = ErrorType.REGISTRY
            error_entry = ErrorEntry(
                error_type=error_type_enum,
                content=content,
                timestamp=time.time()
            )
            self._errors.append(error_entry)
            log(f"Error added to global store. Total errors now: {len(self._errors)}")
            trace_out()
    
    def get_errors(self, error_type: str = None) -> List[ErrorEntry]:
        with self._lock:
            trace_in()
            log(f"Getting errors from global store - type filter: {error_type}, total errors: {len(self._errors)}")
            if error_type:
                try:
                    error_type_enum = ErrorType(error_type)
                    filtered = [e for e in self._errors if e.error_type == error_type_enum]
                    log(f"Filtered errors for type {error_type}: {len(filtered)}")
                    trace_out()
                    return filtered
                except ValueError:
                    warn(f"Unknown error type '{error_type}' in get_errors")
                    trace_out()
                    return []
            log(f"Returning all {len(self._errors)} errors")
            trace_out()
            return self._errors.copy()
    
    def has_errors(self, error_type: str = None) -> bool:
        with self._lock:
            trace_in()
            #log(f"Checking for errors - type filter: {error_type}, total errors: {len(self._errors)}")
            if error_type:
                try:
                    error_type_enum = ErrorType(error_type)
                    has_errors = any(e.error_type == error_type_enum for e in self._errors)
                    if has_errors:
                        log(f"Has errors of type {error_type}: {has_errors}")
                    trace_out()
                    return has_errors
                except ValueError:
                    warn(f"Unknown error type '{error_type}' in has_errors")
                    trace_out()
                    return False
            has_any_errors = len(self._errors) > 0
            if has_any_errors:
                log(f"Has any errors: {has_any_errors}")
            trace_out()
            return has_any_errors
    
_global_error_store = GlobalErrorStore()

def report_error(error_type: str, content: Union[str, Dict[str, Any]]):
    trace_in()
    _global_error_store.add_error(error_type, content)
    trace_out()

def is_error(error_type: str = None) -> bool:
    trace_in()
    result = _global_error_store.has_errors(error_type)
    trace_out()
    return result

def get_errors(error_type: str = None) -> List[ErrorEntry]:
    trace_in()
    result = _global_error_store.get_errors(error_type)
    trace_out()
    return result

def get_error_count(error_type: str = None) -> int:
    trace_in()
    errors = _global_error_store.get_errors(error_type)
    trace_out()
    return len(errors)

def get_global_error_store():
    return _global_error_store
