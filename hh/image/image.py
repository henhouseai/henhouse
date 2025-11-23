from typing import Dict, Any, List, Optional, Union, Callable
import datetime as dt
from pathlib import Path
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_validation import ImageValidationMixin
from hh.image.image_content import ImageContentMixin
from hh.image.image_instances import ImageInstancesMixin
from hh.image.image_usage import ImageUsageMixin
from hh.image.image_display import ImageDisplayMixin
from hh.image.image_cache import ImageCacheMixin
from hh.image.image_method_registry import get_image_method_registry

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
    # Get the collected registry from all image mixins
    method_registry = get_image_method_registry()
    for method_name, config in method_registry.items():
        mixin_method_name = config['mixin_method']
        decorator_type = config['decorator']
        decorator = db_read if decorator_type == 'read' else db_write
        # Create decorator version with closure to capture mixin_method_name
        def make_dec_method(mixin_name):
            @decorator
            def image_dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                self.conn = conn
                # Connection set by decorator, not externally supplied
                self._external_conn = False
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return image_dec_method
        # Create connection version with closure
        def make_conn_method(mixin_name):
            def image_conn_method(self, *args, **kwargs):
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)
            return image_conn_method
        # Create wrapper method with closures
        def make_wrapper_method(dec_name, conn_name, dec_type):
            def wrapper_method(self, *args, **kwargs):
                if not self._external_conn:
                    # No connection supplied - use decorated method which will set self.conn
                    dec_method = getattr(self, dec_name)
                    result = dec_method(*args, **kwargs)
                    # After a decorated method, self.conn is set.
                    # If it was a read operation, we need a new write connection for cache refresh.
                    if getattr(self, '_cache_needs_refresh', False):
                        if dec_type == 'read':
                            # Create a new write connection for refresh
                            self._refresh_cached_image_with_write_conn()
                        else:  # dec_type == 'write'
                            # Reuse the existing write connection
                            self._refresh_cached_image(self.conn)
                    self.reset_connection()
                    return result
                else:
                    # Connection was supplied - use connection method which doesn't set self.conn
                    conn_method = getattr(self, conn_name)
                    result = conn_method(*args, **kwargs)
                    # If connection was supplied, we are in a transaction.
                    # But we still need to check if it's a read connection - cache refresh needs write.
                    if getattr(self, '_cache_needs_refresh', False):
                        if dec_type == 'read':
                            # Even though we're in a transaction, we need a write connection for cache refresh
                            self._refresh_cached_image_with_write_conn()
                        else:  # dec_type == 'write'
                            # Reuse the existing write connection
                            self._refresh_cached_image(self.conn)
                    return result
            return wrapper_method
        # Add methods to class
        dec_method_name = f'image_dec_{method_name}'
        conn_method_name = f'image_conn_{method_name}'
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name, decorator_type))
    return cls

@_create_wrapper_methods
class Image(
    ImageValidationMixin,
    ImageContentMixin,
    ImageInstancesMixin,
    ImageUsageMixin,
    ImageDisplayMixin,
    ImageCacheMixin,
):

    def __init__(self, image_id: int, conn: DatabaseConnection = None):
        debug(f"Initializing Image with id={image_id} and conn={conn}")
        self.conn = conn
        # Track if connection was externally supplied (vs set by decorator)
        self._external_conn = (conn is not None)
        if self.conn is None:
            return self.init_helper_dec(image_id=image_id)
        else:
            return self.init_helper_conn(image_id)
    
    #@db_read
    def init_helper_dec(self, conn: DatabaseConnection, image_id: int):
        self._do_init(conn, image_id=image_id)
    
    def init_helper_conn(self, image_id: int):
        self._do_init(self.conn, image_id=image_id)
    
    def _do_init(self, conn: DatabaseConnection, image_id: int):
        trace_in()
        self.id = image_id
        self.caption = None
        self.username = None
        self.uploaded = None
        self.visibility = None
        self.last_modified = None
        self.comments = None
        self.view_count = None
        self.instances = []
        self.cached_usage = None
        self.cache_built_at = None
        self.cache_source_last_modified = None
        self.cache_hydrated = False
        self._cache_needs_refresh = False
        self._external_conn = conn is not None
        query = "SELECT * FROM images WHERE id = %s"
        results = r_query(conn, query, [image_id])
        if not results:
            warn(f"Image with id {image_id} not found")
            report_error("action", f"Image with id {image_id} not found")
            trace_out()
            return
        image_data = results[0]
        self.caption = image_data.get('caption')
        self.username = image_data.get('username')
        self.uploaded = image_data.get('uploaded')
        self.visibility = image_data.get('visibility')
        self.view_count = image_data.get('viewCount')
        self.last_modified = image_data.get('last_modified')
        self.comments = image_data.get('comments')
        log(f"Loaded image {image_id}: {self.caption}")
        trace_out()
  
    def reset_connection(self):
        self.conn = None
