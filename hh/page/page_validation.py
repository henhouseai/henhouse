from typing import Optional, List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page # Needed for can_move_to_page

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_page_validation_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)




class PageValidationMixin:
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Static method: checks if this page class allows null names"""
        return False


    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Static method: checks if this page class allows duplicate names"""
        return True


    @classmethod
    def auto_link_name(cls) -> bool:
        """Static method: checks if this page class auto-generates links from names"""
        return True
    

    def allow_class_inside(self, target_class: str) -> bool:
        """Instance method: checks if this page instance can contain pages of target_class"""
        return True


    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Static method: checks if this page class can be inside pages of parent_class"""
        return True
    

    def validate_name(
        self,
        name: str,
        page_class: str,
        exclude_id: Optional[int] = None,
        error_on_invalid: bool = True,
    ) -> bool:
        """Validate a page name. Uses parent's connection and parent_id, but checks new page's class settings."""
        trace_in()
        from hh.page.page_class_registry import get_page_class
        NewPageClass = get_page_class(page_class)
        if not NewPageClass:
            warn(f"Page class '{page_class}' not found for validation")
            report_error("action", f"Page class '{page_class}' not found")
            trace_out()
            return False

        def fail(warn_msg: str, log_msg: Optional[str] = None) -> bool:
            if error_on_invalid:
                warn(warn_msg)
            else:
                debug(f"[validate_name suppressed] {warn_msg}")
            if log_msg:
                log(log_msg)
            trace_out()
            return False

        log(f"Validating name: '{name}' for parent {self.parent}, page_class: {page_class}, exclude_id: {exclude_id}")
        if not name or len(name) == 0:
            if not NewPageClass.allow_null_names():
                return fail("Page name cannot be empty", "Validation failed: empty name not allowed")
            else:
                log("Validation passed: empty name allowed")
                trace_out()
                return True
        if len(name) > 255:
            return fail(
                f"Page name too long: {len(name)} characters (max 255)",
                f"Validation failed: name too long ({len(name)} chars)",
            )
        if name and name.isdigit():
            return fail("Page name cannot be all digits", "Validation failed: name is all digits")
        if name and any(char in name for char in ['{', '}', '[', ']']):
            return fail(f"Page name contains illegal characters: {name}", "Validation failed: illegal characters")
        if name and not NewPageClass.allow_duplicate_names():
            log(f"Checking for duplicate names under parent {self.parent}")
            if exclude_id:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE parent = %s AND name = %s AND id != %s", 
                              (self.parent, name, exclude_id))
            else:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE parent = %s AND name = %s", 
                              (self.parent, name))
            if results:
                existing_page_id = results[0]['id']
                return fail(
                    f"Page name '{name}' already exists under parent {self.parent} (page ID: {existing_page_id})",
                    f"Validation failed: duplicate name found (existing page {existing_page_id})",
                )
            log("Duplicate name check passed")
        if name and NewPageClass.auto_link_name():
            log(f"Checking for duplicate links (auto_link_name enabled)")
            if exclude_id:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE link = %s AND id != %s", (name, exclude_id))
            else:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE link = %s", (name,))
            if results:
                existing_page_id = results[0]['id']
                return fail(
                    f"Page link '{name}' already exists (page ID: {existing_page_id})",
                    f"Validation failed: duplicate link found (existing page {existing_page_id})",
                )
            log("Duplicate link check passed")
        log(f"Name validation successful for '{name}'")
        trace_out()
        return True


    def can_move_to_page(self, target_page_id: int) -> bool:
        trace_in()
        if target_page_id == self.id:
            warn("Cannot move page into itself")
            report_error("action", "Cannot move page into itself")
            trace_out()
            return False
        if not is_error():
            target_page = get_page(page_id=target_page_id)
            if not target_page:
                warn(f"Target page {target_page_id} does not exist")
                report_error("action", f"Target page {target_page_id} does not exist")
                trace_out()
                return False
        if not is_error():
            # Check if target is a child of this page (would create circular reference)
            child_ids = self._check_children_recursive()
            if target_page_id in child_ids:
                warn(f"Cannot move page into its own child (page {target_page_id})")
                report_error("action", f"Cannot move page into its own child (page {target_page_id})")
                trace_out()
                return False
        if not is_error():
            # Check class compatibility
            if not target_page.allow_class_inside(self.class_name):
                warn(f"Target page {target_page_id} (class={target_page.class_name}) cannot contain pages with class={self.class_name}")
                report_error("action", f"Target page cannot contain pages with class '{self.class_name}'")
                trace_out()
                return False
        if not is_error():
            if not self.__class__.allow_inside_of(target_page.class_name):
                warn(f"Page class '{self.class_name}' cannot be inside page class '{target_page.class_name}'")
                report_error("action", f"Page class '{self.class_name}' cannot be inside page class '{target_page.class_name}'")
                trace_out()
                return False
        log(f"Page {self.id} can be moved to page {target_page_id}")
        trace_out()
        return not is_error()


    def _check_children_recursive(self) -> List[int]:
        trace_in()
        child_array = []
        if not is_error():
            # Start with this page's direct children
            direct_children = self._get_child_page_ids()
            child_array.extend(direct_children)
            # Recursively get children of children
            for child_id in direct_children:
                if not is_error():
                    child_page = get_page(page_id=child_id)
                    if child_page:
                        grand_children = child_page._check_children_recursive()
                        child_array.extend(grand_children)
                    else:
                        warn(f"Failed to load child page {child_id} for recursive check")
                        report_error("action", f"Failed to load child page {child_id}")
        log(f"Found {len(child_array)} total child pages (including nested) for page {self.id}")
        trace_out()
        return child_array
