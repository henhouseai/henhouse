from typing import Dict, Any, List, Optional, Union, Callable
import datetime as dt
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.image.image_registry import get_image
from hh.image.image import Image
from hh.tp.tp import TextProcessor
from hh.page.page_validation import PageValidationMixin
from hh.page.page_hierarchy import PageHierarchyMixin
from hh.page.page_content import PageContentMixin
from hh.page.page_images import PageImagesMixin
from hh.page.page_display import PageDisplayMixin
from hh.page.page_ajax import PageAjaxMixin
from hh.page.page_method_registry import get_page_method_registry
from hh.page.page_class_registry import register_page_class

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


def _create_wrapper_methods(cls):
    # Get the collected registry from all page mixins
    method_registry = get_page_method_registry()
    for method_name, config in method_registry.items():
        mixin_method_name = config['mixin_method']
        decorator_type = config['decorator']
        decorator = db_read if decorator_type == 'read' else db_write
        # Create decorator version with closure to capture mixin_method_name
        def make_dec_method(mixin_name):
            @decorator
            def page_dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                log(f"{mixin_name}")
                self.conn = conn
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return page_dec_method
        # Create connection version with closure
        def make_conn_method(mixin_name):
            def page_conn_method(self, *args, **kwargs):
                log(f"{mixin_name}")
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return page_conn_method
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
        dec_method_name = f'page_dec_{method_name}'
        conn_method_name = f'page_conn_{method_name}'
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name))
    return cls


@register_page_class('page')
@_create_wrapper_methods
class Page(PageValidationMixin, PageHierarchyMixin, PageContentMixin, PageImagesMixin, PageDisplayMixin, PageAjaxMixin):

    def __init__(self, id: int, conn: DatabaseConnection = None):
        debug(f"Initializing Page with id={id} and conn={conn}")
        self.conn = conn
        if self.conn is None:
            return self.init_helper_dec(id=id)
        else:
            return self.init_helper_conn(id)
    
    @db_read
    def init_helper_dec(self, conn: DatabaseConnection, id: int):
        self.do_init(conn, page_id=id)
    
    def init_helper_conn(self, id: int):
        self.do_init(self.conn, page_id=id)
    
    def do_init(self, conn: DatabaseConnection, page_id: int):
        trace_in()
        self.id = page_id
        self.name = None
        self.link = None
        self.parent = None
        self.class_name = None
        self.visibility = None
        self.text = None
        self.last_modified = None
        self.username = None
        self.comments = None
        query = "SELECT * FROM pages WHERE id = %s"
        results = r_query(conn, query, [page_id])
        if not results:
            warn(f"Page with id {page_id} not found")
            report_error("action", f"Page with id {page_id} not found")
            trace_out()
            return
        page_data = results[0]
        self.name = page_data.get('name')
        self.link = page_data.get('link')
        self.parent = page_data.get('parent')
        self.class_name = page_data.get('class')
        self.visibility = page_data.get('visibility')
        self.text = page_data.get('text')
        self.last_modified = page_data.get('last_modified')
        self.username = page_data.get('username')
        self.comments = page_data.get('comments')
        text_length = len(self.text) if self.text else 0
        log(f"Page {page_id} initialized: name='{self.name}', parent={self.parent}, class='{self.class_name}', visibility={self.visibility}, text_len={text_length}")
        trace_out()
  
    def reset_connection(self):
        self.conn = None

