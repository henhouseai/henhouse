from __future__ import annotations

from typing import Any, Dict

from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.file.file_content import FileContentMixin
from hh.file.file_cache import FileCacheMixin
from hh.file.file_method_registry import get_file_method_registry

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
    method_registry = get_file_method_registry()
    for method_name, config in method_registry.items():
        mixin_method_name = config["mixin_method"]
        decorator_type = config["decorator"]
        decorator = db_read if decorator_type == "read" else db_write

        def make_dec_method(mixin_name):
            @decorator
            def file_dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                self.conn = conn
                # Connection set by decorator, not externally supplied
                self._external_conn = False
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)

            return file_dec_method

        def make_conn_method(mixin_name):
            def file_conn_method(self, *args, **kwargs):
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)

            return file_conn_method

        def make_wrapper_method(dec_name, conn_name, dec_type):
            def wrapper(self, *args, **kwargs):
                if not self._external_conn:
                    # No connection supplied - use decorated method which will set self.conn
                    dec_method = getattr(self, dec_name)
                    result = dec_method(*args, **kwargs)
                    # After a decorated method, self.conn is set.
                    # If it was a read operation, we need a new write connection for cache refresh.
                    if getattr(self, '_cache_needs_refresh', False):
                        if dec_type == 'read':
                            # Create a new write connection for refresh
                            self._refresh_cached_file_with_write_conn()
                        else:  # dec_type == 'write'
                            # Reuse the existing write connection
                            self._refresh_cached_file(self.conn)
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
                            self._refresh_cached_file_with_write_conn()
                        else:  # dec_type == 'write'
                            # Reuse the existing write connection
                            self._refresh_cached_file(self.conn)
                    return result

            return wrapper

        dec_method_name = f"file_dec_{method_name}"
        conn_method_name = f"file_conn_{method_name}"
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name, decorator_type))

    return cls


@_create_wrapper_methods
class File(FileContentMixin, FileCacheMixin):
    def __init__(self, file_id: int, conn: DatabaseConnection = None):
        self.conn = conn
        # Track if connection was externally supplied (vs set by decorator)
        self._external_conn = (conn is not None)
        if self.conn is None:
            self.init_helper_dec(file_id=file_id)
        else:
            self.init_helper_conn(file_id)

    @db_read
    def init_helper_dec(self, conn: DatabaseConnection, file_id: int):
        self._do_init(conn, file_id=file_id)

    def init_helper_conn(self, file_id: int):
        self._do_init(self.conn, file_id=file_id)

    def _do_init(self, conn: DatabaseConnection, file_id: int):
        trace_in()
        self.id = file_id
        self.file_name = None
        self.file_path = None
        self.description = None
        self.mime_type = None
        self.size_bytes = None
        self.username = None
        self.uploaded = None
        self.last_modified = None
        self.comments = None
        self.visibility = None
        self.cache_built_at = None
        self.cache_hydrated = False
        self.pages = []  # Usage data (which pages use this file)
        self._cache_needs_refresh = False
        query = "SELECT * FROM files WHERE id = %s"
        results = r_query(conn, query, [file_id])
        if not results:
            warn(f"File {file_id} not found")
            report_error("action", f"File {file_id} not found")
            trace_out()
            return

        row: dict[str, Any] = results[0]
        self.file_name = row.get("file_name")
        self.file_path = row.get("file_path")
        self.description = row.get("description")
        self.mime_type = row.get("mime_type")
        self.size_bytes = row.get("size_bytes")
        self.username = row.get("username")
        self.uploaded = row.get("uploaded")
        self.last_modified = row.get("last_modified")
        self.comments = row.get("comments")
        self.visibility = row.get("visibility")
        self.cache_built_at = row.get("cache_built_at")
        trace_out()

    def reset_connection(self):
        self.conn = None

