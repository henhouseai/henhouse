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
        decorator = db_read if config["decorator"] == "read" else db_write

        def make_dec_method(mixin_name):
            @decorator
            def file_dec_method(self, conn: DatabaseConnection, *args, **kwargs):
                mixin_method = getattr(super(cls, self), mixin_name)
                self.conn = conn
                return mixin_method(*args, **kwargs)

            return file_dec_method

        def make_conn_method(mixin_name):
            def file_conn_method(self, *args, **kwargs):
                mixin_method = getattr(super(cls, self), mixin_name)
                return mixin_method(*args, **kwargs)

            return file_conn_method

        def make_wrapper_method(dec_name, conn_name):
            def wrapper(self, *args, **kwargs):
                if self.conn is None:
                    dec_method = getattr(self, dec_name)
                    result = dec_method(*args, **kwargs)
                    self.reset_connection()
                    return result
                conn_method = getattr(self, conn_name)
                return conn_method(*args, **kwargs)

            return wrapper

        dec_method_name = f"file_dec_{method_name}"
        conn_method_name = f"file_conn_{method_name}"
        setattr(cls, dec_method_name, make_dec_method(mixin_method_name))
        setattr(cls, conn_method_name, make_conn_method(mixin_method_name))
        setattr(cls, method_name, make_wrapper_method(dec_method_name, conn_method_name))

    return cls


@_create_wrapper_methods
class File(FileContentMixin):
    def __init__(self, file_id: int, conn: DatabaseConnection = None):
        self.conn = conn
        if self.conn is None:
            self.init_helper_dec(file_id=file_id)
        else:
            self.init_helper_conn(file_id)

    @db_read
    def init_helper_dec(self, conn: DatabaseConnection, file_id: int):
        self.do_init(conn, file_id=file_id)

    def init_helper_conn(self, file_id: int):
        self.do_init(self.conn, file_id=file_id)

    def do_init(self, conn: DatabaseConnection, file_id: int):
        trace_in()
        self.id = file_id
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
        trace_out()

    def reset_connection(self):
        self.conn = None

