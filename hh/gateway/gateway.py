from __future__ import annotations
import random
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
from hh.gateway.connection.connection import Connection
from hh.gateway.system.file_system import FileSystem
from hh.gateway.system.process_manager import ProcessManager
from hh.gateway.registry.registry import CommandRegistry
from hh.gateway.registry.backend import BACKEND_RESPONSE_MODULES
from hh.image.image_registry import refresh_stale_image_caches
from hh.file.file_registry import refresh_stale_file_caches
from hh.page.page_registry import refresh_stale_page_caches

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
        self.conn: Optional[Connection] = None
        self.files: Optional[FileSystem] = None
        self.os: Optional[Any] = None  # ProcessManager, lazy loaded
        self.registry: Optional[CommandRegistry] = None
        self._user_tier_level: int = 0
        self.command: Optional[str] = None
        self.action_handler: Optional[Callable] = None
        self.backend: Optional[str] = None
        self.backend_handler: Optional[Callable] = None
        self.error_handler: Optional[Callable] = None
        self.debug_system: str = "table"
        self.debug_module: Optional[Any] = None
        self.get_debug_func: Optional[Callable] = None

    def _initialize(self, raw_argv: List[str], backend: str) -> None:
        self.backend = backend
        
        if not is_error():
            self.request = Request(raw_argv)
            self._initialize_command()
        
        if not is_error():
            self._initialize_debug_module()
        
        if not is_error():
            # Check for dry_run flag from request before initializing connection and filesystem
            dry_run = False
            if self.request:
                dry_run = bool(self.request.get_arg('dry_run') or self.request.get_arg('dry-run'))
            self._user_tier_level = self._initialize_connection(dry_run=dry_run)
        
        if not is_error():
            # Initialize response after connection (so we can pass tier level)
            self._initialize_response()
            
            self.files = FileSystem(dry_run=dry_run)
            self.os = ProcessManager()
        
        if not is_error():
            self.registry = CommandRegistry(self.command, self.backend)
        
        self._initialize_action()
        self._initialize_backend()
        self._configure_debug_module()

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
        # Check trace flag first (enables trace flags regardless of backend)
        if self.request.get_arg("trace"):
            self.debug_system = "trace"
        elif self.request.is_no("debug"):
            self.debug_system = "none"
        else:
            self.debug_system = "table"
        
        # MCP backend/flag check LAST - always uses debug_mcp
        if self.request.get_arg("mcp") or self.backend == "mcp" or self.backend == "maintenance":
            self.debug_system = "mcp"
        
        # Set debug backend and resolve function
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

        # Injected errors for maintenance ping testing (25% chance each, or always if -log).
        # Commented out - uncomment to test error handling.
        # proceed_to_backend = not is_error()
        # force_error = bool(self.request and self.request.get_arg('log'))
        # if force_error or random.random() < 0.25:
        #     report_error("action", "Injected test error after action execution")
        # if force_error or random.random() < 0.25:
        #     report_error("backend", "Injected test error before backend execution")
        proceed_to_backend = not is_error()

        if proceed_to_backend:
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
        self._process_errors()
        self._commit()
        
        # Close database connections before flushing debug (so close logs are captured)
        if self.conn:
            log("Closing database connections...")
            self.conn.close()
        
        self.flush_debug()
        if not self.response:
            return "Error: Response object not initialized. Gateway initialization may have failed."
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
                # Set debug_output on response object (even if empty for MCP)
                # For MCP, debug_safe will output JSON structure (dict)
                # For HTTP/Parser, it will output text (string)
                if isinstance(debug_output, dict):
                    # MCP backend - always set, even if entries array is empty
                    self.response.debug_output = debug_output
                elif debug_output:
                    # For text output (HTTP/Parser), store as dict with "text" key
                    self.response.debug_output = {"text": debug_output}
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
    
    def _initialize_connection(self, dry_run: bool = False) -> int:
        """Determine and create connection type based on command-line arguments (lazy import if needed). Returns user tier level."""
        trace_in()
        tier_level = 0
        
        if self.request:
            if self.request.get_arg('password') or self.request.get_arg('root_password'):
                log("Root connection type requested, lazy-importing RootConnection...")
                from hh.gateway.connection.root_connection import RootConnection
                self.conn = RootConnection(dry_run=dry_run)
            else:
                log("Standard connection type selected")
                self.conn = Connection(dry_run=dry_run)
        else:
            log("Standard connection type selected (no request available)")
            self.conn = Connection(dry_run=dry_run)
        
        if self.conn:
            tier_level = self.conn.initialize()
        
        trace_out()
        return tier_level
    
    def _initialize_response(self) -> None:
        """Initialize response handler with user tier level."""
        trace_in()
        try:
            # Lazy load and instantiate appropriate Response subclass based on backend
            response_path = BACKEND_RESPONSE_MODULES.get(self.backend)
            if response_path is None:
                response_path = BACKEND_RESPONSE_MODULES.get("parser")
                log(f"Unknown backend '{self.backend}', defaulting to parser response handler")
            module_name, class_name = response_path.rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            ResponseClass = getattr(module, class_name)
            self.response = ResponseClass()
            # Set user tier level on response
            if self._user_tier_level > 0:
                self.response.set_user_tier_level(self._user_tier_level)
                log(f"Set user tier level {self._user_tier_level} in response")
            log(f"Initialized {self.backend} response handler: {response_path}")
        except Exception as e:  # noqa: BLE001
            warn(f"Failed to initialize response handler: {e}")
            report_error("backend", f"Failed to initialize response handler: {e}")
            self.response = None
        trace_out()
    
    def _process_errors(self) -> None:
        """Process errors and run error handler if available."""
        trace_in()
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
        trace_out()
    
    def _commit(self) -> None:
        """Commit file operations and database transactions if no errors."""
        trace_in()
        log("Starting commit process...")
        
        if is_error():
            log("Skipping commit due to errors")
            trace_out()
            return
        
        # Always commit file operations first (will no-op if no operations)
        if self.files:
            log("Committing file operations...")
            if not self.files.commit():
                warn("File operations failed, rolling back")
                self.files.rollback()
                if self.conn:
                    self.conn.rollback()
                report_error("file_operation", "File operations failed")
                trace_out()
                return
        else:
            log("No FileSystem available, skipping file operations")
        
        # Refresh image caches for any images in hot cache that need updating
        if not is_error():
            log("Refreshing stale image caches...")
            try:
                refresh_stale_image_caches()
            except Exception as e:
                warn(f"Error refreshing image caches: {e}")
                report_error("cache_refresh", f"Error refreshing image caches: {e}")
        
        # Refresh file caches for any files in hot cache that need updating
        if not is_error():
            log("Refreshing stale file caches...")
            try:
                refresh_stale_file_caches()
            except Exception as e:
                warn(f"Error refreshing file caches: {e}")
                report_error("cache_refresh", f"Error refreshing file caches: {e}")
        
        # Refresh page caches for any pages in hot cache that need updating
        if not is_error():
            log("Refreshing stale page caches...")
            try:
                refresh_stale_page_caches()
            except Exception as e:
                warn(f"Error refreshing page caches: {e}")
                report_error("cache_refresh", f"Error refreshing page caches: {e}")
        
        # Check for errors again after file operations and cache refresh
        if not is_error():
            # Always commit database transactions (will no-op if no transaction)
            if self.conn:
                log("Committing database transactions...")
                try:
                    self.conn.commit()
                except Exception as e:
                    warn(f"Database commit failed: {e}")
                    # Rollback file operations if DB commit fails
                    if self.files:
                        self.files.rollback()
                    report_error("connection", f"Database commit failed: {e}")
            else:
                log("No connection available, skipping database commit")
        else:
            # Errors detected after file operations, rollback everything
            warn("Errors detected after file operations, rolling back")
            if self.files:
                self.files.rollback()
            if self.conn:
                self.conn.rollback()
        
        log("Commit process completed")
        trace_out()


gateway: Optional[Gateway] = None

def get_gateway() -> Gateway:
    global gateway
    trace_in()
    if gateway is None:
        gateway = Gateway()
    trace_out()
    return gateway
