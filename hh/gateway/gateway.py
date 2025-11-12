from __future__ import annotations
import time
from typing import List, Optional, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from hh.gateway.response.response import Response
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, is_safe_mode, set_debug_backend, resolve_get_debug_for, set_trace_flags, initialize_debug_modules, register_debug_init
from hh.gateway.registry.debug import set_shared_debug_whitelist, set_shared_debug_graylist, set_shared_debug_blacklist, set_shared_debug_summary_limit
from hh.gateway.debug.debug_filters import parse_list_arg
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

from hh.gateway.request.request import Request
from hh.gateway.registry.registry import CommandRegistry

__all__ = [
    "get_gateway",
    "Gateway",
]

gateway: Optional[Gateway] = None

def get_gateway() -> Gateway:
    global gateway
    if gateway is None:
        gateway = Gateway()
    return gateway

class Gateway:
    def __init__(self):
        self.request: Optional[Request] = None
        self.response: Optional[Response] = None
        self.registry: Optional[CommandRegistry] = None
        self.command: Optional[str] = None
        self.action_handler: Optional[Callable] = None
        self.backend: Optional[str] = None
        self.backend_handler: Optional[Callable] = None
        self.error_handler: Optional[Callable] = None
        self.debug_system: str = "table"
        self.debug_module: Optional[Any] = None
        self.get_debug_func: Optional[Callable] = None

    def _initialize(self, raw_argv: List[str], backend: str) -> None:
        # Lazy load and instantiate appropriate Response subclass based on backend
        self.backend = backend
        if backend == "http":
            from hh.gateway.response.response_http import ResponseHTTP
            self.response = ResponseHTTP()
            log("Initialized HTTP response handler")
        elif backend == "parser":
            from hh.gateway.response.response_parser import ResponseParser
            self.response = ResponseParser()
            log("Initialized parser response handler")
        elif backend == "mcp":
            from hh.gateway.response.response_mcp import ResponseMCP
            self.response = ResponseMCP()
            log("Initialized MCP response handler")
        else:
            # Default to parser for unknown backends (backward compatibility)
            from hh.gateway.response.response_parser import ResponseParser
            self.response = ResponseParser()
            log(f"Unknown backend '{backend}', defaulting to parser response handler")
        
        if not is_error():
            self.request = Request(raw_argv)
            self._initialize_command()
        if not is_error():
            self._initialize_debug_module()
        log("Debug module initialized")
        if not is_error():
            self.registry = CommandRegistry(self.command, self.backend)
        log("Command registry initialized")
        self._initialize_action()
        log("Action initialized")
        self._initialize_backend()
        log("Backend initialized")
        self._configure_debug_module()
        log("Debug module configured")
        log("Gateway initialization completed")

    def _initialize_debug_module(self):
        if self.request is None:
            return
        use_trace = bool(self.request.get_arg('trace'))
        use_log = bool(self.request.get_arg('log'))
        use_debug = bool(self.request.get_arg('debug') or self.request.get_arg('log'))
        set_trace_flags(use_trace, use_log, use_debug)
        initialize_debug_modules()

    def _initialize_command(self):
        if not is_error() and self.request is None:
            report_error("request", "No request found")
        if not is_error() and self.request.has_command():
            # Command was specified - use it as-is
            self.command = self.request.get_command()
        elif not is_error():
            # No command was specified - provide backend-specific defaults
            if self.backend == "http":
                # HTTP backend: default to show_page with id=1 (homepage)
                self.command = "show_page"
                self.request.command = "show_page"
                self.request.add_synthetic_arg("id", "1", "int")
                log("No command specified for HTTP backend, defaulting to 'show_page' with id=1")
            elif self.backend == "parser":
                # Parser backend: default to help command
                self.command = "help"
                self.request.command = "help"
                log("No command specified for parser backend, defaulting to 'help'")
            else:
                # Other backends: report error (unchanged behavior)
                report_error("request", "No command found")

    def _initialize_action(self):
        if not is_error() and self.registry.has_action_handler():
            self.action_handler = self.registry.get_action_handler()
        else:
            report_error("registry", "No action handler found.")
        if not is_error() and self.registry.has_action_args():
            action_args = self.registry.get_action_args()
            for arg in action_args:
                self.request.add_synthetic_arg(arg, arg)

    def _initialize_backend(self):
        if not is_error() and self.registry.has_backend_handler():
            self.backend_handler = self.registry.get_backend_handler()
        else:
            report_error("registry", "No backend handler found.")
        
    def _configure_debug_module(self):
        if self.request.is_no("debug"):
            self.debug_system = "none"
        elif self.request.get_arg("trace"):
            self.debug_system = "trace"
        else:
            self.debug_system = "table"
        set_debug_backend(self.debug_system)
        self.get_debug_func = resolve_get_debug_for(self.debug_system)
        if self.get_debug_func is None and self.debug_system != "none":
            self.debug_system = "debug_safe"
            set_debug_backend(self.debug_system)
            self.get_debug_func = resolve_get_debug_for("debug_safe")
        self._apply_debug_filter_overrides()
        log("Debug module configuration completed")
    
    def _apply_debug_filter_overrides(self):
        """Apply debug filter overrides from request arguments to shared debug store"""
        try:
            # Process debug limit
            debug_limit = self.request.get_arg('debug-limit')
            if debug_limit:
                try:
                    limit = int(debug_limit)
                    set_shared_debug_summary_limit(limit)
                except (ValueError, TypeError):
                    pass
            
            # Process whitelist
            white_list = self.request.get_arg('white')
            if white_list:
                parsed_list = parse_list_arg(white_list)
                if parsed_list:
                    set_shared_debug_whitelist(parsed_list)
            
            # Process graylist
            gray_list = self.request.get_arg('gray')
            if gray_list:
                parsed_list = parse_list_arg(gray_list)
                if parsed_list:
                    set_shared_debug_graylist(parsed_list)
            
            # Process blacklist
            black_list = self.request.get_arg('black')
            if black_list:
                parsed_list = parse_list_arg(black_list)
                if parsed_list:
                    set_shared_debug_blacklist(parsed_list)
        except Exception:
            pass

    def dispatch(self, raw_argv: List[str], backend: str) -> None:
        self._initialize(raw_argv, backend)
        log("Gateway initialization completed, dispatching...")
        if not is_error() and not self.request:
            report_error("request", "No request found")
        if not is_error() and not self.command:
            report_error("request", "No command found")
        if not is_error() and not self.backend:
            report_error("registry", "No backend found.")
        if not is_error():
            if self.registry.load_action_module():
                log(f"Action module loaded: {self.action_handler.__module__}")
            else:
                module_name = self.action_handler.__module__ if self.action_handler else "unknown"
                report_error("registry", f"Error loading action module: {module_name}")
        if not is_error():
            if self.registry.load_backend_module():
                log(f"Backend module loaded: {self.backend_handler.__module__}")
            else:
                module_name = self.backend_handler.__module__ if self.backend_handler else "unknown"
                report_error("registry", f"Error loading backend module: {module_name}")
        if not is_error():
            log(f"Starting action execution: {self.action_handler.__module__}.{self.action_handler.__name__}")
            start_time = time.time()
            try:
                result = self.action_handler()
                duration = time.time() - start_time
                if result:
                    log(f"Action execution completed successfully in {duration:.3f}s")
                else:
                    warn("Action execution failed.")
                    report_error("action", f"Action execution failed in {duration:.3f}s")
            except Exception as e:
                duration = time.time() - start_time
                warn("Action execution raised an exception.")
                report_error("action", f"Action execution raised an exception in {duration:.3f}s: {e}")
        if not is_error() and not self.response.has_action_response():
            report_error("backend", "No action response found")
        if not is_error():
            log(f"Starting backend execution: {self.backend_handler.__module__}.{self.backend_handler.__name__}")
            start_time = time.time()
            try:
                result = self.backend_handler()
                duration = time.time() - start_time
                if result:
                    log(f"Backend execution completed successfully in {duration:.3f}s")
                else:
                    warn("Backend execution failed.")
                    report_error("backend", f"Backend execution failed in {duration:.3f}s")
            except Exception as e:
                duration = time.time() - start_time
                warn("Backend execution raised an exception.")
                report_error("backend", f"Backend execution raised an exception in {duration:.3f}s: {e}")
        has_errors = is_error()
        log(f"Error check result: {has_errors}")
        if has_errors:
            if self.registry and self.registry.has_error_handler():
                log("Errors detected, running error handler")
                error_handler = self.registry.get_error_handler()
                if error_handler:
                    try:
                        error_result = error_handler()
                        if error_result:
                            log("Error handler completed successfully")
                        else:
                            warn("Error handler failed")
                    except Exception as e:
                        warn(f"Error handler raised an exception: {e}")
                else:
                    warn("Error handler is None")
            else:
                log("Errors detected but no error handler available")
        else:
            log("No errors detected")
        self.flush_debug()
        return self.response.get_output()

    def get_arg(self, name: str) -> Any:
        trace_in()
        if not self.request:
            log("No request available")
            trace_out()
            return None
        result = self.request.get_arg(name)
        log(f"Retrieved arg '{name}': {result}")
        trace_out()
        return result

    def is_no(self, flag_name: str) -> bool:
        trace_in()
        if not self.request:
            log("No request available")
            trace_out()
            return False
        result = self.request.is_no(flag_name)
        if result:
            log(f"Flag '{flag_name}' is disabled")
        trace_out()
        return result
    
    def is_set(self, name: str) -> bool:
        trace_in()
        if not self.request:
            log("No request available")
            trace_out()
            return False
        result = self.request.is_set(name)
        trace_out()
        return result

    def capture(self, message: str, level: int) -> None:
        if is_safe_mode():
            return
        if self.debug_system == "none" or not self.get_debug_func:
            return
        try:
            debug_obj = self.get_debug_func()
            if debug_obj:
                debug_obj.capture(message, level)
        except Exception:
            pass
    
    def flush_debug(self) -> None:
        if self.debug_system == "none" or not self.get_debug_func:
            return
        try:
            debug_obj = self.get_debug_func()
            if hasattr(debug_obj, 'render'):
                debug_output = debug_obj.render()
                if debug_output:
                    self.response.add_output(debug_output)
        except Exception as e:
            warn(f"Error flushing debug output: {e}")
    
    def get_debug_safe_mode(self) -> bool:
        return self.debug_system == "debug_safe" or self.debug_system == "none"
    
    def switch_to_safe_debug(self) -> None:
        if self.debug_system == "table":
            try:
                import importlib
                self.debug_module = importlib.import_module("hh.gateway.debug.debug_safe")
                self.debug_system = "debug_safe"
            except Exception as e:
                self.warn(f"Failed to switch to safe debug mode: {e}")
    
    def restore_debug_system(self) -> None:
        if self.debug_system == "debug_safe":
            try:
                if self.request.get_arg("trace"):
                    target_system = "trace"
                else:
                    target_system = "table"              
                from hh.gateway.registry.debug import set_debug_backend, resolve_get_debug_for
                set_debug_backend(target_system)
                self.get_debug_func = resolve_get_debug_for(target_system)
                self.debug_system = target_system
            except Exception as e:
                self.warn(f"Failed to restore debug system: {e}")


gateway: Optional[Gateway] = None

def get_gateway() -> Gateway:
    global gateway
    trace_in()
    if gateway is None:
        gateway = Gateway()
    trace_out()
    return gateway
