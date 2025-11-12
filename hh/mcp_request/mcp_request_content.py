from __future__ import annotations

import json
from typing import Dict, Any, Optional

from hh.gateway.connection.connection import r_query, u_query, c_query, d_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.mcp_request.mcp_request_method_registry import (
    register_mcp_request_mixin_methods,
)


trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_mcp_request_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_mcp_request_mixin_methods
def _register_mcp_request_methods():
    return {
        'update_request': {'mixin_method': '_update_request', 'decorator': 'write'},
    }


class McpRequestContentMixin:
    VALID_STATUSES = {
        'pending',
        'approved',
        'executing',
        'completed',
        'failed',
        'cancelled',
        'rolled_back',
    }

    @staticmethod
    def get_children_query(parent_id: int) -> tuple[str, list]:
        """Return query to get mcp_request children."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'mcp_request' ORDER BY id",
            [parent_id]
        )

    @classmethod
    def allow_null_names(cls) -> bool:
        return True

    @classmethod
    def auto_link_name(cls) -> bool:
        """Override: mcp_request pages do not auto-link names."""
        return False

    def get_display_name(self) -> str:
        """
        Override to return status-based display name when name is None.
        """
        if self.name:
            return self.name
        
        status = self.status if hasattr(self, 'status') else 'pending'
        return f"MCP Request ({status})"

    def do_init(self, conn: DatabaseConnection, page_id: int):
        super().do_init(conn, page_id)

        if is_error() or not conn:
            return

        trace_in()
        query = """
            SELECT
                input_request,
                output_response,
                create_request,
                read_request,
                update_request,
                delete_request,
                create_executed,
                read_executed,
                update_executed,
                delete_executed,
                status
            FROM mcp_requests
            WHERE page_id = %s
        """
        results = r_query(conn, query, [page_id])
        if results:
            data = results[0]
            self.input_request = data.get('input_request')
            self.output_response = data.get('output_response')
            self.create_request = data.get('create_request', 0)
            self.read_request = data.get('read_request', 0)
            self.update_request_count = data.get('update_request', 0)
            self.delete_request = data.get('delete_request', 0)
            self.create_executed = data.get('create_executed', 0)
            self.read_executed = data.get('read_executed', 0)
            self.update_executed = data.get('update_executed', 0)
            self.delete_executed = data.get('delete_executed', 0)
            self.status = data.get('status', 'pending')
            log(
                f"MCP Request {page_id} loaded: status={self.status}, "
                f"request_totals=({self.create_request},{self.read_request},"
                f"{self.update_request_count},{self.delete_request}), "
                f"executed_totals=({self.create_executed},{self.read_executed},"
                f"{self.update_executed},{self.delete_executed})"
            )
        else:
            debug(f"MCP Request {page_id} missing record; initializing defaults")
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
        trace_out()

    @classmethod
    def add_page_class_information(cls, new_page_id: int, conn: DatabaseConnection):
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return

        input_request = cls._safe_json_arg(gateway.get_arg('input_request'))
        output_response = cls._safe_json_arg(gateway.get_arg('output_response'))

        try:
            c_query(
                conn,
                """
                INSERT INTO mcp_requests (
                    page_id,
                    input_request,
                    output_response,
                    create_request,
                    read_request,
                    update_request,
                    delete_request,
                    create_executed,
                    read_executed,
                    update_executed,
                    delete_executed,
                    status
                )
                VALUES (%s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 'pending')
                """,
                (new_page_id, input_request, output_response),
            )
            log(f"Initialized mcp_requests entry for page {new_page_id}")
        except Exception as exc:
            warn(f"Failed to initialize mcp_requests entry: {exc}")
            report_error("backend", f"Failed to create mcp_requests entry: {exc}")
        trace_out()

    def delete_page_class_information(self):
        trace_in()
        if self.conn and self.id:
            try:
                d_query(self.conn, "DELETE FROM mcp_requests WHERE page_id = %s", [self.id])
                log(f"Deleted mcp_requests entry for page {self.id}")
            except Exception as exc:
                warn(f"Failed to delete mcp_requests entry: {exc}")
                report_error("backend", f"Failed to delete mcp_requests entry: {exc}")
        trace_out()

    def _get_page_data(self) -> Dict[str, Any]:
        data = super()._get_page_data()
        data.update(
            {
                "input_request": self.input_request,
                "output_response": self.output_response,
                "create_request": self.create_request,
                "read_request": self.read_request,
                "update_request": self.update_request_count,
                "delete_request": self.delete_request,
                "create_executed": self.create_executed,
                "read_executed": self.read_executed,
                "update_executed": self.update_executed,
                "delete_executed": self.delete_executed,
                "status": self.status,
            }
        )
        return data

    def add_badge_headers(self) -> Dict[str, Any]:
        badge_headers = super().add_badge_headers()
        badge_headers['page_summary']['status'] = self.status
        badge_headers['mcp_request_counts'] = {
            "create_request": self.create_request,
            "read_request": self.read_request,
            "update_request": self.update_request_count,
            "delete_request": self.delete_request,
            "create_executed": self.create_executed,
            "read_executed": self.read_executed,
            "update_executed": self.update_executed,
            "delete_executed": self.delete_executed,
        }
        return badge_headers

    def add_lower_content(self) -> list[str]:
        lines: list[str] = []
        if self.input_request:
            pretty = self._pretty_json(self.input_request)
            lines.append(f"Input Request:\n{pretty}")
        if self.output_response:
            pretty = self._pretty_json(self.output_response)
            lines.append(f"Output Response:\n{pretty}")
        return lines

    def get_child_page_data(self) -> Dict[str, Any]:
        """Override to return simplified data for mcp_request children: id, status, total_actions."""
        trace_in()
        total_actions = (
            self.create_request + self.read_request + 
            self.update_request_count + self.delete_request
        )
        data = {
            "id": self.id,
            "status": self.status if hasattr(self, 'status') else 'pending',
            "total_actions": total_actions,
        }
        trace_out()
        return data

    def get_child_row_field_type(self) -> str:
        """Return field type for mcp_request rows."""
        return 'mcp_request'

    def _update_request(
        self,
        input_request: Optional[str] = None,
        output_response: Optional[str] = None,
        create_request: Optional[int] = None,
        read_request: Optional[int] = None,
        update_request: Optional[int] = None,
        delete_request: Optional[int] = None,
        create_executed: Optional[int] = None,
        read_executed: Optional[int] = None,
        update_executed: Optional[int] = None,
        delete_executed: Optional[int] = None,
        status: Optional[str] = None,
    ) -> bool:
        trace_in()
        updates = []
        params = []

        if input_request is not None:
            normalized = self._safe_json_arg(input_request, field_name='input_request')
            if not is_error():
                updates.append("input_request = %s")
                params.append(normalized)

        if output_response is not None:
            normalized = self._safe_json_arg(output_response, field_name='output_response')
            if not is_error():
                updates.append("output_response = %s")
                params.append(normalized)

        numeric_fields = {
            "create_request": create_request,
            "read_request": read_request,
            "update_request": update_request,
            "delete_request": delete_request,
            "create_executed": create_executed,
            "read_executed": read_executed,
            "update_executed": update_executed,
            "delete_executed": delete_executed,
        }

        for column, value in numeric_fields.items():
            if value is not None:
                try:
                    converted = int(value)
                    updates.append(f"{column} = %s")
                    params.append(converted)
                except (TypeError, ValueError):
                    warn(f"Invalid integer for {column}: {value}")
                    report_error("action", f"Invalid integer for {column}")

        if status is not None:
            normalized_status = status.strip().lower()
            if normalized_status not in self.VALID_STATUSES:
                warn(f"Invalid status value '{status}'")
                report_error("action", f"Invalid status '{status}'")
            else:
                updates.append("status = %s")
                params.append(normalized_status)

        if is_error():
            trace_out()
            return False

        if not updates:
            log("No MCP request fields provided for update")
            trace_out()
            return True

        params.append(self.id)
        affected = u_query(
            self.conn,
            f"UPDATE mcp_requests SET {', '.join(updates)} WHERE page_id = %s",
            params,
        )
        if affected == 0:
            warn(f"Failed to update mcp_requests entry for page {self.id}")
            report_error("action", f"Failed to update MCP request {self.id}")
        else:
            log(f"Updated mcp_requests entry for page {self.id} ({affected} rows)")
            self._refresh_local_state()

        trace_out()
        return not is_error()

    def _refresh_local_state(self):
        if self.conn:
            results = r_query(
                self.conn,
                """
                SELECT
                    input_request,
                    output_response,
                    create_request,
                    read_request,
                    update_request,
                    delete_request,
                    create_executed,
                    read_executed,
                    update_executed,
                    delete_executed,
                    status
                FROM mcp_requests
                WHERE page_id = %s
                """,
                [self.id],
            )
            if results:
                data = results[0]
                self.input_request = data.get('input_request')
                self.output_response = data.get('output_response')
                self.create_request = data.get('create_request', 0)
                self.read_request = data.get('read_request', 0)
                self.update_request_count = data.get('update_request', 0)
                self.delete_request = data.get('delete_request', 0)
                self.create_executed = data.get('create_executed', 0)
                self.read_executed = data.get('read_executed', 0)
                self.update_executed = data.get('update_executed', 0)
                self.delete_executed = data.get('delete_executed', 0)
                self.status = data.get('status', 'pending')

    @staticmethod
    def _safe_json_arg(value: Optional[str], field_name: str = 'json') -> Optional[str]:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                parsed = json.loads(value)
                return json.dumps(parsed, ensure_ascii=False)
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            warn(f"Invalid JSON for {field_name}: {exc}")
            report_error("action", f"Invalid JSON supplied for {field_name}")
            return None

    @staticmethod
    def _pretty_json(value: Any) -> str:
        try:
            if isinstance(value, str):
                parsed = json.loads(value)
            else:
                parsed = value
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

