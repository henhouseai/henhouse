"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                     Line 50
_add_badge_headers()           Line 240
_add_lower_content()           Line 252
_add_page_class_information()  Line 178
_delete_page_class_information() Line 217
_ensure_metadata_defaults()    Line 120
_get_child_page_data()         Line 262
_get_child_row_field_type()    Line 284
_get_children_query()           Line 177
_get_display_name()            Line 164
get_page_data()               Line 203
_parse_boolean()                Line 397
_pretty_json()                  Line 382
_refresh_local_state()          Line 367
_safe_json_arg()                Line 371
_sync_from_metadata()           Line 145
allow_class_inside()           Line 75
allow_duplicate_names()         Line 65
allow_inside_of()              Line 70
allow_null_names()             Line 60
auto_link_name()               Line 68
update_action_request()        Line 286

"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional

from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.page.page import Page
from hh.page.page_registry import get_page
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


@register_page_class('mcp_action_request')
class McpActionRequest(Page):
    """
    A derived Page class for MCP action requests.
    Extends Page with MCP action request specific functionality.
    """
    
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
    
    def __init__(self, id: int):
        """Initialize McpActionRequest by calling parent constructor."""
        # Call parent constructor (Page handles gateway, DB load, cache hydration, and automatically extracts metadata fields as attributes)
        super().__init__(id)
        # Load and sync metadata after parent initialization
        if not is_error() and hasattr(self, 'gateway') and self.gateway and self.gateway.conn:
            if hasattr(self, '_refresh_local_state'):
                self._refresh_local_state()
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """MCP action requests allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """MCP action requests allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """MCP action requests do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """MCP action requests cannot contain any child pages."""
        return False
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """MCP action requests can be inside pages or mcp_request."""
        return parent_class in ('page', 'mcp_request')
    
    def _ensure_metadata_defaults(self) -> Dict[str, Any]:
        """Ensure metadata has all required fields with defaults."""
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
        """Sync instance attributes from metadata dictionary."""
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
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Return query to get mcp_action children."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'mcp_action_request' ORDER BY id",
            [parent_id]
        )

    def _get_display_name(self) -> str:
        """
        Override to return tool-based display name when name is None.
        """
        if self.name:
            return self.name
        
        tool_name = self.tool_name if hasattr(self, 'tool_name') and self.tool_name else 'unknown'
        status = self.status if hasattr(self, 'status') else 'pending'
        display_name = f"{tool_name} ({status})"
        self.display_name = display_name
        self._flag_cache_refresh()
        return display_name

    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """Hook called after page creation to initialize MCP action request metadata."""
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

        page = get_page(new_page_id)
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
            # Also set the attribute directly on the page instance since it was already hydrated
            setattr(page, key, value)

        log(f"Initialized metadata for MCP action request page {new_page_id}")
        trace_out()


    def get_page_data(self) -> Dict[str, Any]:
        """Override to add MCP action request specific fields to page data."""
        data = super().get_page_data()
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

    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add status, tool_name, and CRUD flags to badge headers."""
        badge_headers = super()._add_badge_headers()
        badge_headers['page_summary']['status'] = self.status
        badge_headers['page_summary']['tool_name'] = self.tool_name
        badge_headers['page_summary']['crud'] = {
            "create": bool(self.is_create),
            "read": bool(self.is_read),
            "update": bool(self.is_update),
            "delete": bool(self.is_delete),
        }
        return badge_headers

    def _add_lower_content(self) -> list[str]:
        """Add arguments and result JSON to lower content section."""
        lines: list[str] = []
        if self.arguments:
            pretty = self._pretty_json(self.arguments)
            lines.append(f"Arguments:\n{pretty}")
        if self.result:
            pretty = self._pretty_json(self.result)
            lines.append(f"Result:\n{pretty}")
        return lines

    def _get_child_page_data(self) -> Dict[str, Any]:
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

    def _get_child_row_field_type(self) -> str:
        """Return field type for mcp_action_request rows."""
        return 'mcp_action_request'

    def update_action_request(
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
        """Update MCP action request metadata fields."""
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
            self.flag_page_modification("action request updated")

        trace_out()
        return not is_error()

    def _refresh_local_state(self):
        """Refresh instance state from metadata."""
        metadata = self._ensure_metadata_defaults()
        self._sync_from_metadata(metadata)

    @staticmethod
    def _safe_json_arg(value: Optional[str], field_name: str = 'json') -> Optional[str]:
        """Safely parse and normalize JSON argument."""
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
        """Format JSON value as pretty-printed string."""
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
        """Parse boolean value from various formats."""
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

