from __future__ import annotations
import re
from dataclasses import dataclass
from functools import wraps
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional
from hh.gateway.registry.cache import  check_command_exists, check_backend_exists, check_command_in_backend, discover_backend_specific_registrations  # type: ignore[attr-defined]
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.backend import BACKEND_TYPES, BACKEND_DECORATORS, BACKEND_DICTS
from hh.gateway.error.error_store import report_error, is_error

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

# Dynamically generate backend dataclasses
for backend_type in BACKEND_TYPES:
    class_name = f"{backend_type.title()}Info"
    exec(f"""
@dataclass(frozen=True)
class {class_name}:
    function: Callable
""")

# Dynamically generate backend dictionaries
for backend_type in BACKEND_TYPES:
    dict_name = f"{backend_type}s"
    exec(f"{dict_name}: Dict[str, {backend_type.title()}Info] = {{}}")

# Dynamically generate backend decorators
def create_backend_decorator(backend_type: str):
    info_class_name = f"{backend_type.title()}Info"
    dict_name = f"{backend_type}s"
    
    def decorator(name: Optional[str] = None):
        def inner_decorator(func):
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any):
                return func(*args, **kwargs)
            trace_in()
            actual_name = name if name is not None else func.__name__
            info_class = globals()[info_class_name]
            info_instance = info_class(function=wrapper)
            globals()[dict_name][actual_name] = info_instance
            log(f"Registered {backend_type}: {actual_name} -> {func.__module__}.{func.__name__}")
            trace_out()
            return wrapper
        return inner_decorator
    return decorator

# Generate decorator functions
for backend_type in BACKEND_TYPES:
    decorator_name = f"register_{backend_type}"
    exec(f"{decorator_name} = create_backend_decorator('{backend_type}')")

# Create unified backend_handlers structure automatically from BACKEND_TYPES
backend_handlers = {}
for backend_type in BACKEND_TYPES:
    dict_name = f"{backend_type}s"
    backend_handlers[backend_type] = globals()[dict_name]


@dataclass(frozen=True)
class BackendInfo:
    function: Callable

@dataclass(frozen=True)
class CommandInfo:
    function: Callable
    action_args: List[str]

backends: Dict[str, BackendInfo] = {}
commands: Dict[str, CommandInfo] = {}

# Pre-populate backends with predefined types
def backend_stub():
    pass

for backend_type in BACKEND_TYPES:
    backends[backend_type] = BackendInfo(function=backend_stub)

def register_command(name: Optional[str] = None, action_args: Optional[List[str]] = None) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            return func(*args, **kwargs)
        trace_in()
        actual_name = name if name is not None else func.__name__
        log("register_command buffering '%s' from '%s' (action_args=%s)" % (actual_name, func.__module__, action_args))
        command_info = CommandInfo(function=wrapper, action_args=action_args or [])
        commands[actual_name] = command_info
        register_command.commands = dict(commands)  # type: ignore[attr-defined]
        trace_out()
        return wrapper
    return decorator
register_command.commands = {}  # type: ignore[attr-defined]

class CommandRegistry:
    def __init__(self, command: str, backend: str) -> None:
        trace_in()
        self.command = command
        self.backend = backend
        self.matched_backend: Optional[BackendInfo] = None
        self.backend_registration: Optional[Dict[str, Any]] = None
        self.action_cache_data: Optional[Dict[str, Any]] = None
        self.backend_cache_data: Optional[Dict[str, Any]] = None
        self.error_cache_data: Optional[Dict[str, Any]] = None
        if not check_command_exists(command):
            warn(f"Command '{command}' not found in registry")
            report_error("registry", f"Command '{command}' not found in registry")
        if not check_backend_exists(backend):
            warn(f"Backend '{backend}' not found in registry")
        self.backend_registration = check_command_in_backend(command, backend)
        if not self.backend_registration:
            warn(f"Command '{command}' not found in backend '{backend}'")
        
        # Extract handler info if backend_registration exists
        command_name = self.command
        if self.backend_registration and "handlers" in self.backend_registration:
            handler_info = self.backend_registration["handlers"].get(command_name, {})
            if handler_info:
                self.backend_cache_data = handler_info
                log(f"Stored backend handler info for '{command_name}': {handler_info['module']}.{handler_info['function']}")
            else:
                warn(f"No handler found for command '{command_name}' in backend '{backend}' cache")
        
        # Extract error handler info if backend_registration exists
        if self.backend_registration:
            error_handler_info = self.backend_registration.get("error_handler")
            if error_handler_info:
                self.error_cache_data = error_handler_info
        
        self.select_backend()
        self.select_command()
        self.select_error_handler()
        trace_out()

    def select_backend(self) -> None:
        trace_in()
        if self.backend:
            backend = backends.get(self.backend)
            if backend:
                self.matched_backend = backend
                log(f"Found backend '{self.backend}' with function: '{self.matched_backend.function.__module__}.{self.matched_backend.function.__name__}'")
                trace_out()
                return
            warn(f"Requested backend '{self.backend}' not registered")
        trace_out()

    def select_command(self) -> None:
        trace_in()
        if not self.command:
            warn(f"No command specified")
            trace_out()
            return
        
        # Use action cache data to find the action handler (not the delivery backend cache)
        action_registration = check_command_in_backend(self.command, "action")
        if action_registration and "handlers" in action_registration:
            command_name = self.command
            handler_info = action_registration["handlers"].get(command_name, {})
            if handler_info:
                # Just store the cache data - no need for mock objects!
                self.action_cache_data = handler_info
                log(f"Found command '{command_name}' from action cache with function '{handler_info['module']}.{handler_info['function']}'")
                trace_out()
                return
        
        warn(f"No command registration found for '{self.command}'")
        trace_out()

    def select_error_handler(self) -> None:
        trace_in()
        if self.backend and self.backend != "action":
            # Try to discover error handler if not already cached
            if not self.error_cache_data:
                try:
                    # Force discovery of backend-specific registrations
                    registrations = discover_backend_specific_registrations(self.backend, force_regenerate=True)
                    error_handler_info = registrations.get("error_handler")
                    if error_handler_info:
                        self.error_cache_data = error_handler_info
                except Exception as e:
                    warn(f"Error during error handler discovery: {e}")
        trace_out()

    def has_command(self) -> bool:
        return hasattr(self, 'action_cache_data') and self.action_cache_data is not None

    def has_backend(self) -> bool:
        return self.matched_backend is not None

    def has_action_handler(self) -> bool:
        return hasattr(self, 'action_cache_data') and self.action_cache_data is not None

    def has_backend_handler(self) -> bool:
        return hasattr(self, 'backend_cache_data') and self.backend_cache_data is not None

    def has_action_args(self) -> bool:
        return hasattr(self, 'action_cache_data') and self.action_cache_data is not None and 'action_args' in self.action_cache_data

    def get_action_handler(self) -> Optional[Callable]:
        if hasattr(self, 'action_cache_data') and self.action_cache_data:
            # Load the actual function from cache data
            try:
                module = import_module(self.action_cache_data["module"])
                return getattr(module, self.action_cache_data["function"])
            except Exception as e:
                warn(f"Error loading action handler: {e}")
                return None
        return None

    def get_backend_handler(self) -> Optional[Callable]:
        if not self.matched_backend or not self.backend_registration:
            return None
        
        # Get the handler info from cache
        command_name = self.command
        handler_info = self.backend_registration["handlers"].get(command_name, {})
        if not handler_info:
            return None
        
        # Load the actual function from cache data
        try:
            module = import_module(handler_info["module"])
            return getattr(module, handler_info["function"])
        except Exception as e:
            warn(f"Error loading backend handler: {e}")
            return None

    def has_error_handler(self) -> bool:
        trace_in()
        if not self.backend:
            log("No backend specified for error handler")
            trace_out()
            return False
        
        # Skip action backend - actions are front-end, not backends
        if self.backend == "action":
            log("Skipping error handler check for action backend")
            trace_out()
            return False
        
        # Check if we have error handler cache data
        result = hasattr(self, 'error_cache_data') and self.error_cache_data is not None and self.error_cache_data.get('load_status') == 'success'
        trace_out()
        return result

    def get_error_handler(self) -> Optional[Callable]:
        trace_in()
        if not self.backend:
            log("No backend specified for error handler")
            trace_out()
            return None
        
        # Check if we have error handler cache data
        if not hasattr(self, 'error_cache_data') or not self.error_cache_data:
            log("No error handler cache data available")
            trace_out()
            return None
        
        # Load the actual function from cache data
        try:
            module = import_module(self.error_cache_data["module"])
            error_handler = getattr(module, self.error_cache_data["function"])
            log(f"Retrieved error handler: {self.error_cache_data['module']}.{self.error_cache_data['function']}")
            trace_out()
            return error_handler
        except Exception as e:
            warn(f"Error loading error handler: {e}")
            trace_out()
            return None

    def get_action_args(self) -> List[str]:
        if hasattr(self, 'action_cache_data') and self.action_cache_data and 'action_args' in self.action_cache_data:
            return self.action_cache_data['action_args']
        return []

    def load_action_module(self) -> bool:
        trace_in()
        if not self.has_command():
            warn("No command found")
            trace_out()
            return False
        if not self.has_action_handler():
            warn("No action handler found")
            trace_out()
            return False
        
        # Load action module from cache data
        if not self.action_cache_data:
            warn("No action cache data found")
            trace_out()
            return False
        module_to_load = self.action_cache_data.get("module")
        function_name = self.action_cache_data.get("function")
        if not module_to_load or not function_name:
            warn("Incomplete action cache data")
            trace_out()
            return False
            
        try:
            module = import_module(module_to_load)
            function = getattr(module, function_name)
            log(f"Action module loaded: '{module_to_load}' with function: '{function_name}'")
            trace_out()
            return True
        except Exception as e:
            warn(f"Error loading action module: {str(e)}")
            trace_out()
            return False

    def load_backend_module(self) -> bool:
        trace_in()
        if not self.has_backend():
            warn("No backend found")
            trace_out()
            return False
        if not self.has_backend_handler():
            warn("No backend handler found")
            trace_out()
            return False
        
        # Load backend module from cache data
        if not self.backend_cache_data:
            warn("No backend cache data found")
            trace_out()
            return False
        module_to_load = self.backend_cache_data.get("module")
        function_name = self.backend_cache_data.get("function")
        if not module_to_load or not function_name:
            warn("Incomplete backend cache data")
            trace_out()
            return False
            
        try:
            module = import_module(module_to_load)
            function = getattr(module, function_name)
            log(f"Backend module loaded: '{module_to_load}' with function: '{function_name}'")
            trace_out()
            return True
        except Exception as e:
            warn(f"Error loading backend module: {str(e)}")
            trace_out()
            return False
