from __future__ import annotations
import re
import json
from typing import Dict, Any
from hh.gateway.connection.connection import r_query, c_query, d_query, u_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.work.work_page_method_registry import register_work_page_mixin_methods

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


def _camel_to_snake_plural(class_name: str) -> str:
    """
    Convert CamelCase class name to snake_case plural table name.
    Examples:
        WorkDocket -> work_dockets
        Ask -> asks
        Task -> tasks
        Step -> steps
    """
    # Insert underscore before uppercase letters (except the first one)
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
    # Pluralize: simple rule - add 's' or 'es' based on ending
    if snake.endswith('y'):
        # e.g., category -> categories
        snake = snake[:-1] + 'ies'
    elif snake.endswith(('s', 'sh', 'ch', 'x', 'z')):
        # e.g., class -> classes
        snake = snake + 'es'
    else:
        # Default: add 's'
        snake = snake + 's'
    return snake


@register_work_page_mixin_methods
def _register_work_page_content_methods():
    return {
        'modify_work_status': {'mixin_method': '_modify_status', 'decorator': 'write'},
        'modify_work_meta_set_pair': {'mixin_method': '_modify_meta_set_pair', 'decorator': 'write'},
        'modify_work_meta_remove_pair': {'mixin_method': '_modify_meta_remove_pair', 'decorator': 'write'},
        'modify_work_meta_set_all': {'mixin_method': '_modify_meta_set_all', 'decorator': 'write'},
        'modify_work_sort_order': {'mixin_method': '_modify_sort_order', 'decorator': 'write'},
    }


class WorkPageContentMixin:
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the database table name for this work entity class."""
        # Import here to avoid circular import
        from hh.work.work_page import WorkPage
        
        # Walk up the MRO to find the actual work entity class (not the mixin or abstract base)
        for base in cls.__mro__:
            # Skip mixins (classes ending with Mixin), WorkPage (abstract base), object, and base classes
            if (base not in (cls, WorkPageContentMixin, WorkPage, object) and 
                hasattr(base, '__module__') and 
                base.__module__ and
                not base.__name__.endswith('Mixin') and  # Skip all mixin classes
                base.__name__ != 'WorkPage' and  # Skip abstract WorkPage base class
                ('work' in base.__module__ or 'work_docket' in base.__module__ or 'work_page' in base.__module__)):
                class_name = base.__name__
                return _camel_to_snake_plural(class_name)
        # Fallback: use the class name directly
        class_name = cls.__name__
        return _camel_to_snake_plural(class_name)
    
    def do_init(self, conn: DatabaseConnection, page_id: int):
        # Call parent's do_init first to load base page data
        super().do_init(conn, page_id)
        
        # Only proceed if parent initialization succeeded and we have a connection
        if is_error() or not conn:
            return
        
        # Load work entity data using dynamically determined table name
        trace_in()
        table_name = self.__class__.get_table_name()
        query = f"SELECT status, meta, sort_order, started_ts, ended_ts FROM {table_name} WHERE page_id = %s"
        results = r_query(conn, query, [page_id])
        if results:
            entity_data = results[0]
            self.status = entity_data.get('status') or 'todo'
            self.meta = entity_data.get('meta') or ''
            self.sort_order = entity_data.get('sort_order') or 0
            self.started_ts = entity_data.get('started_ts')
            self.ended_ts = entity_data.get('ended_ts')
            log(f"{self.__class__.__name__} {page_id} loaded: status='{self.status}', sort_order={self.sort_order}")
        else:
            debug(f"{self.__class__.__name__} {page_id} has no {table_name} entry")
            self.status = 'todo'
            self.meta = ''
            self.sort_order = 0
            self.started_ts = None
            self.ended_ts = None
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
        Hook called after page creation to add work entity table entry.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return
        
        # Get status and meta from gateway arguments (both optional)
        status = gateway.get_arg('status') or 'todo'
        meta = gateway.get_arg('meta') or None
        
        # Get parent page ID for the new page
        parent_id = None
        try:
            parent_results = r_query(conn, "SELECT parent FROM pages WHERE id = %s", [new_page_id])
            if parent_results and parent_results[0].get('parent') is not None:
                parent_id = int(parent_results[0]['parent'])
        except Exception as e:
            debug(f"Failed to get parent for page {new_page_id}: {str(e)}")
        
        # Get max sort_order for entities of this type under the same parent
        table_name = cls.get_table_name()
        max_order = 0
        if parent_id:
            try:
                # Join work entity table with pages table to filter by parent
                query = f"""
                    SELECT MAX({table_name}.sort_order) as max_order 
                    FROM {table_name} 
                    INNER JOIN pages ON {table_name}.page_id = pages.id 
                    WHERE pages.parent = %s
                """
                results = r_query(conn, query, [parent_id])
                if results and results[0].get('max_order') is not None:
                    max_order = int(results[0]['max_order'])
            except Exception as e:
                debug(f"Failed to get max sort_order for parent {parent_id}: {str(e)}")
        
        new_sort_order = max_order + 1
        
        # Insert into work entity table
        if conn:
            try:
                c_query(conn, f"""
                    INSERT INTO {table_name} (page_id, status, meta, sort_order)
                    VALUES (%s, %s, %s, %s)
                """, (new_page_id, status, meta, new_sort_order))
                log(f"Created {table_name} entry for page {new_page_id}: status='{status}', sort_order={new_sort_order}")
            except Exception as e:
                warn(f"Failed to create {table_name} entry: {str(e)}")
                report_error("backend", f"Failed to create {table_name} entry: {str(e)}")
        
        trace_out()
    
    def delete_page_class_information(self):
        """
        Hook called before page deletion to remove work entity table entry.
        """
        trace_in()
        if self.conn and self.id:
            table_name = self.__class__.get_table_name()
            try:
                d_query(self.conn, f"DELETE FROM {table_name} WHERE page_id = %s", [self.id])
                log(f"Deleted {table_name} entry for page {self.id}")
            except Exception as e:
                warn(f"Failed to delete {table_name} entry: {str(e)}")
                report_error("backend", f"Failed to delete {table_name} entry: {str(e)}")
        trace_out()
    
    def _modify_status(self, status: str) -> bool:
        """Modify the status of this work entity."""
        trace_in()
        log(f"Starting status modification for page {self.id}: '{self.status}' -> '{status}'")
        if status == self.status:
            log("Status unchanged, no update needed")
            trace_out()
            return True
        old_status = self.status
        log(f"Old status: '{old_status}', new status: '{status}'")
        table_name = self.__class__.get_table_name()
        if not is_error():
            log(f"Updating page {self.id} status in database: '{old_status}' -> '{status}'")
            affected = u_query(self.conn, f"UPDATE {table_name} SET status = %s WHERE page_id = %s", (status, self.id))
            if affected == 0:
                # Entry should already exist - if UPDATE affects 0 rows, that's an error
                warn(f"No {table_name} entry found for page {self.id} - entry should exist before modification")
                report_error("action", f"No {table_name} entry found for page {self.id}")
            else:
                log(f"Successfully updated page {self.id} status in database")
        if not is_error():
            self.status = status
            log(f"Successfully updated page {self.id} status to '{status}'")
        trace_out()
        return not is_error()
    
    def _modify_meta_set_pair(self, key: str, value: str) -> bool:
        """Set/add/update a single key-value pair in the meta JSON field."""
        trace_in()
        log(f"Setting meta key '{key}' for page {self.id}")
        table_name = self.__class__.get_table_name()
        
        # Get current meta
        current_meta_str = self.meta if hasattr(self, 'meta') and self.meta else '{}'
        try:
            current_meta = json.loads(current_meta_str) if current_meta_str else {}
        except json.JSONDecodeError:
            # If current meta is not valid JSON, start with empty dict
            warn(f"Current meta for page {self.id} is not valid JSON, starting fresh")
            current_meta = {}
        
        # Try to parse value as JSON, fall back to string
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            parsed_value = value
        
        # Update the key
        current_meta[key] = parsed_value
        new_meta_str = json.dumps(current_meta)
        
        if not is_error():
            log(f"Updating page {self.id} meta in database")
            affected = u_query(self.conn, f"UPDATE {table_name} SET meta = %s WHERE page_id = %s", (new_meta_str, self.id))
            if affected == 0:
                # Entry should already exist - if UPDATE affects 0 rows, that's an error
                warn(f"No {table_name} entry found for page {self.id} - entry should exist before modification")
                report_error("action", f"No {table_name} entry found for page {self.id}")
            else:
                log(f"Successfully updated page {self.id} meta in database")
        if not is_error():
            self.meta = new_meta_str
            log(f"Successfully updated page {self.id} meta key '{key}'")
        trace_out()
        return not is_error()
    
    def _modify_meta_remove_pair(self, key: str) -> bool:
        """Remove a single key from the meta JSON field."""
        trace_in()
        log(f"Removing meta key '{key}' for page {self.id}")
        table_name = self.__class__.get_table_name()
        
        # Get current meta
        current_meta_str = self.meta if hasattr(self, 'meta') and self.meta else '{}'
        try:
            current_meta = json.loads(current_meta_str) if current_meta_str else {}
        except json.JSONDecodeError:
            # If current meta is not valid JSON, nothing to remove
            warn(f"Current meta for page {self.id} is not valid JSON, nothing to remove")
            log("No valid meta to remove key from")
            trace_out()
            return True
        
        # Remove the key if it exists
        if key in current_meta:
            del current_meta[key]
            new_meta_str = json.dumps(current_meta)
            
            if not is_error():
                log(f"Updating page {self.id} meta in database")
                affected = u_query(self.conn, f"UPDATE {table_name} SET meta = %s WHERE page_id = %s", (new_meta_str, self.id))
                if affected == 0:
                    # Entry should already exist - if UPDATE affects 0 rows, that's an error
                    warn(f"No {table_name} entry found for page {self.id} - entry should exist before modification")
                    report_error("action", f"No {table_name} entry found for page {self.id}")
                else:
                    log(f"Successfully updated page {self.id} meta in database")
            if not is_error():
                self.meta = new_meta_str
                log(f"Successfully removed key '{key}' from page {self.id} meta")
        else:
            log(f"Key '{key}' not found in meta, nothing to remove")
        
        trace_out()
        return not is_error()
    
    def _modify_meta_set_all(self, meta_json: str) -> bool:
        """Replace the entire meta JSON field with a new JSON object."""
        trace_in()
        log(f"Setting entire meta for page {self.id}")
        table_name = self.__class__.get_table_name()
        
        # Validate JSON
        if meta_json and meta_json.strip():
            try:
                # Parse to validate JSON, then stringify to ensure consistent format
                parsed = json.loads(meta_json)
                new_meta_str = json.dumps(parsed)
            except json.JSONDecodeError as e:
                warn(f"Invalid JSON provided for meta: {str(e)}")
                report_error("action", f"Invalid JSON for meta: {str(e)}")
                trace_out()
                return False
        else:
            # Empty string means clear all meta
            new_meta_str = '{}'
        
        if not is_error():
            log(f"Updating page {self.id} meta in database")
            affected = u_query(self.conn, f"UPDATE {table_name} SET meta = %s WHERE page_id = %s", (new_meta_str, self.id))
            if affected == 0:
                # Entry should already exist - if UPDATE affects 0 rows, that's an error
                warn(f"No {table_name} entry found for page {self.id} - entry should exist before modification")
                report_error("action", f"No {table_name} entry found for page {self.id}")
            else:
                log(f"Successfully updated page {self.id} meta in database")
        if not is_error():
            self.meta = new_meta_str
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
            table_name = self.__class__.get_table_name()
            class_name = self.class_name
            
            # Get current ordering of all siblings (same parent, same class)
            if not is_error():
                query = f"""
                    SELECT {table_name}.page_id, {table_name}.sort_order 
                    FROM {table_name} 
                    INNER JOIN pages ON {table_name}.page_id = pages.id 
                    WHERE pages.parent = %s AND pages.class = %s 
                    ORDER BY {table_name}.sort_order
                """
                siblings = r_query(self.conn, query, [parent_id, class_name])
                
                if not siblings:
                    warn(f"No siblings found for page {self.id} under parent {parent_id}")
                    report_error("action", f"No siblings found for page {self.id}")
            
            if not is_error():
                # Find the target entity in the list
                target_found = None
                target_index = None
                for i, sibling in enumerate(siblings):
                    if sibling['page_id'] == self.id:
                        target_found = sibling
                        target_index = i
                        break
                
                if target_found is None:
                    # Target not in siblings list - might not have a work entity entry yet
                    # Create a minimal entry for it
                    target_found = {'page_id': self.id, 'sort_order': 0}
                    siblings.append(target_found)
                    target_index = len(siblings) - 1
                    log(f"Page {self.id} not found in siblings, adding to end")
                
                # Remove target from list
                siblings_without_target = [s for s in siblings if s['page_id'] != self.id]
                
                # Clamp position: <= 0 or negative = beginning, too high = end
                if sort_order <= 0:
                    new_pos = 0
                    log(f"Position {sort_order} clamped to beginning (0)")
                elif sort_order > len(siblings_without_target):
                    new_pos = len(siblings_without_target)
                    log(f"Position {sort_order} clamped to end ({new_pos})")
                else:
                    new_pos = sort_order - 1  # Convert to 0-based
                    log(f"Position {sort_order} -> index {new_pos}")
                
                # Insert target at new position
                siblings_without_target.insert(new_pos, target_found)
                new_order = siblings_without_target
                
                # Check if order actually changed
                order_changed = False
                if len(new_order) != len(siblings):
                    order_changed = True
                else:
                    for i, sibling in enumerate(new_order):
                        if sibling['page_id'] != siblings[i]['page_id']:
                            order_changed = True
                            break
                
                if not order_changed:
                    log("Sort order unchanged after reflow, no update needed")
                    trace_out()
                    return True
                
                # Reflow all siblings to sequential order (1, 2, 3, 4...)
                if not is_error():
                    log(f"Reflowing {len(new_order)} siblings under parent {parent_id}")
                    try:
                        # Use transaction for atomic updates
                        u_query(self.conn, "START TRANSACTION", [])
                        for i, sibling in enumerate(new_order):
                            new_sort_order = i + 1
                            u_query(self.conn, f"UPDATE {table_name} SET sort_order = %s WHERE page_id = %s", 
                                   (new_sort_order, sibling['page_id']))
                        u_query(self.conn, "COMMIT", [])
                        log(f"Successfully reflowed {len(new_order)} siblings to sequential order")
                    except Exception as e:
                        u_query(self.conn, "ROLLBACK", [])
                        warn(f"Failed to reflow siblings: {str(e)}")
                        report_error("action", f"Failed to reflow siblings: {str(e)}")
                
                if not is_error():
                    # Update instance variable to new sort_order
                    new_sort_order = new_pos + 1
                    self.sort_order = new_sort_order
                    log(f"Successfully updated page {self.id} sort_order to {new_sort_order} (position {sort_order})")
        
        trace_out()
        return not is_error()

