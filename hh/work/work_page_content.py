from __future__ import annotations
import json
import datetime as dt
from typing import Dict, Any
from hh.gateway.connection.connection import r_query, u_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.work.work_page_method_registry import register_work_page_mixin_methods
from hh.page.page_registry import get_page_conn

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_work_page_content_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_work_page_mixin_methods
def _register_work_page_content_methods():
    return {
        'modify_work_status': {'mixin_method': '_modify_status', 'decorator': 'write'},
        'modify_work_meta_set_pair': {'mixin_method': '_modify_meta_set_pair', 'decorator': 'write'},
        'modify_work_meta_remove_pair': {'mixin_method': '_modify_meta_remove_pair', 'decorator': 'write'},
        'modify_work_meta_set_all': {'mixin_method': '_modify_meta_set_all', 'decorator': 'write'},
        'modify_work_sort_order': {'mixin_method': '_modify_sort_order', 'decorator': 'write'},
    }


def _parse_metadata(metadata: Any) -> Dict[str, Any]:
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


class WorkPageContentMixin:
    WORK_NAMESPACE = 'work'
    CUSTOM_META_NAMESPACE = 'meta'
    
    def do_init(self, conn: DatabaseConnection, page_id: int):
        # Call parent's do_init first to load base page data
        super().do_init(conn, page_id)
        
        # Only proceed if parent initialization succeeded and we have a connection
        if is_error() or not conn:
            return
        
        trace_in()
        work_defaults = {
            'status': 'todo',
            'sort_order': 0,
            'started_ts': dt.datetime.now().isoformat(),
            'ended_ts': None,
        }
        work_data = self.get_metadata_namespace(
            self.WORK_NAMESPACE,
            default=work_defaults,
            persist_if_missing=True,
        )
        self.status = work_data.get('status', 'todo')
        self.sort_order = work_data.get('sort_order', 0)
        self.started_ts = work_data.get('started_ts')
        self.ended_ts = work_data.get('ended_ts')

        meta_bucket = self.get_metadata_namespace(
            self.CUSTOM_META_NAMESPACE,
            default={},
            persist_if_missing=True,
        )
        if not isinstance(meta_bucket, dict):
            meta_bucket = {}
            self.set_metadata_namespace(self.CUSTOM_META_NAMESPACE, meta_bucket)
        self.meta_dict = meta_bucket
        self.meta = json.dumps(meta_bucket, ensure_ascii=False)
        log(
            f"{self.__class__.__name__} {page_id} loaded from metadata: "
            f"status='{self.status}', sort_order={self.sort_order}"
        )
        trace_out()
    
    def _get_page_data(self) -> Dict[str, Any]:
        """Override to add work entity specific fields to full page data."""
        trace_in()
        # Get full page data from parent
        data = super()._get_page_data()
        # Add work entity specific fields
        data['status'] = self.status if hasattr(self, 'status') else 'todo'
        data['meta'] = self.meta if hasattr(self, 'meta') else ''
        data['sort_order'] = self.sort_order if hasattr(self, 'sort_order') else 0
        data['started_ts'] = str(self.started_ts) if hasattr(self, 'started_ts') and self.started_ts else None
        data['ended_ts'] = str(self.ended_ts) if hasattr(self, 'ended_ts') and self.ended_ts else None
        trace_out()
        return data
    
    def get_child_page_data(self) -> Dict[str, Any]:
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
    
    @classmethod
    def add_page_class_information(cls, new_page_id: int, conn: DatabaseConnection):
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

        parent_id = None
        class_name = None
        try:
            parent_results = r_query(conn, "SELECT parent, class FROM pages WHERE id = %s", [new_page_id])
            if parent_results:
                parent_id = parent_results[0].get('parent')
                class_name = parent_results[0].get('class')
        except Exception as exc:
            debug(f"Failed to get parent/class for page {new_page_id}: {exc}")

        max_order = 0
        if parent_id is not None and class_name:
            sibling_rows = r_query(
                conn,
                "SELECT metadata FROM pages WHERE parent = %s AND class = %s",
                [parent_id, class_name],
            )
            for row in sibling_rows:
                metadata = _parse_metadata(row.get('metadata'))
                work_block = metadata.get(cls.WORK_NAMESPACE)
                if isinstance(work_block, dict):
                    try:
                        current = int(work_block.get('sort_order') or 0)
                        if current > max_order:
                            max_order = current
                    except (TypeError, ValueError):
                        continue

        new_sort_order = max_order + 1
        work_namespace = {
            'status': status,
            'sort_order': new_sort_order,
            'started_ts': dt.datetime.now().isoformat(),
            'ended_ts': None,
        }

        new_page = get_page_conn(conn, new_page_id)
        if not new_page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return

        new_page.set_metadata_namespace(cls.WORK_NAMESPACE, work_namespace)
        new_page.set_metadata_namespace(cls.CUSTOM_META_NAMESPACE, user_meta or {})
        new_page.status = status
        new_page.sort_order = new_sort_order
        new_page.started_ts = work_namespace['started_ts']
        new_page.ended_ts = None
        new_page.meta = json.dumps(user_meta or {}, ensure_ascii=False)
        new_page.reset_connection()
        trace_out()
    
    def delete_page_class_information(self):
        """
        Hook called before page deletion to remove work-specific metadata if desired.
        """
        trace_in()
        # No additional cleanup required now that metadata lives on the page row.
        trace_out()
    
    def _modify_status(self, status: str) -> bool:
        """Modify the status of this work entity."""
        trace_in()
        log(f"Starting status modification for page {self.id}: '{self.status}' -> '{status}'")
        if status == self.status:
            log("Status unchanged, no update needed")
            trace_out()
            return True
        work_data = self.get_metadata_namespace(self.WORK_NAMESPACE, default={}, persist_if_missing=True)
        updated = dict(work_data)
        updated['status'] = status
        if self.set_metadata_namespace(self.WORK_NAMESPACE, updated):
            self.status = status
            log(f"Successfully updated page {self.id} status to '{status}'")
        trace_out()
        return not is_error()
    
    def _modify_meta_set_pair(self, key: str, value: str) -> bool:
        """Set/add/update a single key-value pair in the meta JSON field."""
        trace_in()
        log(f"Setting meta key '{key}' for page {self.id}")
        current_meta = self.get_metadata_namespace(
            self.CUSTOM_META_NAMESPACE,
            default={},
            persist_if_missing=True,
        )
        meta_copy = dict(current_meta)
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            parsed_value = value
        meta_copy[key] = parsed_value
        if self.set_metadata_namespace(self.CUSTOM_META_NAMESPACE, meta_copy):
            self.meta = json.dumps(meta_copy, ensure_ascii=False)
            log(f"Successfully updated page {self.id} meta key '{key}'")
        trace_out()
        return not is_error()
    
    def _modify_meta_remove_pair(self, key: str) -> bool:
        """Remove a single key from the meta JSON field."""
        trace_in()
        log(f"Removing meta key '{key}' for page {self.id}")
        current_meta = self.get_metadata_namespace(
            self.CUSTOM_META_NAMESPACE,
            default={},
            persist_if_missing=True,
        )
        if key in current_meta:
            meta_copy = dict(current_meta)
            meta_copy.pop(key, None)
            if self.set_metadata_namespace(self.CUSTOM_META_NAMESPACE, meta_copy):
                self.meta = json.dumps(meta_copy, ensure_ascii=False)
                log(f"Successfully removed key '{key}' from page {self.id} meta")
        else:
            log(f"Key '{key}' not found in meta, nothing to remove")
        trace_out()
        return not is_error()
    
    def _modify_meta_set_all(self, meta_json: str) -> bool:
        """Replace the entire meta JSON field with a new JSON object."""
        trace_in()
        log(f"Setting entire meta for page {self.id}")
        
        if meta_json and isinstance(meta_json, str) and meta_json.strip():
            try:
                meta_dict = json.loads(meta_json)
                if not isinstance(meta_dict, dict):
                    warn("Provided meta JSON must describe an object")
                    report_error("action", "Meta JSON must be an object")
                    trace_out()
                    return False
            except json.JSONDecodeError as exc:
                warn(f"Invalid JSON provided for meta: {exc}")
                report_error("action", f"Invalid JSON for meta: {exc}")
                trace_out()
                return False
        else:
            meta_dict = {}
        
        if self.set_metadata_namespace(self.CUSTOM_META_NAMESPACE, meta_dict):
            self.meta = json.dumps(meta_dict, ensure_ascii=False)
            log(f"Successfully updated page {self.id} meta")
        trace_out()
        return not is_error()
    
    def _modify_sort_order(self, sort_order: int) -> bool:
        """Modify the sort_order of this work entity, reflowing all siblings within the same parent."""
        trace_in()
        log(f"Starting sort_order modification for page {self.id}: {self.sort_order} -> {sort_order}")
        
        # Get parent page ID
        parent_id = None
        if not is_error():
            parent_results = r_query(self.conn, "SELECT parent FROM pages WHERE id = %s", [self.id])
            if parent_results and parent_results[0].get('parent') is not None:
                parent_id = int(parent_results[0]['parent'])
            else:
                warn(f"Could not determine parent for page {self.id}")
                report_error("action", f"Could not determine parent for page {self.id}")
        
        if not is_error() and parent_id:
            class_name = self.class_name
            siblings = r_query(
                self.conn,
                "SELECT id, metadata FROM pages WHERE parent = %s AND class = %s ORDER BY id",
                [parent_id, class_name],
            )
            if not siblings:
                warn(f"No siblings found for page {self.id} under parent {parent_id}")
                report_error("action", f"No siblings found for page {self.id}")
            else:
                siblings_with_meta = []
                for row in siblings:
                    metadata = _parse_metadata(row.get('metadata'))
                    work_block = metadata.get(self.WORK_NAMESPACE, {})
                    current_order = work_block.get('sort_order') or 0
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
                
                if sort_order <= 0:
                    new_pos = 0
                    log(f"Position {sort_order} clamped to beginning (0)")
                elif sort_order > len(siblings_without_target):
                    new_pos = len(siblings_without_target)
                    log(f"Position {sort_order} clamped to end ({new_pos})")
                else:
                    new_pos = sort_order - 1
                    log(f"Position {sort_order} -> index {new_pos}")
                
                siblings_without_target.insert(new_pos, target_entry)
                new_order = siblings_without_target
                
                order_changed = any(
                    original['page_id'] != updated['page_id']
                    for original, updated in zip(siblings_with_meta, new_order)
                ) or (len(siblings_with_meta) != len(new_order))
                
                if not order_changed:
                    log("Sort order unchanged after reflow, no update needed")
                    trace_out()
                    return True
                
                log(f"Reflowing {len(new_order)} siblings under parent {parent_id}")
                for index, sibling in enumerate(new_order):
                    new_sort = index + 1
                    metadata = sibling['metadata']
                    work_block = metadata.get(self.WORK_NAMESPACE)
                    if not isinstance(work_block, dict):
                        work_block = {}
                    work_block['sort_order'] = new_sort
                    metadata[self.WORK_NAMESPACE] = work_block
                    metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
                    affected = u_query(
                        self.conn,
                        "UPDATE pages SET metadata = %s WHERE id = %s",
                        (metadata_json, sibling['page_id']),
                    )
                    if affected == 0:
                        warn(f"Failed to update sort_order for page {sibling['page_id']}")
                        report_error("action", f"Failed to update sort_order for page {sibling['page_id']}")
                        break
                    if sibling['page_id'] == self.id:
                        self.sort_order = new_sort
                if not is_error():
                    log(f"Successfully updated ordering for {len(new_order)} siblings")
        
        trace_out()
        return not is_error()

