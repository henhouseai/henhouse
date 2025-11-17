from __future__ import annotations
import re
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
        'modify_work_meta': {'mixin_method': '_modify_meta', 'decorator': 'write'},
        'modify_work_sort_order': {'mixin_method': '_modify_sort_order', 'decorator': 'write'},
    }


class WorkPageContentMixin:
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the database table name for this work entity class."""
        # Walk up the MRO to find the actual work entity class (not the mixin)
        for base in cls.__mro__:
            # Skip mixins, object, and Page base classes
            if (base not in (cls, WorkPageContentMixin, object) and 
                hasattr(base, '__module__') and 
                base.__module__ and
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
        
        # Get max sort_order for all entities of this type
        table_name = cls.get_table_name()
        max_order = 0
        try:
            results = r_query(conn, f"SELECT MAX(sort_order) as max_order FROM {table_name}", [])
            if results and results[0].get('max_order') is not None:
                max_order = int(results[0]['max_order'])
        except Exception as e:
            debug(f"Failed to get max sort_order: {str(e)}")
        
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
                # If no row exists, insert one
                try:
                    c_query(self.conn, f"INSERT INTO {table_name} (page_id, status, meta, sort_order) VALUES (%s, %s, %s, %s)", 
                           (self.id, status, self.meta if hasattr(self, 'meta') else None, self.sort_order if hasattr(self, 'sort_order') else 0))
                    log(f"Created {table_name} entry for page {self.id}")
                except Exception as e:
                    warn(f"Failed to create {table_name} entry: {str(e)}")
                    report_error("action", f"Failed to create {table_name} entry: {str(e)}")
            else:
                log(f"Successfully updated page {self.id} status in database")
        if not is_error():
            self.status = status
            log(f"Successfully updated page {self.id} status to '{status}'")
        trace_out()
        return not is_error()
    
    def _modify_meta(self, meta: str) -> bool:
        """Modify the meta field of this work entity."""
        trace_in()
        log(f"Starting meta modification for page {self.id}")
        table_name = self.__class__.get_table_name()
        if not is_error():
            log(f"Updating page {self.id} meta in database")
            affected = u_query(self.conn, f"UPDATE {table_name} SET meta = %s WHERE page_id = %s", (meta, self.id))
            if affected == 0:
                # If no row exists, insert one
                try:
                    c_query(self.conn, f"INSERT INTO {table_name} (page_id, status, meta, sort_order) VALUES (%s, %s, %s, %s)", 
                           (self.id, self.status if hasattr(self, 'status') else 'todo', meta, self.sort_order if hasattr(self, 'sort_order') else 0))
                    log(f"Created {table_name} entry for page {self.id}")
                except Exception as e:
                    warn(f"Failed to create {table_name} entry: {str(e)}")
                    report_error("action", f"Failed to create {table_name} entry: {str(e)}")
            else:
                log(f"Successfully updated page {self.id} meta in database")
        if not is_error():
            self.meta = meta
            log(f"Successfully updated page {self.id} meta")
        trace_out()
        return not is_error()
    
    def _modify_sort_order(self, sort_order: int) -> bool:
        """Modify the sort_order of this work entity."""
        trace_in()
        log(f"Starting sort_order modification for page {self.id}: {self.sort_order} -> {sort_order}")
        if sort_order == self.sort_order:
            log("Sort order unchanged, no update needed")
            trace_out()
            return True
        old_sort_order = self.sort_order
        log(f"Old sort_order: {old_sort_order}, new sort_order: {sort_order}")
        table_name = self.__class__.get_table_name()
        if not is_error():
            log(f"Updating page {self.id} sort_order in database: {old_sort_order} -> {sort_order}")
            affected = u_query(self.conn, f"UPDATE {table_name} SET sort_order = %s WHERE page_id = %s", (sort_order, self.id))
            if affected == 0:
                # If no row exists, insert one
                try:
                    c_query(self.conn, f"INSERT INTO {table_name} (page_id, status, meta, sort_order) VALUES (%s, %s, %s, %s)", 
                           (self.id, self.status if hasattr(self, 'status') else 'todo', self.meta if hasattr(self, 'meta') else None, sort_order))
                    log(f"Created {table_name} entry for page {self.id}")
                except Exception as e:
                    warn(f"Failed to create {table_name} entry: {str(e)}")
                    report_error("action", f"Failed to create {table_name} entry: {str(e)}")
            else:
                log(f"Successfully updated page {self.id} sort_order in database")
        if not is_error():
            self.sort_order = sort_order
            log(f"Successfully updated page {self.id} sort_order to {sort_order}")
        trace_out()
        return not is_error()

