"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                          Line 79
_add_badge_headers()                Line 230
_add_page_class_information()       Line 105
_delete_page_class_information()    Line 187
_get_child_page_data()               Line 216
_get_display_name()                 Line 195
_load_work_metadata()               Line 320
_modify_work_sort_order_internal()   Line 464
_sort_meta_dict()                   Line 98
_validate_is_string()               Line 371
allow_inside_of()                   Line 93
finalize_response_http()             Line 302
get_page_data()                     Line 306
modify_work_sort_order()            Line 453
modify_work_status()                Line 985
work_add()                          Line 660
work_add_log()                      Line 741
work_remove()                       Line 784
work_set()                          Line 861
work_set_all()                      Line 935

"""

from __future__ import annotations
import json
import datetime as dt
from typing import Dict, Any, List
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page import Page
from hh.page.page_registry import get_page


def _format_relative_time(timestamp_str: str) -> str:
    """Convert ISO timestamp to relative time string (e.g., '3 days ago')."""
    trace_in()
    try:
        if not timestamp_str:
            trace_out()
            return ''
        # Parse ISO timestamp
        timestamp = dt.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = dt.datetime.now(timestamp.tzinfo if timestamp.tzinfo else None)
        delta = now - timestamp
        
        # Calculate time differences
        seconds = int(delta.total_seconds())
        if seconds < 60:
            result = 'just now' if seconds < 10 else f'{seconds} seconds ago'
        elif seconds < 3600:
            minutes = seconds // 60
            result = '1 minute ago' if minutes == 1 else f'{minutes} minutes ago'
        elif seconds < 86400:
            hours = seconds // 3600
            result = '1 hour ago' if hours == 1 else f'{hours} hours ago'
        elif seconds < 604800:
            days = seconds // 86400
            result = '1 day ago' if days == 1 else f'{days} days ago'
        elif seconds < 2592000:
            weeks = seconds // 604800
            result = '1 week ago' if weeks == 1 else f'{weeks} weeks ago'
        elif seconds < 31536000:
            months = seconds // 2592000
            result = '1 month ago' if months == 1 else f'{months} months ago'
        else:
            years = seconds // 31536000
            result = '1 year ago' if years == 1 else f'{years} years ago'
        log(f"Converted timestamp '{timestamp_str}' to '{result}'")
        trace_out()
        return result
    except Exception as e:
        warn(f"Error formatting relative time for '{timestamp_str}': {e}")
        trace_out()
        return timestamp_str

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


def _parse_metadata(metadata: Any) -> Dict[str, Any]:
    """Parse metadata from various formats (bytes, str, dict) into a dict."""
    if metadata in (None, '', b''):
        return {}
    try:
        if isinstance(metadata, (bytes, bytearray)):
            metadata = metadata.decode('utf-8')
        if isinstance(metadata, str):
            parsed = json.loads(metadata)
        else:
            parsed = metadata
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, TypeError):
        pass
    return {}


def _sort_meta_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sort a metadata dictionary by keys (case-insensitive)."""
    if not isinstance(data, dict):
        return {}
    return {key: data[key] for key in sorted(data.keys(), key=lambda k: k.lower())}


class WorkPage(Page):
    """
    Abstract base class for work entities (work dockets, asks, tasks, steps).
    Provides shared functionality for status, meta, sort_order, and timestamps.
    This class should never be instantiated directly - only inherited from.
    """
    
    def __init__(self, id: int):
        """Initialize WorkPage by calling parent constructor."""
        # Call parent constructor first (Page handles gateway, DB load, cache hydration, and automatically extracts metadata fields as attributes)
        # The _after_metadata_extraction() hook will be called automatically to load work metadata
        super().__init__(id)
    
    def _after_metadata_extraction(self) -> None:
        """Override hook to load and normalize work-specific metadata after parent extracts metadata fields."""
        # Page.__init__() already extracted metadata fields (status, meta, sort_order, etc.) as attributes
        # This method normalizes them and sets defaults if needed
        if not is_error() and hasattr(self, 'gateway') and self.gateway and self.gateway.conn:
            # Call the method to load work metadata
            if hasattr(self, '_load_work_metadata'):
                self._load_work_metadata()
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """WorkPage is abstract - never allow it to be created directly."""
        return False
    
    @staticmethod
    def _sort_meta_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sort a metadata dictionary by keys (case-insensitive)."""
        if not isinstance(data, dict):
            return {}
        return {key: data[key] for key in sorted(data.keys(), key=lambda k: k.lower())}
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize metadata for work entities.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return
        
        status = gateway.get_arg('status') or 'todo'
        meta_arg = gateway.get_arg('meta')
        if meta_arg is True:
            meta_arg = "{}"
        user_meta: Dict[str, Any] = {}
        if meta_arg and isinstance(meta_arg, str) and meta_arg.strip():
            try:
                user_meta = json.loads(meta_arg)
                if not isinstance(user_meta, dict):
                    user_meta = {}
            except json.JSONDecodeError as exc:
                warn(f"Invalid JSON provided for work meta: {exc}")
                report_error("action", f"Invalid JSON for meta: {exc}")
        elif isinstance(meta_arg, dict):
            user_meta = meta_arg

        if is_error():
            trace_out()
            return

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available for add_page_class_information")
            trace_out()
            return
        
        parent_id = None
        class_name = None
        try:
            parent_results = gateway.conn.read("SELECT parent, class FROM pages WHERE id = %s", [new_page_id])
            if parent_results:
                parent_id = parent_results[0].get('parent')
                class_name = parent_results[0].get('class')
        except Exception as exc:
            debug(f"Failed to get parent/class for page {new_page_id}: {exc}")

        max_order = 0
        if parent_id is not None and class_name:
            sibling_rows = gateway.conn.read(
                "SELECT metadata FROM pages WHERE parent = %s AND class = %s",
                [parent_id, class_name],
            )
            for row in sibling_rows:
                metadata = _parse_metadata(row.get('metadata'))
                try:
                    current = int(metadata.get('sort_order') or 0)
                    if current > max_order:
                        max_order = current
                except (TypeError, ValueError):
                    continue

        new_sort_order = max_order + 1
        new_page = get_page(new_page_id)
        if not new_page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return

        now_iso = dt.datetime.now().isoformat()
        new_page.set_metadata_value('status', status)
        new_page.set_metadata_value('sort_order', new_sort_order)
        new_page.set_metadata_value('started_ts', now_iso)
        new_page.set_metadata_value('ended_ts', None)
        new_page.set_metadata_value('meta', user_meta or {})
        new_page.status = status
        new_page.sort_order = new_sort_order
        new_page.started_ts = now_iso
        new_page.ended_ts = None
        new_page.meta = json.dumps(user_meta or {}, ensure_ascii=False)
        trace_out()
    
    
    def _get_display_name(self) -> str:
        """
        Override to use class name instead of 'Page' when name is missing.
        Formats class name nicely: 'work_docket' -> 'Work Docket 699'
        """
        # Check if field is already populated
        if hasattr(self, 'display_name') and self.display_name:
            return self.display_name
        # Field is empty, compute it
        if self.name:
            display_name = self.name
        else:
            # Format class name: convert underscores to spaces and capitalize words
            class_name = self.class_name or 'page'
            formatted_class = ' '.join(word.capitalize() for word in class_name.split('_'))
            display_name = f"{formatted_class} {self.id}"
        self.display_name = display_name
        # Flag that cache needs refresh since we just computed
        self._flag_cache_refresh()
        return display_name
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return simplified data for work page children: id, name, sort_order, meta, timestamps."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "sort_order": self.sort_order if hasattr(self, 'sort_order') else 0,
            "meta": self.meta if hasattr(self, 'meta') else '',
            "started_ts": str(self.started_ts) if hasattr(self, 'started_ts') and self.started_ts else None,
            "ended_ts": str(self.ended_ts) if hasattr(self, 'ended_ts') and self.ended_ts else None
        }
        trace_out()
        return data
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add work-specific fields to page_summary and add separate work badges."""
        trace_in()
        # Get base badge headers from parent
        badge_headers = super()._add_badge_headers()
        
        # Add work fields to page_summary badge (like mcp_request does with status)
        badge_headers['page_summary']['status'] = self.status if hasattr(self, 'status') else 'todo'
        badge_headers['page_summary']['sort_order'] = self.sort_order if hasattr(self, 'sort_order') else 0
        if hasattr(self, 'started_ts') and self.started_ts:
            badge_headers['page_summary']['started_ts'] = _format_relative_time(str(self.started_ts))
        else:
            badge_headers['page_summary']['started_ts'] = None
        if hasattr(self, 'ended_ts') and self.ended_ts:
            badge_headers['page_summary']['ended_ts'] = _format_relative_time(str(self.ended_ts))
        else:
            badge_headers['page_summary']['ended_ts'] = None
        
        # Add work meta badge as generic badge
        # Get full metadata dict to access protected namespaces
        metadata = self._get_metadata_dict()
        
        # Extract meta bucket (user-defined key-value pairs)
        meta_dict = {}
        if hasattr(self, 'meta_dict') and self.meta_dict:
            meta_dict = self.meta_dict
        elif hasattr(self, 'meta') and self.meta:
            if isinstance(self.meta, str):
                try:
                    meta_dict = json.loads(self.meta)
                except (ValueError, TypeError):
                    meta_dict = {}
            elif isinstance(self.meta, dict):
                meta_dict = self.meta
        
        # Extract protected namespaces from full metadata
        log_list = metadata.get('log', [])
        files_touched_dict = metadata.get('files_touched', {})
        deviations_dict = metadata.get('deviations', {})
        
        # Create one badge per log entry, converting timestamp to relative time
        if log_list and isinstance(log_list, list):
            for i, log_entry in enumerate(log_list):
                if isinstance(log_entry, dict):
                    # Create a copy of the log entry
                    log_entry_copy = dict(log_entry)
                    # Extract and convert timestamp
                    timestamp = log_entry_copy.pop('timestamp', '')
                    relative_time = _format_relative_time(timestamp) if timestamp else ''
                    
                    # Sort remaining keys alphabetically
                    sorted_keys = sorted([k for k in log_entry_copy.keys()], key=lambda x: x.lower())
                    sorted_entry = {k: log_entry_copy[k] for k in sorted_keys}
                    
                    # Create badge dict with header row first (work_log field config + relative_time)
                    badge_data = {'work_log': relative_time}
                    # Add rest of sorted log data
                    badge_data.update(sorted_entry)
                    badge_headers[f'work_log_{i}'] = badge_data
        
        # Create separate badges for meta, files_touched, and deviations (only if non-empty)
        if meta_dict and isinstance(meta_dict, dict) and len(meta_dict) > 0:
            # Sort keys alphabetically
            sorted_keys = sorted(meta_dict.keys(), key=lambda x: x.lower())
            sorted_meta = {k: meta_dict[k] for k in sorted_keys}
            # Create badge dict with header row first (work_meta field config + blank value)
            badge_data = {'work_meta': ''}
            badge_data.update(sorted_meta)
            badge_headers['work_meta'] = badge_data
        
        if files_touched_dict and isinstance(files_touched_dict, dict) and len(files_touched_dict) > 0:
            # Sort keys alphabetically
            sorted_keys = sorted(files_touched_dict.keys(), key=lambda x: x.lower())
            sorted_files = {k: files_touched_dict[k] for k in sorted_keys}
            # Create badge dict with header row first (work_files_touched field config + count)
            badge_data = {'work_files_touched': str(len(files_touched_dict))}
            badge_data.update(sorted_files)
            badge_headers['work_files_touched'] = badge_data
        
        if deviations_dict and isinstance(deviations_dict, dict) and len(deviations_dict) > 0:
            # Sort keys alphabetically
            sorted_keys = sorted(deviations_dict.keys(), key=lambda x: x.lower())
            sorted_deviations = {k: deviations_dict[k] for k in sorted_keys}
            # Create badge dict with header row first (work_deviations field config + count)
            badge_data = {'work_deviations': str(len(deviations_dict))}
            badge_data.update(sorted_deviations)
            badge_headers['work_deviations'] = badge_data
        
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """WorkPage keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def get_page_data(self) -> Dict[str, Any]:
        """Override to add work entity specific fields to full page data."""
        trace_in()
        # Get full page data from parent
        data = super().get_page_data()
        # Add work entity specific fields
        data['status'] = self.status if hasattr(self, 'status') else 'todo'
        data['meta'] = self.meta if hasattr(self, 'meta') else ''
        data['sort_order'] = self.sort_order if hasattr(self, 'sort_order') else 0
        data['started_ts'] = str(self.started_ts) if hasattr(self, 'started_ts') and self.started_ts else None
        data['ended_ts'] = str(self.ended_ts) if hasattr(self, 'ended_ts') and self.ended_ts else None
        trace_out()
        return data
    
    def _load_work_metadata(self):
        """Load work-specific metadata after parent Page initialization."""
        trace_in()
        metadata = self._get_metadata_dict()
        mutated = False
        if 'status' not in metadata:
            metadata['status'] = 'todo'
            mutated = True
        if 'sort_order' not in metadata:
            metadata['sort_order'] = 0
            mutated = True
        if 'meta' not in metadata or metadata['meta'] in (None, ''):
            metadata['meta'] = {}
            mutated = True
        # Initialize protected namespaces if they don't exist
        if 'log' not in metadata:
            metadata['log'] = []
            mutated = True
        if 'files_touched' not in metadata:
            metadata['files_touched'] = {}
            mutated = True
        if 'deviations' not in metadata:
            metadata['deviations'] = {}
            mutated = True
        self.status = metadata.get('status') or 'todo'
        self.sort_order = metadata.get('sort_order') or 0
        self.started_ts = metadata.get('started_ts')
        self.ended_ts = metadata.get('ended_ts')
        raw_meta_bucket = metadata.get('meta') or {}
        if isinstance(raw_meta_bucket, str):
            try:
                raw_meta_bucket = json.loads(raw_meta_bucket)
            except (ValueError, TypeError):
                raw_meta_bucket = {}
        elif not isinstance(raw_meta_bucket, dict):
            raw_meta_bucket = {}
        sorted_meta_bucket = self._sort_meta_dict(raw_meta_bucket)
        if metadata.get('meta') != sorted_meta_bucket:
            metadata['meta'] = sorted_meta_bucket
            mutated = True
        if mutated:
            self._write_metadata_dict(metadata)
        self.meta_dict = sorted_meta_bucket
        self.meta = json.dumps(sorted_meta_bucket, ensure_ascii=False) if sorted_meta_bucket else '{}'
        log(
            f"{self.__class__.__name__} {self.id} loaded from metadata: "
            f"status='{self.status}', sort_order={self.sort_order}"
        )
        trace_out()
    
    @staticmethod
    def _validate_is_string(value: Any) -> bool:
        """Validate that a value is a simple string."""
        return isinstance(value, str)
    
    @staticmethod
    def _normalize_field_name(field: str) -> str:
        """Normalize field name to canonical form. Maps 'files', 'files_touched', 'files-touched' to 'files_touched'."""
        if field in ('files', 'files_touched', 'files-touched'):
            return 'files_touched'
        return field
    
    def _modify_work_sort_order_internal(self, page_id: int, new_sort_order: int) -> bool:
        """Helper method to update a single page's sort_order using JSON_SET()."""
        trace_in()
        log(f"Updating page {page_id} sort_order to {new_sort_order} using JSON_SET")
        
        # Check current value first to handle "already correct" case
        current_result = self.gateway.conn.read(
            "SELECT COALESCE(CAST(JSON_EXTRACT(metadata, '$.sort_order') AS UNSIGNED), 0) AS current_sort FROM pages WHERE id = %s",
            [page_id]
        )
        
        if not current_result:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
            trace_out()
            return False
        
        current_sort = current_result[0].get('current_sort', 0)
        if current_sort == new_sort_order:
            log(f"Page {page_id} already has sort_order {new_sort_order}, skipping update")
            trace_out()
            return True
        
        affected = self.gateway.conn.update(
            "UPDATE pages SET metadata = JSON_SET(COALESCE(metadata, '{}'), '$.sort_order', %s) WHERE id = %s",
            (new_sort_order, page_id),
        )
        
        if affected == 0:
            # Verify if the value was actually set correctly (might be 0 rows if value was already correct)
            verify_result = self.gateway.conn.read(
                "SELECT COALESCE(CAST(JSON_EXTRACT(metadata, '$.sort_order') AS UNSIGNED), 0) AS verify_sort FROM pages WHERE id = %s",
                [page_id]
            )
            if verify_result:
                verify_sort = verify_result[0].get('verify_sort', 0)
                if verify_sort == new_sort_order:
                    log(f"Page {page_id} already had sort_order {new_sort_order} (UPDATE returned 0 rows but value is correct)")
                    # Still mark as stale
                    page_obj = get_page(page_id=page_id)
                    if page_obj:
                        page_obj.flag_page_modification("child page modified")
                    trace_out()
                    return True
            
            warn(f"Failed to update sort_order for page {page_id} (expected {new_sort_order}, got {current_sort}, verify={verify_result[0].get('verify_sort', 'unknown') if verify_result else 'no verify'})")
            report_error("action", f"Failed to update sort_order for page {page_id}")
            trace_out()
            return False
        
        # Mark this page as stale (use "child page modified" to prevent recursive parent flagging)
        page_obj = get_page(page_id=page_id)
        if page_obj:
            page_obj.flag_page_modification("child page modified")
        else:
            warn(f"Could not get page {page_id} to flag modification")
        
        log(f"Successfully updated page {page_id} sort_order from {current_sort} to {new_sort_order}")
        trace_out()
        return True
    
    def modify_work_sort_order(self, sort_order: int) -> bool:
        """Modify the sort_order of this work entity, reflowing all siblings within the same parent."""
        trace_in()
        log(f"Starting sort_order modification for page {self.id}: {self.sort_order} -> {sort_order}")
        
        # Get parent page ID
        parent_id = None
        if not is_error():
            parent_results = self.gateway.conn.read("SELECT parent FROM pages WHERE id = %s", [self.id])
            if parent_results and parent_results[0].get('parent') is not None:
                parent_id = int(parent_results[0]['parent'])
            else:
                warn(f"Could not determine parent for page {self.id}")
                report_error("action", f"Could not determine parent for page {self.id}")
        
        if not is_error() and parent_id:
            class_name = self.class_name
            # Order siblings by sort_order from metadata, not by id
            siblings = self.gateway.conn.read(
                """SELECT id, metadata, 
                   COALESCE(CAST(JSON_EXTRACT(metadata, '$.sort_order') AS UNSIGNED), 0) AS sort_order_val
                   FROM pages 
                   WHERE parent = %s AND class = %s 
                   ORDER BY sort_order_val, id""",
                [parent_id, class_name],
            )
            if not siblings:
                warn(f"No siblings found for page {self.id} under parent {parent_id}")
                report_error("action", f"No siblings found for page {self.id}")
            else:
                siblings_with_meta = []
                for row in siblings:
                    metadata = _parse_metadata(row.get('metadata'))
                    current_order = metadata.get('sort_order') or 0
                    try:
                        current_order = int(current_order)
                    except (TypeError, ValueError):
                        current_order = 0
                    siblings_with_meta.append({
                        'page_id': row['id'],
                        'sort_order': current_order,
                        'metadata': metadata,
                    })
                
                target_entry = next((s for s in siblings_with_meta if s['page_id'] == self.id), None)
                if target_entry is None:
                    target_entry = {
                        'page_id': self.id,
                        'sort_order': self.sort_order or 0,
                        'metadata': self._get_metadata_dict(),
                    }
                    siblings_with_meta.append(target_entry)
                    log(f"Page {self.id} not found in siblings metadata, adding placeholder")
                
                siblings_without_target = [s for s in siblings_with_meta if s['page_id'] != self.id]
                
                # Valid positions are 1 through len(siblings_without_target) + 1
                # (1 = beginning, len+1 = end)
                max_valid_position = len(siblings_without_target) + 1
                
                if sort_order <= 0:
                    new_pos = 0
                    log(f"Position {sort_order} clamped to beginning (0)")
                elif sort_order > max_valid_position:
                    new_pos = len(siblings_without_target)
                    log(f"Position {sort_order} clamped to end ({new_pos}, max valid: {max_valid_position})")
                else:
                    new_pos = sort_order - 1
                    log(f"Position {sort_order} -> index {new_pos} (max valid: {max_valid_position})")
                
                siblings_without_target.insert(new_pos, target_entry)
                new_order = siblings_without_target
                
                # Check if order of pages changed
                order_changed = any(
                    original['page_id'] != updated['page_id']
                    for original, updated in zip(siblings_with_meta, new_order)
                ) or (len(siblings_with_meta) != len(new_order))
                
                # Also check if target page's sort_order value changed
                if not order_changed:
                    target_new_position = new_pos + 1  # Convert 0-based index to 1-based position
                    target_old_sort_order = target_entry.get('sort_order', 0)
                    if target_new_position != target_old_sort_order:
                        order_changed = True
                        log(f"Target page sort_order changed: {target_old_sort_order} -> {target_new_position}")
                
                if not order_changed:
                    log("Sort order unchanged after reflow, no update needed")
                    trace_out()
                    return True
                
                log(f"Reflowing {len(new_order)} siblings under parent {parent_id}")
                # Update each affected sibling using helper method (only if sort_order changed)
                for index, sibling in enumerate(new_order):
                    new_sort = index + 1
                    old_sort = sibling.get('sort_order', 0)
                    # Only update and flag if the sort_order actually changed
                    if old_sort != new_sort:
                        success = self._modify_work_sort_order_internal(sibling['page_id'], new_sort)
                        if not success:
                            break
                    if sibling['page_id'] == self.id:
                        self.sort_order = new_sort
                
                # Flag parent page as stale (use "child page modified" to prevent recursive parent flagging)
                if not is_error():
                    parent_page = get_page(page_id=parent_id)
                    if parent_page:
                        parent_page.flag_page_modification("child page modified")
                    else:
                        warn(f"Could not get parent page {parent_id} to flag modification")
                
                if not is_error():
                    log(f"Successfully updated ordering for {len(new_order)} siblings")
        
        trace_out()
        return not is_error()
    
    def work_add(self, data: Dict[str, str], field: str = "meta") -> bool:
        """Add key-value pairs to specified field dictionary. Errors if any key already exists."""
        trace_in()
        # Normalize field name (e.g., 'files' -> 'files_touched')
        field = self._normalize_field_name(field)
        log(f"Adding to {field} for page {self.id}")
        
        if field not in ("files_touched", "deviations", "meta"):
            warn(f"Invalid field: {field}. Must be 'files_touched', 'deviations', or 'meta'")
            report_error("action", f"Invalid field: {field}")
            trace_out()
            return False
        
        if not isinstance(data, dict):
            warn(f"Data must be a dictionary, got {type(data)}")
            report_error("action", "Data must be a dictionary")
            trace_out()
            return False
        
        for key, value in data.items():
            if not self._validate_is_string(key):
                warn(f"{field} key must be a string, got {type(key)}")
                report_error("action", f"{field} key must be a string, got {type(key)}")
                trace_out()
                return False
            if not self._validate_is_string(value):
                warn(f"{field} value must be a string, got {type(value)}")
                report_error("action", f"{field} value must be a string, got {type(value)}")
                trace_out()
                return False
        
        if is_error():
            trace_out()
            return False
        
        metadata = self._get_metadata_dict()
        
        if field == "meta":
            current_field = metadata.get('meta', {})
            if isinstance(current_field, str):
                try:
                    current_field = json.loads(current_field)
                except (ValueError, TypeError):
                    current_field = {}
            if not isinstance(current_field, dict):
                current_field = {}
        else:
            current_field = metadata.get(field, {})
            if not isinstance(current_field, dict):
                current_field = {}
        
        duplicates = [k for k in data.keys() if k in current_field]
        if duplicates:
            warn(f"{field} keys already exist: {duplicates}")
            report_error("action", f"{field} keys already exist: {duplicates}")
            trace_out()
            return False
        
        current_field.update(data)
        
        if field == "meta":
            sorted_field = self._sort_meta_dict(current_field)
            metadata['meta'] = sorted_field
            if self._write_metadata_dict(metadata):
                self.meta_dict = sorted_field
                self.meta = json.dumps(sorted_field, ensure_ascii=False) if sorted_field else '{}'
                log(f"Successfully added {len(data)} keys to {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        else:
            metadata[field] = current_field
            if self._write_metadata_dict(metadata):
                log(f"Successfully added {len(data)} entries to {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        
        trace_out()
        return not is_error()
    
    def work_add_log(self, data: Dict[str, str]) -> bool:
        """Append a log entry to the log list with automatic timestamp."""
        trace_in()
        log(f"Adding log entry for page {self.id}")
        
        if not isinstance(data, dict):
            warn(f"Log entry must be a dictionary, got {type(data)}")
            report_error("action", "Log entry must be a dictionary")
            trace_out()
            return False
        
        for key, value in data.items():
            if not self._validate_is_string(key):
                warn(f"Log entry key must be a string, got {type(key)}")
                report_error("action", f"Log entry key must be a string, got {type(key)}")
                trace_out()
                return False
            if not self._validate_is_string(value):
                warn(f"Log entry value for key '{key}' must be a string, got {type(value)}")
                report_error("action", f"Log entry value for key '{key}' must be a string")
                trace_out()
                return False
        
        if is_error():
            trace_out()
            return False
        
        metadata = self._get_metadata_dict()
        log_list = metadata.get('log', [])
        if not isinstance(log_list, list):
            log_list = []
        
        entry_copy = dict(data)
        entry_copy['timestamp'] = dt.datetime.now().isoformat()
        
        log_list.append(entry_copy)
        metadata['log'] = log_list
        
        if self._write_metadata_dict(metadata):
            log(f"Successfully added log entry to page {self.id}")
            self.flag_page_modification("meta updated")
        else:
            warn(f"Failed to write log entry for page {self.id}")
            report_error("action", "Failed to write log entry")
        
        trace_out()
        return not is_error()
    
    def work_remove(self, keys: List[str], field: str = "meta") -> bool:
        """Remove specified keys from specified field dictionary. Errors if any key doesn't exist."""
        trace_in()
        # Normalize field name (e.g., 'files' -> 'files_touched')
        field = self._normalize_field_name(field)
        log(f"Removing from {field} for page {self.id}")
        
        if field not in ("files_touched", "deviations", "meta"):
            warn(f"Invalid field: {field}. Must be 'files_touched', 'deviations', or 'meta'")
            report_error("action", f"Invalid field: {field}")
            trace_out()
            return False
        
        if not isinstance(keys, list):
            warn(f"Keys must be a list, got {type(keys)}")
            report_error("action", "Keys must be a list")
            trace_out()
            return False
        
        for key in keys:
            if not self._validate_is_string(key):
                warn(f"Key must be a string, got {type(key)}")
                report_error("action", f"Key must be a string, got {type(key)}")
                trace_out()
                return False
        
        if is_error():
            trace_out()
            return False
        
        metadata = self._get_metadata_dict()
        
        if field == "meta":
            current_field = metadata.get('meta', {})
            if isinstance(current_field, str):
                try:
                    current_field = json.loads(current_field)
                except (ValueError, TypeError):
                    current_field = {}
            if not isinstance(current_field, dict):
                current_field = {}
        else:
            current_field = metadata.get(field, {})
            if not isinstance(current_field, dict):
                current_field = {}
        
        missing = [k for k in keys if k not in current_field]
        if missing:
            warn(f"Keys not found in {field}: {missing}")
            report_error("action", f"Keys not found in {field}: {missing}")
            trace_out()
            return False
        
        for key in keys:
            current_field.pop(key, None)
        
        if field == "meta":
            sorted_field = self._sort_meta_dict(current_field)
            metadata['meta'] = sorted_field
            if self._write_metadata_dict(metadata):
                self.meta_dict = sorted_field
                self.meta = json.dumps(sorted_field, ensure_ascii=False) if sorted_field else '{}'
                log(f"Successfully removed {len(keys)} keys from {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        else:
            metadata[field] = current_field
            if self._write_metadata_dict(metadata):
                log(f"Successfully removed {len(keys)} keys from {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        
        trace_out()
        return not is_error()
    
    def work_set(self, data: Dict[str, str], field: str = "meta") -> bool:
        """Add/update key-value pairs in specified field dictionary. No error if keys already exist, leaves other keys unchanged."""
        trace_in()
        # Normalize field name (e.g., 'files' -> 'files_touched')
        field = self._normalize_field_name(field)
        log(f"Setting {field} for page {self.id}")
        
        if field not in ("files_touched", "deviations", "meta"):
            warn(f"Invalid field: {field}. Must be 'files_touched', 'deviations', or 'meta'")
            report_error("action", f"Invalid field: {field}")
            trace_out()
            return False
        
        if not isinstance(data, dict):
            warn(f"Data must be a dictionary, got {type(data)}")
            report_error("action", "Data must be a dictionary")
            trace_out()
            return False
        
        for key, value in data.items():
            if not self._validate_is_string(key):
                warn(f"{field} key must be a string, got {type(key)}")
                report_error("action", f"{field} key must be a string, got {type(key)}")
                trace_out()
                return False
            if not self._validate_is_string(value):
                warn(f"{field} value must be a string, got {type(value)}")
                report_error("action", f"{field} value must be a string, got {type(value)}")
                trace_out()
                return False
        
        if is_error():
            trace_out()
            return False
        
        metadata = self._get_metadata_dict()
        
        if field == "meta":
            current_field = metadata.get('meta', {})
            if isinstance(current_field, str):
                try:
                    current_field = json.loads(current_field)
                except (ValueError, TypeError):
                    current_field = {}
            if not isinstance(current_field, dict):
                current_field = {}
        else:
            current_field = metadata.get(field, {})
            if not isinstance(current_field, dict):
                current_field = {}
        
        current_field.update(data)
        
        if field == "meta":
            sorted_field = self._sort_meta_dict(current_field)
            metadata['meta'] = sorted_field
            if self._write_metadata_dict(metadata):
                self.meta_dict = sorted_field
                self.meta = json.dumps(sorted_field, ensure_ascii=False) if sorted_field else '{}'
                log(f"Successfully set {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        else:
            metadata[field] = current_field
            if self._write_metadata_dict(metadata):
                log(f"Successfully set {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        
        trace_out()
        return not is_error()
    
    def work_set_all(self, data: Dict[str, str], field: str = "meta") -> bool:
        """Replace entire specified field dictionary with new dictionary."""
        trace_in()
        # Normalize field name (e.g., 'files' -> 'files_touched')
        field = self._normalize_field_name(field)
        log(f"Setting all {field} for page {self.id}")
        
        if field not in ("files_touched", "deviations", "meta"):
            warn(f"Invalid field: {field}. Must be 'files_touched', 'deviations', or 'meta'")
            report_error("action", f"Invalid field: {field}")
            trace_out()
            return False
        
        if not isinstance(data, dict):
            warn(f"Data must be a dictionary, got {type(data)}")
            report_error("action", "Data must be a dictionary")
            trace_out()
            return False
        
        for key, value in data.items():
            if not self._validate_is_string(key):
                warn(f"{field} key must be a string, got {type(key)}")
                report_error("action", f"{field} key must be a string, got {type(key)}")
                trace_out()
                return False
            if not self._validate_is_string(value):
                warn(f"{field} value must be a string, got {type(value)}")
                report_error("action", f"{field} value must be a string, got {type(value)}")
                trace_out()
                return False
        
        if is_error():
            trace_out()
            return False
        
        metadata = self._get_metadata_dict()
        
        if field == "meta":
            sorted_field = self._sort_meta_dict(data)
            metadata['meta'] = sorted_field
            if self._write_metadata_dict(metadata):
                self.meta_dict = sorted_field
                self.meta = json.dumps(sorted_field, ensure_ascii=False) if sorted_field else '{}'
                log(f"Successfully set all {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        else:
            metadata[field] = data
            if self._write_metadata_dict(metadata):
                log(f"Successfully set all {field} for page {self.id}")
                self.flag_page_modification("meta updated")
            else:
                warn(f"Failed to write {field} for page {self.id}")
                report_error("action", f"Failed to write {field}")
        
        trace_out()
        return not is_error()
    
    def modify_work_status(self, status: str) -> bool:
        """Modify the status of this work entity."""
        trace_in()
        log(f"Starting status modification for page {self.id}: '{self.status}' -> '{status}'")
        if status == self.status:
            log("Status unchanged, no update needed")
            trace_out()
            return True
        metadata = self._get_metadata_dict()
        metadata['status'] = status
        if self._write_metadata_dict(metadata):
            self.status = status
            log(f"Successfully updated page {self.id} status to '{status}'")
            self.flag_page_modification("status changed")
        trace_out()
        return not is_error()
