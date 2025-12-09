from __future__ import annotations
import importlib
import threading
import inspect
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, List, Callable, Dict, Any
from hh.gateway.debug.debug_filters import FilterMixin

_SAFE_MODE_ATTR = "_gateway_safe_mode_depth"
_SAFE_DEBUG_ATTR = "_gateway_safe_debug_instance"
_tls = threading.local()
_DEBUG_MODULE_PATH: Optional[str] = "hh.gateway.debug.debug_table"

_use_trace = False
_use_log = False
_use_debug = False

_debug_init_functions: List[Callable] = []
_initialized_functions: set = set()
_initialized = False
_DEBUG_REGISTRY_PRINTS = False

def debug_print(message: str) -> None:
    """Debug print function that can be easily enabled/disabled"""
    # Uncomment the next line to enable debug prints
    # print(f"DEBUG: {message}")
    pass

class SharedDebugDataStore(FilterMixin):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self.captured_data: List[Any] = []
        self._next_index: int = 0
        self._module_colors: Dict[str, int] = {}
        self._filename_colors: Dict[str, int] = {}
        self._function_colors: Dict[str, int] = {}
        self._module_color_index: int = 0
    
    def capture(self, message: str, level: int) -> None:
        with self._lock:
            try:
                frame = inspect.currentframe()
                if frame:
                    frame = frame.f_back
                if frame:
                    frame = frame.f_back
                if not frame:
                    raise RuntimeError("Unable to resolve caller frame")
                calling_file = frame.f_code.co_filename
                calling_function = frame.f_code.co_name
                filename = os.path.basename(calling_file)
                function_name = calling_function
                current_file = Path(calling_file).resolve()
                full_module = str(current_file)
                from hh.gateway.debug.debug_safe import trim_document_root
                module = trim_document_root(full_module)
                folder = str(Path(module).parent).rstrip('/') + '/'
                from hh.gateway.debug.debug_safe import DebugEntry
                entry = DebugEntry(
                    index=self._next_index,
                    timestamp=time.time(),
                    level=level,
                    message=message,
                    function_name=function_name,
                    filename=filename,
                    folder=folder
                )
                self.captured_data.append(entry)
                self._next_index += 1
            except Exception:
                from hh.gateway.debug.debug_safe import DebugEntry
                entry = DebugEntry(
                    index=self._next_index,
                    timestamp=time.time(),
                    level=level,
                    message=message,
                    function_name="unknown",
                    filename="unknown",
                    folder="unknown"
                )
                self.captured_data.append(entry)
                self._next_index += 1
    
    def clear_processed_data(self) -> None:
        with self._lock:
            self.captured_data.clear()
            self.clear_combinations()
            self._module_colors.clear()
            self._filename_colors.clear()
            self._function_colors.clear()
            self._module_color_index = 0

_shared_debug_store = SharedDebugDataStore()

def _debug_print(message: str) -> None:
    if _DEBUG_REGISTRY_PRINTS:
        print(message)

def _initialize_single_debug_func(func: Callable, module_name: str, function_name: str, auto_init: bool = False) -> bool:
    func_id = f"{module_name}.{function_name}"
    if func_id in _initialized_functions:
        return False
        
    try:
        prefix = "Auto-initializing" if auto_init else "Initializing debug module"
        _debug_print(f"[DEBUG_REGISTRY] {prefix}: {module_name}.{function_name}")
        func()
        _initialized_functions.add(func_id)
        success_prefix = "Successfully auto-initialized" if auto_init else "Successfully initialized"
        _debug_print(f"[DEBUG_REGISTRY] {success_prefix}: {module_name}.{function_name}")
        return True
    except Exception as e:
        fail_prefix = "Failed to auto-initialize" if auto_init else "Failed to initialize debug module"
        _debug_print(f"[DEBUG_REGISTRY] {fail_prefix} {module_name}.{function_name}: {e}")
        return False

def register_debug_init(func: Callable) -> Callable:
    module_name = func.__module__ if hasattr(func, '__module__') else 'unknown'
    function_name = func.__name__ if hasattr(func, '__name__') else 'unknown'
    _debug_print(f"[DEBUG_REGISTRY] Registering debug init function: {module_name}.{function_name}")
    _debug_init_functions.append(func)
    _debug_print(f"[DEBUG_REGISTRY] Total registered debug init functions: {len(_debug_init_functions)}")
    
    if _initialized:
        _initialize_single_debug_func(func, module_name, function_name, auto_init=True)
    
    return func

def initialize_debug_modules() -> None:
    global _initialized
    uninitialized_count = len(_debug_init_functions) - len(_initialized_functions)
    
    if uninitialized_count == 0:
        _debug_print(f"[DEBUG_REGISTRY] No uninitialized modules found")
        return
        
    _debug_print(f"[DEBUG_REGISTRY] Initializing {uninitialized_count} uninitialized debug modules")
    
    newly_initialized = 0
    for i, func in enumerate(_debug_init_functions):
        module_name = func.__module__ if hasattr(func, '__module__') else 'unknown'
        function_name = func.__name__ if hasattr(func, '__name__') else 'unknown'
        _debug_print(f"[DEBUG_REGISTRY] Initializing debug module {newly_initialized+1}/{uninitialized_count}: {module_name}.{function_name}")
        if _initialize_single_debug_func(func, module_name, function_name, auto_init=False):
            newly_initialized += 1
    
    _initialized = True
    _debug_print(f"[DEBUG_REGISTRY] Completed initialization of {newly_initialized} debug modules (total initialized: {len(_initialized_functions)})")

def get_debug_init_count() -> int:
    return len(_debug_init_functions)

def _resolve_get_debug():
    try:
        if not _DEBUG_MODULE_PATH:
            return None
        module = importlib.import_module(_DEBUG_MODULE_PATH)
    except Exception:
        return None
    return getattr(module, "get_debug", None)

def set_debug_backend(system: str) -> None:
    global _DEBUG_MODULE_PATH
    if not system or system == "none":
        _DEBUG_MODULE_PATH = None
        return
    _DEBUG_MODULE_PATH = f"hh.gateway.debug.debug_{system}"

def resolve_get_debug_for(system: str):
    try:
        if not system or system == "none":
            return None
        module = importlib.import_module(f"hh.gateway.debug.debug_{system}")
        return getattr(module, "get_debug", None)
    except Exception:
        return None

def _get_depth() -> int:
    return getattr(_tls, _SAFE_MODE_ATTR, 0)

def _set_depth(depth: int) -> None:
    setattr(_tls, _SAFE_MODE_ATTR, depth)

def _get_safe_debug():
    result = getattr(_tls, _SAFE_DEBUG_ATTR, None)
    debug_print(f"_get_safe_debug() - result is None: {result is None}")
    return result

def _set_safe_debug(debug_instance) -> None:
    setattr(_tls, _SAFE_DEBUG_ATTR, debug_instance)

def is_safe_mode() -> bool:
    return _get_depth() > 0

@contextmanager
def safe_mode() -> Iterator[None]:
    depth = _get_depth()
    debug_print(f"safe_mode() - current depth: {depth}")
    _set_depth(depth + 1)
    safe_debug = None
    if depth == 0:
        debug_print(f"safe_mode() - creating safe_debug instance")
        try:
            from hh.gateway.debug.debug_safe import get_debug as get_safe_debug
            debug_print(f"safe_mode() - imported get_safe_debug")
            safe_debug = get_safe_debug()
            debug_print(f"safe_mode() - got safe_debug instance: {safe_debug is not None}")
            main_debug = _resolve_debug_obj()
            debug_print(f"safe_mode() - got main_debug: {main_debug is not None}")
            if main_debug is not None:
                safe_debug.set_whitelist(main_debug.whitelist)
                safe_debug.set_graylist(main_debug.graylist)
                safe_debug.set_blacklist(main_debug.blacklist)
                safe_debug.set_summary_limit(main_debug.summary_limit)
                # Note: set_min_level doesn't exist in FilterMixin, skipping
                debug_print(f"safe_mode() - configured safe_debug")
            _set_safe_debug(safe_debug)
            debug_print(f"safe_mode() - stored safe_debug in thread local")
        except Exception as e:
            debug_print(f"safe_mode() - exception creating safe_debug: {e}")
            pass
    try:
        yield
    finally:
        depth = _get_depth() - 1
        if depth <= 0:
            depth = 0
            _set_safe_debug(None)
        _set_depth(depth)

def trace_in() -> None:
	_shared_debug_store.capture("ENTER", 1)

def trace_out() -> None:
    _shared_debug_store.capture("EXIT", 2)

def log(message: str) -> None:
    _shared_debug_store.capture(message, 3)

def debug(message: str) -> None:
    _shared_debug_store.capture(message, 4)

def warn(message: str) -> None:
    _shared_debug_store.capture(message, 5)

def _resolve_debug_obj():
    get_debug = _resolve_get_debug()
    if get_debug is None:
        return None
    try:
        return get_debug()
    except Exception:
        return None

def set_debug_min_level(level: int) -> bool:
    if is_safe_mode():
        return False
    debug_obj = _resolve_debug_obj()
    if not debug_obj:
        return False
    debug_obj.set_min_level(level)
    return True

def set_debug_summary_limit(limit: int) -> bool:
    if is_safe_mode():
        return False
    debug_obj = _resolve_debug_obj()
    if not debug_obj:
        return False
    debug_obj.set_summary_limit(limit)
    return True

def set_debug_whitelist(values: list[str]) -> bool:
    if is_safe_mode():
        return False
    debug_obj = _resolve_debug_obj()
    if not debug_obj:
        return False
    debug_obj.set_whitelist(values)
    return True

def set_debug_graylist(values: list[str]) -> bool:
    if is_safe_mode():
        return False
    debug_obj = _resolve_debug_obj()
    if not debug_obj:
        return False
    debug_obj.set_graylist(values)
    return True

def set_debug_blacklist(values: list[str]) -> bool:
    if is_safe_mode():
        return False
    debug_obj = _resolve_debug_obj()
    if not debug_obj:
        return False
    debug_obj.set_blacklist(values)
    return True

def get_safe_debug_output() -> str:
    safe_debug = _get_safe_debug()
    debug_print(f"get_safe_debug_output - safe_debug is None: {safe_debug is None}")
    if safe_debug is None:
        return ""
    try:
        # Check what data the safe debug instance sees
        shared_data = _shared_debug_store.captured_data
        debug_print(f"get_safe_debug_output - shared_data length: {len(shared_data)}")
        result = safe_debug.render()
        debug_print(f"get_safe_debug_output - render result length: {len(result) if result else 0}")
        return result
    except Exception as e:
        import traceback
        print(f"DEBUG: get_safe_debug_output - exception: {e}")
        print(f"DEBUG: get_safe_debug_output - traceback: {traceback.format_exc()}")
        return ""

def set_trace_flags(use_trace: bool = False, use_log: bool = False, use_debug: bool = False) -> None:
    global _use_trace, _use_log, _use_debug
    _use_trace = use_trace
    _use_log = use_log
    _use_debug = use_debug

def get_trace_in(debug_enabled: bool = True):
    if not debug_enabled or not _use_trace:
        def noop_trace_in(message=None): pass
        return noop_trace_in
    return trace_in

def get_trace_out(debug_enabled: bool = True):
    if not debug_enabled or not _use_trace:
        def noop_trace_out(message=None): pass
        return noop_trace_out
    return trace_out

def get_log(debug_enabled: bool = True):
    if not debug_enabled or not _use_log:
        def noop_log(message): pass
        return noop_log
    return log

def get_debug(debug_enabled: bool = True):
    if not debug_enabled or not _use_debug:
        def noop_debug(message): pass
        return noop_debug
    return debug

def get_warn(debug_enabled: bool = True):
    return warn

def get_shared_debug_store():
    """Get the shared debug data store"""
    return _shared_debug_store

def set_shared_debug_whitelist(values: list[str]) -> bool:
    _shared_debug_store.set_whitelist(values)
    return True

def set_shared_debug_graylist(values: list[str]) -> bool:
    _shared_debug_store.set_graylist(values)
    return True

def set_shared_debug_blacklist(values: list[str]) -> bool:
    _shared_debug_store.set_blacklist(values)
    return True

def set_shared_debug_summary_limit(limit: int) -> bool:
    _shared_debug_store.set_summary_limit(limit)
    return True

__all__ = [
    "register_debug_init",
    "initialize_debug_modules",
    "get_debug_init_count",
    "safe_mode",
    "is_safe_mode",
    "trace_in",
    "trace_out",
    "log",
    "debug",
    "warn",
    "set_debug_backend",
    "resolve_get_debug_for",
    "set_debug_min_level",
    "set_debug_summary_limit",
    "set_debug_whitelist",
    "set_debug_graylist",
    "set_debug_blacklist",
    "set_shared_debug_whitelist",
    "set_shared_debug_graylist",
    "set_shared_debug_blacklist",
    "set_shared_debug_summary_limit",
    "get_safe_debug_output",
    "set_trace_flags",
    "get_trace_in",
    "get_trace_out",
    "get_log",
    "get_debug",
    "get_warn",
    "get_shared_debug_store",
]