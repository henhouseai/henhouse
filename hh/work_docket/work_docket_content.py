from __future__ import annotations
from typing import Dict, Any, List, Optional
from hh.gateway.connection.connection import r_query, c_query, d_query, u_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.work_docket.work_docket_method_registry import register_work_docket_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_work_docket_content_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_work_docket_mixin_methods
def _register_work_docket_content_methods():
    # All modify methods (status, meta, sort_order) are handled by WorkPageContentMixin
    # Only work_docket-specific methods would go here
    return {}


class WorkDocketContentMixin:
    # do_init, _get_page_data, add_page_class_information, delete_page_class_information,
    # _modify_status, _modify_meta, _modify_sort_order are all handled by WorkPage base class
    
    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        return (
            """
            SELECT pages.id
            FROM pages
            WHERE pages.parent = %s
              AND pages.class = 'work_docket'
            ORDER BY COALESCE(
                CAST(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.sort_order')) AS UNSIGNED),
                0
            )
            """,
            [parent_id]
        )
    
    def _get_child_row_field_type(self) -> str:
        """Return field type based on status for work docket rows."""
        status = self.status if hasattr(self, 'status') else 'todo'
        return f'work_docket_{status}'

