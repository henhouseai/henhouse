from __future__ import annotations
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.page.page import Page
from hh.page.page import _create_wrapper_methods
from hh.work.work_page_content import WorkPageContentMixin
from hh.work.work_page_validation import WorkPageValidationMixin
from hh.work.work_page_method_registry import get_work_page_method_registry

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_work_page_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def _create_work_page_wrapper_methods(cls):
    # Get the collected registry from all work_page mixins
    method_registry = get_work_page_method_registry()
    for method_name, config in method_registry.items():
        mixin_method_name = config['mixin_method']
        decorator_type = config['decorator']
        decorator = db_read if decorator_type == 'read' else db_write
        # Create decorator version with closure to capture mixin_method_name
        def make_dec_method(mixin_name):
            @decorator
            def work_page_dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                log(f"{mixin_name}")
                self.conn = conn
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return work_page_dec_method
        # Create connection version with closure
        def make_conn_method(mixin_name):
            def work_page_conn_method(self, *args, **kwargs):
                log(f"{mixin_name}")
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return work_page_conn_method
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
        dec_method_name = f'work_page_dec_{method_name}'
        conn_method_name = f'work_page_conn_{method_name}'
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name))
    return cls


@_create_wrapper_methods
@_create_work_page_wrapper_methods
class WorkPage(WorkPageValidationMixin, WorkPageContentMixin, Page):
    """
    Abstract base class for work entities (work dockets, asks, tasks, steps).
    Provides shared functionality for status, meta, sort_order, and timestamps.
    This class should never be instantiated directly - only inherited from.
    """
    
    def __init__(self, id: int, conn: DatabaseConnection = None):
        # Initialize work page specific attributes
        self.status = 'todo'
        self.meta = ''
        self.sort_order = 0
        self.started_ts = None
        self.ended_ts = None
        # Call parent constructor
        super().__init__(id, conn)

