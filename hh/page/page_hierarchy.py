from typing import Dict, Any, List, Optional
import datetime as dt
from hh.gateway.connection.connection import r_query, u_query, c_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, get_page_conn
from hh.page.page_method_registry import register_page_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_page_hierarchy_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_mixin_methods
def _register_hierarchy_methods():
    return {
        'get_path': {'mixin_method': '_get_path', 'decorator': 'read'},
        'get_children_data': {'mixin_method': '_get_children_data', 'decorator': 'read'},
        'get_child_page_ids': {'mixin_method': '_get_child_page_ids', 'decorator': 'read'},
        'get_child_count': {'mixin_method': '_get_child_count', 'decorator': 'read'},
        'move_page': {'mixin_method': '_move_page', 'decorator': 'write'},
        'copy_page': {'mixin_method': '_copy_page', 'decorator': 'write'},
    }


class PageHierarchyMixin:

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        # Default: only return children of class 'page', sorted by name
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'page' ORDER BY name",
            [parent_id]
        )


    def _copy_page_class_information(self, new_page_id: int):
        pass
    
    def _get_display_name(self) -> str:
        """
        Get the display name for this page, with fallback logic.
        Override this method in subclasses to provide custom display names.
        Checks cached display_name first, then computes if needed.
        """
        # Check if field is already populated
        if hasattr(self, 'display_name') and self.display_name:
            return self.display_name
        # Field is empty, compute it
        display_name = self.name or f"Page {self.id}"
        self.display_name = display_name
        # Flag that cache needs refresh since we just computed
        self._flag_cache_refresh()
        return display_name

    def _get_path(self) -> List[Dict[str, Any]]:
        trace_in()
        path = []
        current_page = self
        level = 0
        while current_page and current_page.parent != 0:
            level += 1
            path.append({
                "id": current_page.id,
                "name": current_page._get_display_name(),
                "class": current_page.class_name
            })
            # Get parent page
            parent_page = get_page(page_id=current_page.parent)
            if not parent_page:
                warn(f"Parent page {current_page.parent} not found for page {current_page.id}")
                break
            current_page = parent_page
        # Add root page (parent = 0)
        if current_page:
            level += 1
            path.append({
                "id": current_page.id,
                "name": current_page._get_display_name(),
                "class": current_page.class_name
            })
        # Reverse to get root -> current order
        path.reverse()
        log(f"Built path for page {self.id}: {len(path)} levels -> {[p['name'] for p in path]}")
        trace_out()
        return path


    def _get_children_data(self) -> List[Dict[str, Any]]:
        trace_in()
        children_data = []
        if not is_error():
            child_ids = self._get_child_page_ids()
        if not is_error():
            for i, child_id in enumerate(child_ids):
                if not is_error():
                    child_page = get_page_conn(self.conn, page_id=child_id)
                    if child_page:
                        child_data = child_page.get_page_data()
                        # Add child count for this child page
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        children_data.append(child_data)
                    else:
                        warn(f"Failed to load child page {child_id}")
                        report_error("action", f"Failed to load child page {child_id}")
        log(f"Loaded {len(children_data)}/{len(child_ids)} child pages for page {self.id}: {[c['name'] for c in children_data]}")
        trace_out()
        return children_data


    def _get_child_page_ids(self) -> List[int]:
        trace_in()
        child_ids = []
        if not is_error():
            query, params = self._get_children_query(self.id)
            results = r_query(self.conn, query, params)
            if results:
                child_ids = [row['id'] for row in results]
        log(f"Child page IDs for page {self.id}: {len(child_ids)} found -> {child_ids}")
        trace_out()
        return child_ids


    def _get_child_count(self) -> int:
        trace_in()
        count = 0
        if not is_error():
            results = r_query(self.conn, "SELECT COUNT(*) as count FROM pages WHERE parent = %s", [self.id])
            if results:
                count = results[0]['count']
            else:
                warn(f"Failed to get child count for page {self.id}")
        log(f"Page {self.id} has {count} children")
        trace_out()
        return count


    def _move_page(self, target_page_id: int) -> bool:
        trace_in()
        # Validate the move is allowed
        if not self.can_move_to_page(target_page_id):
            warn("Move validation failed")
            report_error("action", "Move validation failed")
            trace_out()
            return False
        original_parent = self.parent
        if not is_error():
            # Perform the actual move
            affected = u_query(self.conn, "UPDATE pages SET parent = %s WHERE id = %s", (target_page_id, self.id))
            if affected == 0:
                warn(f"Failed to move page {self.id} - no rows affected")
                report_error("action", f"Failed to move page {self.id}")
        if not is_error():
            # Update object property and audit trail
            self.parent = target_page_id
            self._flag_page_modification("page moved")
            # Flag old parent so cache sees removals
            if original_parent and original_parent != 0 and original_parent != target_page_id:
                old_parent = get_page_conn(self.conn, page_id=original_parent)
                if old_parent:
                    old_parent.flag_page_modification("child moved out")
            # Flag new parent for additions
            if target_page_id and target_page_id != 0:
                new_parent = get_page_conn(self.conn, page_id=target_page_id)
                if new_parent:
                    new_parent.flag_page_modification("child moved in")
            log(f"Successfully moved page {self.id} to parent {target_page_id}")
        trace_out()
        return not is_error()


    def _copy_page(self, target_page_id: int, recursive: bool = False, max_depth: Optional[int] = None) -> int:
        trace_in()
        # Validate the copy is allowed (same as move validation)
        if not self.can_move_to_page(target_page_id):
            warn("Copy validation failed")
            report_error("action", "Copy validation failed")
            trace_out()
            return 0
        new_page_id = 0
        if not is_error():
            # Determine name for copy
            name = self.name if self.name else ''
            if not self.name:  # this page has no name
                if not self.allow_null_names():
                    warn("Cannot copy page with null name")
                    report_error("action", "Cannot copy page with null name")
            else:  # this page has a name - figure out a good name for the copy
                name_ctr = 1
                loop_failsafe = 100
                good_name = False
                while not good_name and (name_ctr < loop_failsafe):
                    log(f"Trying name '{name}' (attempt {name_ctr})")
                    # Use validate_name on the target parent page (use self's class since that's what the copied page will be)
                    target_page = get_page(page_id=target_page_id)
                    if target_page:
                        if target_page.validate_name(name, self.class_name, error_on_invalid=False):
                            good_name = True
                            log(f"Name '{name}' is valid")
                        else:
                            log(f"Name '{name}' failed validation, generating new name")
                            name = f"copy{' ' + str(name_ctr) if name_ctr > 1 else ''} of {self.name}"
                            name_ctr += 1
                    else:
                        warn(f"Target page {target_page_id} not found during name validation")
                        break
                if name_ctr == loop_failsafe:
                    warn("Copy name generation loop failsafe hit")
                    report_error("action", "Copy name generation failed")
        if not is_error():
            # Create the new page using add_page
            target_page = get_page(page_id=target_page_id)
            if target_page:
                new_page_id = target_page.add_page(self.class_name, name)
            else:
                warn(f"Target page {target_page_id} not found")
                report_error("action", f"Target page {target_page_id} not found")
        if not is_error() and new_page_id > 0:
            # Copy text content
            if self.text:
                new_page = get_page(page_id=new_page_id)
                if new_page:
                    new_page.modify_text(self.text)
            # Call class-specific copy logic hook
            self._copy_page_class_information(new_page_id)
            # Recursively copy children if requested
            if recursive:
                self._copy_children_recursive(new_page_id, max_depth)
            log(f"Successfully copied page {self.id} to page {new_page_id}")
        trace_out()
        return new_page_id


    def _copy_children_recursive(self, parent_id: int, max_depth: Optional[int] = None, current_depth: int = 0) -> None:
        trace_in()
        if max_depth is not None and current_depth >= max_depth:
            log(f"Reached max depth {max_depth}, stopping recursion")
            trace_out()
            return
        if not is_error():
            child_ids = self._get_child_page_ids()
            for child_id in child_ids:
                if not is_error():
                    child_page = get_page(page_id=child_id)
                    if child_page:
                        # Copy child to new parent
                        copied_child_id = child_page.copy_page(parent_id, recursive=True, max_depth=max_depth)
                        if copied_child_id > 0:
                            log(f"Copied child page {child_id} to {copied_child_id}")
        trace_out()
