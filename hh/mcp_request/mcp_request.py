from __future__ import annotations

from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.page.page import Page, _create_wrapper_methods
from hh.page.page_class_registry import register_page_class
from hh.mcp_request.mcp_request_content import McpRequestContentMixin
from hh.mcp_request.mcp_request_validation import McpRequestValidationMixin
from hh.mcp_request.mcp_request_method_registry import get_mcp_request_method_registry


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


def _create_mcp_request_wrapper_methods(cls):
    method_registry = get_mcp_request_method_registry()
    for method_name, config in method_registry.items():
        mixin_method_name = config['mixin_method']
        decorator_type = config['decorator']
        decorator = db_read if decorator_type == 'read' else db_write

        def make_dec_method(mixin_name):
            @decorator
            def dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                log(f"{mixin_name}")
                self.conn = conn
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)

            return dec_method

        def make_conn_method(mixin_name):
            def conn_method(self, *args, **kwargs):
                log(f"{mixin_name}")
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)

            return conn_method

        def make_wrapper_method(dec_name, conn_name):
            def wrapper_method(self, *args, **kwargs):
                if self.conn is None:
                    dec_method = getattr(self, dec_name)
                    result = dec_method(*args, **kwargs)
                    self.reset_connection()
                    return result
                conn_method = getattr(self, conn_name)
                return conn_method(*args, **kwargs)

            return wrapper_method

        dec_method_name = f'mcp_request_dec_{method_name}'
        conn_method_name = f'mcp_request_conn_{method_name}'
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name))
    return cls


@register_page_class('mcp_request')
@_create_wrapper_methods
@_create_mcp_request_wrapper_methods
class McpRequest(McpRequestValidationMixin, McpRequestContentMixin, Page):
    def __init__(self, id: int, conn: DatabaseConnection = None):
        self.input_request = None
        self.output_response = None
        self.create_request = 0
        self.read_request = 0
        self.update_request_count = 0
        self.delete_request = 0
        self.create_executed = 0
        self.read_executed = 0
        self.update_executed = 0
        self.delete_executed = 0
        self.status = 'pending'
        super().__init__(id, conn)

