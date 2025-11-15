from __future__ import annotations
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.page.page import Page
from hh.page.page_class_registry import register_page_class
from hh.page.page import _create_wrapper_methods
from hh.source_code_file.source_code_file_content import SourceCodeFileContentMixin
from hh.source_code_file.source_code_file_validation import SourceCodeFileValidationMixin
from hh.source_code_file.source_code_file_method_registry import get_source_code_file_method_registry

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_source_code_file_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def _create_source_code_file_wrapper_methods(cls):
    # Get the collected registry from all source_code_file mixins
    method_registry = get_source_code_file_method_registry()
    for method_name, config in method_registry.items():
        mixin_method_name = config['mixin_method']
        decorator_type = config['decorator']
        decorator = db_read if decorator_type == 'read' else db_write
        # Create decorator version with closure to capture mixin_method_name
        def make_dec_method(mixin_name):
            @decorator
            def source_code_file_dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                log(f"{mixin_name}")
                self.conn = conn
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return source_code_file_dec_method
        # Create connection version with closure
        def make_conn_method(mixin_name):
            def source_code_file_conn_method(self, *args, **kwargs):
                log(f"{mixin_name}")
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return source_code_file_conn_method
        # Create wrapper method with closures
        def make_wrapper_method(dec_name, conn_name):
            def wrapper_method(self, *args, **kwargs):
                if self.conn is None:
                    dec_method = getattr(self, dec_name)
                    result = dec_method(*args, **kwargs)
                    self.reset_connection()
                    return result
                else:
                    conn_method = getattr(self, conn_name)
                    return conn_method(*args, **kwargs)
            return wrapper_method
        # Add methods to class
        dec_method_name = f'source_code_file_dec_{method_name}'
        conn_method_name = f'source_code_file_conn_{method_name}'
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name))
    return cls


@register_page_class('source_code_file')
@_create_wrapper_methods
@_create_source_code_file_wrapper_methods
class SourceCodeFile(SourceCodeFileValidationMixin, SourceCodeFileContentMixin, Page):
    """
    A derived Page class for source code files.
    Extends Page with file path and language information.
    """
    
    def __init__(self, id: int, conn: DatabaseConnection = None):
        # Initialize source code file specific attributes
        self.file_path = None
        self.language = None
        # Call parent constructor
        super().__init__(id, conn)

