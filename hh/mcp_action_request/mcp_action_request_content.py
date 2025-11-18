from __future__ import annotations

import json
from typing import Dict, Any, Optional

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
from hh.mcp_action_request.mcp_action_request_method_registry import (
    register_mcp_action_request_mixin_methods,
)
from hh.page.page_registry import get_page_conn


trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_mcp_action_request_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_mcp_action_request_mixin_methods
def _register_mcp_action_request_methods():
    return {
        'update_action_request': {
            'mixin_method': '_update_action_request',
            'decorator': 'write',
        },
    }


class McpActionRequestContentMixin:
    VALID_STATUSES = {
        'pending',
        'approved',
        'dependency_unmet',
        'executing',
        'executed',
        'failed',
        'rejected',
        'cancelled',
    }

    BOOL_FIELDS = ['is_create', 'is_read', 'is_update', 'is_delete']

    def _ensure_metadata_defaults(self) -> Dict[str, Any]:
        metadata = self._get_metadata_dict()
        mutated = False

        for field in ['tool_name', 'arguments', 'extraction_spec', 'result']:
            if field not in metadata:
                metadata[field] = None
                mutated = True

        status = metadata.get('status')
        normalized_status = status.strip().lower() if isinstance(status, str) else None
        if normalized_status not in self.VALID_STATUSES:
            metadata['status'] = 'pending'
            mutated = True

        for field in self.BOOL_FIELDS:
            current = bool(metadata.get(field))
            if metadata.get(field) != current:
                metadata[field] = current
                mutated = True

        if mutated:
            self._write_metadata_dict(metadata)
        return metadata

    def _sync_from_metadata(self, metadata: Dict[str, Any]) -> None:
        self.tool_name = metadata.get('tool_name')
        self.arguments = metadata.get('arguments')
        self.extraction_spec = metadata.get('extraction_spec')
        self.status = metadata.get('status', 'pending')
        self.result = metadata.get('result')
        self.is_create = bool(metadata.get('is_create'))
        self.is_read = bool(metadata.get('is_read'))
        self.is_update = bool(metadata.get('is_update'))
        self.is_delete = bool(metadata.get('is_delete'))

    @staticmethod
    def get_children_query(parent_id: int) -> tuple[str, list]:
        """Return query to get mcp_action children."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'mcp_action' ORDER BY id",
            [parent_id]
        )

    def get_display_name(self) -> str:
        """
        Override to return tool-based display name when name is None.
        """
        if self.name:
            return self.name
        
        tool_name = self.tool_name if hasattr(self, 'tool_name') and self.tool_name else 'unknown'
        status = self.status if hasattr(self, 'status') else 'pending'
        return f"{tool_name} ({status})"

    def do_init(self, conn: DatabaseConnection, page_id: int):
        super().do_init(conn, page_id)

        if is_error() or not conn:
            return

        trace_in()
        metadata = self._ensure_metadata_defaults()
        self._sync_from_metadata(metadata)
        log(
            f"MCP Action Request {page_id} loaded: tool={self.tool_name}, "
            f"status={self.status}, crud_flags="
            f"({self.is_create},{self.is_read},{self.is_update},{self.is_delete})"
        )
        trace_out()

    @classmethod
    def add_page_class_information(cls, new_page_id: int, conn: DatabaseConnection):
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return

        tool_name = gateway.get_arg('tool_name') if gateway.is_set('tool_name') else None
        arguments = cls._safe_json_arg(gateway.get_arg('arguments'))
        extraction_spec = cls._safe_json_arg(gateway.get_arg('extraction_spec'))
        result = cls._safe_json_arg(gateway.get_arg('result'))

        page = get_page_conn(conn, new_page_id)
        if not page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return

        defaults = {
            'tool_name': tool_name,
            'arguments': arguments,
            'extraction_spec': extraction_spec,
            'status': 'pending',
            'result': result,
            'is_create': False,
            'is_read': False,
            'is_update': False,
            'is_delete': False,
        }

        for key, value in defaults.items():
            page.set_metadata_value(key, value)

        page.reset_connection()
        log(f"Initialized metadata for MCP action request page {new_page_id}")
        trace_out()

    def delete_page_class_information(self):
        trace_in()
        # Metadata stored with page; nothing additional to delete.
        trace_out()

    def _get_page_data(self) -> Dict[str, Any]:
        data = super()._get_page_data()
        data.update(
            {
                "tool_name": self.tool_name,
                "arguments": self.arguments,
                "extraction_spec": self.extraction_spec,
                "status": self.status,
                "result": self.result,
                "is_create": self.is_create,
                "is_read": self.is_read,
                "is_update": self.is_update,
                "is_delete": self.is_delete,
            }
        )
        return data

    def add_badge_headers(self) -> Dict[str, Any]:
        badge_headers = super().add_badge_headers()
        badge_headers['page_summary']['status'] = self.status
        badge_headers['page_summary']['tool_name'] = self.tool_name
        badge_headers['page_summary']['crud'] = {
            "create": bool(self.is_create),
            "read": bool(self.is_read),
            "update": bool(self.is_update),
            "delete": bool(self.is_delete),
        }
        return badge_headers

    def add_lower_content(self) -> list[str]:
        lines: list[str] = []
        if self.arguments:
            pretty = self._pretty_json(self.arguments)
            lines.append(f"Arguments:\n{pretty}")
        if self.result:
            pretty = self._pretty_json(self.result)
            lines.append(f"Result:\n{pretty}")
        return lines

    def get_child_page_data(self) -> Dict[str, Any]:
        """Override to return simplified data for mcp_action_request children: id, tool_name, status."""
        trace_in()
        crud_type = None
        if self.is_create:
            crud_type = 'create'
        elif self.is_read:
            crud_type = 'read'
        elif self.is_update:
            crud_type = 'update'
        elif self.is_delete:
            crud_type = 'delete'
        
        data = {
            "id": self.id,
            "tool_name": self.tool_name if hasattr(self, 'tool_name') and self.tool_name else 'N/A',
            "status": self.status if hasattr(self, 'status') else 'pending',
        }
        if crud_type:
            data["crud_type"] = crud_type
        trace_out()
        return data

    def get_child_row_field_type(self) -> str:
        return 'mcp_action_request'

    def _update_action_request(
        self,
        tool_name: Optional[str] = None,
        arguments: Optional[str] = None,
        extraction_spec: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[str] = None,
        is_create: Optional[str] = None,
        is_read: Optional[str] = None,
        is_update: Optional[str] = None,
        is_delete: Optional[str] = None,
    ) -> bool:
        trace_in()
        metadata = self._get_metadata_dict()
        mutated = False

        if tool_name is not None:
            sanitized = tool_name.strip()
            metadata['tool_name'] = sanitized or None
            mutated = True

        if arguments is not None:
            normalized = self._safe_json_arg(arguments, field_name='arguments')
            if not is_error():
                metadata['arguments'] = normalized
                mutated = True

        if extraction_spec is not None:
            normalized = self._safe_json_arg(extraction_spec, field_name='extraction_spec')
            if not is_error():
                metadata['extraction_spec'] = normalized
                mutated = True

        if result is not None:
            normalized = self._safe_json_arg(result, field_name='result')
            if not is_error():
                metadata['result'] = normalized
                mutated = True

        if status is not None:
            normalized_status = status.strip().lower()
            if normalized_status not in self.VALID_STATUSES:
                warn(f"Invalid status value '{status}'")
                report_error("action", f"Invalid status '{status}'")
            else:
                metadata['status'] = normalized_status
                mutated = True

        boolean_fields = {
            "is_create": is_create,
            "is_read": is_read,
            "is_update": is_update,
            "is_delete": is_delete,
        }

        for column, value in boolean_fields.items():
            if value is not None:
                parsed = self._parse_boolean(value, column)
                if parsed is not None:
                    metadata[column] = bool(parsed)
                    mutated = True

        if is_error():
            trace_out()
            return False

        if not mutated:
            log("No MCP action request fields provided for update")
            trace_out()
            return True

        if self._write_metadata_dict(metadata):
            self._sync_from_metadata(metadata)
            log(f"Updated MCP action request metadata for page {self.id}")

        trace_out()
        return not is_error()

    def _refresh_local_state(self):
        metadata = self._ensure_metadata_defaults()
        self._sync_from_metadata(metadata)

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

    @staticmethod
    def _parse_boolean(value: Any, field_name: str) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {'1', 'true', 'yes', 'y'}:
                return True
            if normalized in {'0', 'false', 'no', 'n'}:
                return False
        warn(f"Invalid boolean for {field_name}: {value}")
        report_error("action", f"Invalid boolean for {field_name}")
        return None

