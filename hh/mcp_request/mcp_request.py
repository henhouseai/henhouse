"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                     Line 50
_add_badge_headers()           Line 256
_add_lower_content()           Line 271
_add_page_class_information()  Line 192
_delete_page_class_information() Line 232
_ensure_metadata_defaults()    Line 128
_get_child_page_data()         Line 281
_get_child_row_field_type()    Line 301
_get_children_query()           Line 172
_get_display_name()            Line 159
get_page_data()               Line 234
_pretty_json()                  Line 395
_refresh_local_state()         Line 377
_safe_json_arg()                Line 381
_sync_from_metadata()          Line 157
allow_class_inside()           Line 75
allow_duplicate_names()         Line 65
allow_inside_of()              Line 70
allow_null_names()             Line 60
auto_link_name()               Line 68
update_request()               Line 303

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


@register_page_class('mcp_request')
class McpRequest(Page):
    """
    A derived Page class for MCP requests.
    Extends Page with MCP request specific functionality.
    """
    
    VALID_STATUSES = {
        'pending',
        'approved',
        'executing',
        'completed',
        'failed',
        'cancelled',
        'rolled_back',
    }

    INT_FIELDS = [
        'create_request',
        'read_request',
        'update_request',
        'delete_request',
        'create_executed',
        'read_executed',
        'update_executed',
        'delete_executed',
    ]
    
    def __init__(self, id: int):
        """Initialize McpRequest by calling parent constructor."""
        # Call parent constructor (Page handles gateway, DB load, cache hydration, and automatically extracts metadata fields as attributes)
        super().__init__(id)
        # Load and sync metadata after parent initialization
        if not is_error() and hasattr(self, 'gateway') and self.gateway and self.gateway.conn:
            if hasattr(self, '_refresh_local_state'):
                self._refresh_local_state()
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """MCP requests allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """MCP requests allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """MCP requests do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """MCP requests can contain pages or mcp_action_request."""
        return target_class in ('page', 'mcp_action_request')
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """MCP requests can only be inside pages."""
        return parent_class == 'page'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for MCP request section header."""
        return ['MCP Requests']

    def _ensure_metadata_defaults(self) -> Dict[str, Any]:
        """Ensure metadata has all required fields with defaults."""
        metadata = self._get_metadata_dict()
        mutated = False

        for field in ['input_request', 'output_response']:
            if field not in metadata:
                metadata[field] = None
                mutated = True

        for field in self.INT_FIELDS:
            value = metadata.get(field)
            try:
                converted = int(value) if value is not None else 0
            except (TypeError, ValueError):
                converted = 0
            if value != converted:
                metadata[field] = converted
                mutated = True

        status = metadata.get('status')
        normalized_status = status.strip().lower() if isinstance(status, str) else None
        if normalized_status not in self.VALID_STATUSES:
            metadata['status'] = 'pending'
            mutated = True

        if mutated:
            self._write_metadata_dict(metadata)
        return metadata

    def _sync_from_metadata(self, metadata: Dict[str, Any]) -> None:
        """Sync instance attributes from metadata dictionary."""
        self.input_request = metadata.get('input_request')
        self.output_response = metadata.get('output_response')
        self.create_request = int(metadata.get('create_request') or 0)
        self.read_request = int(metadata.get('read_request') or 0)
        self.update_request_count = int(metadata.get('update_request') or 0)
        self.delete_request = int(metadata.get('delete_request') or 0)
        self.create_executed = int(metadata.get('create_executed') or 0)
        self.read_executed = int(metadata.get('read_executed') or 0)
        self.update_executed = int(metadata.get('update_executed') or 0)
        self.delete_executed = int(metadata.get('delete_executed') or 0)
        status = metadata.get('status')
        self.status = status if isinstance(status, str) and status in self.VALID_STATUSES else 'pending'

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Return query to get mcp_request children."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'mcp_request' ORDER BY id",
            [parent_id]
        )

    def _get_display_name(self) -> str:
        """
        Override to return status-based display name when name is None.
        """
        if self.name:
            return self.name
        
        status = self.status if hasattr(self, 'status') else 'pending'
        display_name = f"MCP Request ({status})"
        self.display_name = display_name
        self._flag_cache_refresh()
        return display_name

    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """Hook called after page creation to initialize MCP request metadata."""
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return

        input_request = cls._safe_json_arg(gateway.get_arg('input_request'))
        output_response = cls._safe_json_arg(gateway.get_arg('output_response'))

        page = get_page(new_page_id)
        if not page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return

        defaults = {
            'input_request': input_request,
            'output_response': output_response,
            'create_request': 0,
            'read_request': 0,
            'update_request': 0,
            'delete_request': 0,
            'create_executed': 0,
            'read_executed': 0,
            'update_executed': 0,
            'delete_executed': 0,
            'status': 'pending',
        }

        for key, value in defaults.items():
            page.set_metadata_value(key, value)
            # Also set the attribute directly on the page instance since it was already hydrated
            setattr(page, key, value)

        log(f"Initialized metadata for MCP request page {new_page_id}")
        trace_out()


    def get_page_data(self) -> Dict[str, Any]:
        """Override to add MCP request specific fields to page data."""
        data = super().get_page_data()
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

    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add status and request/executed counts to badge headers."""
        badge_headers = super()._add_badge_headers()
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

    def _add_lower_content(self) -> list[str]:
        """Add input_request and output_response JSON to lower content section."""
        lines: list[str] = []
        if self.input_request:
            pretty = self._pretty_json(self.input_request)
            lines.append(f"Input Request:\n{pretty}")
        if self.output_response:
            pretty = self._pretty_json(self.output_response)
            lines.append(f"Output Response:\n{pretty}")
        return lines

    def _get_child_page_data(self) -> Dict[str, Any]:
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

    def _get_child_row_field_type(self) -> str:
        """Return field type for mcp_request rows."""
        return 'mcp_request'

    def update_request(
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
        """Update MCP request metadata fields."""
        trace_in()
        metadata = self._get_metadata_dict()
        mutated = False

        if input_request is not None:
            normalized = self._safe_json_arg(input_request, field_name='input_request')
            if not is_error():
                metadata['input_request'] = normalized
                mutated = True

        if output_response is not None:
            normalized = self._safe_json_arg(output_response, field_name='output_response')
            if not is_error():
                metadata['output_response'] = normalized
                mutated = True

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
                    metadata[column] = converted
                    mutated = True
                except (TypeError, ValueError):
                    warn(f"Invalid integer for {column}: {value}")
                    report_error("action", f"Invalid integer for {column}")

        if status is not None:
            normalized_status = status.strip().lower()
            if normalized_status not in self.VALID_STATUSES:
                warn(f"Invalid status value '{status}'")
                report_error("action", f"Invalid status '{status}'")
            else:
                metadata['status'] = normalized_status
                mutated = True

        if is_error():
            trace_out()
            return False

        if not mutated:
            log("No MCP request fields provided for update")
            trace_out()
            return True

        if self._write_metadata_dict(metadata):
            self._sync_from_metadata(metadata)
            log(f"Updated MCP request metadata for page {self.id}")
            self.flag_page_modification("request updated")

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

