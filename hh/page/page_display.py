from typing import List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.page.page_method_registry import register_page_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_page_display_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_mixin_methods
def _register_display_methods():
    return {
        'show_page': {'mixin_method': '_show_page', 'decorator': 'read'},
    }


class PageDisplayMixin:
    
    def add_upper_content(self) -> List[str]:
        return []
    

    def add_lower_content(self) -> List[str]:
        return []


    def get_child_row_field_type(self) -> str:
        """Return the field type for this page when displayed as a child row.
        Override in subclasses to customize the label/icon shown in child tables.
        """
        return 'page'


    def add_badge_headers(self) -> Dict[str, Any]:
        badge_headers = {}
        page_data = self.get_page_data()
        # Calculate children count from children_by_class
        children_by_class = self._get_children_by_class()
        children_count = sum(len(group['children']) for group in children_by_class.values())
        # Add page summary as first badge
        badge_headers['page_summary'] = {
            'page_id': page_data.get('id'),
            'name': page_data.get('name'),
            'link': page_data.get('link'),
            'parent': page_data.get('parent'),
            'class': page_data.get('class'),
            'modified': page_data.get('last_modified'),
            'username': page_data.get('username'),
            'children': children_count
        }
        return badge_headers
    

    def _show_page(self, conn=None) -> Dict[str, Any]:
        trace_in()
        # Get base page data
        page_data = self.get_page_data()
        images_data = self.get_images_data()
        # Get children grouped by class (equivalent to legacy displayChildPages)
        children_by_class = self._get_children_by_class()
        # Call display hooks (equivalent to legacy index() hook calls)
        badge_headers = self.add_badge_headers()
        upper_content = self.add_upper_content()
        lower_content = self.add_lower_content()
        response_data = {
            "page": page_data,
            "children_by_class": children_by_class,  # Grouped by class
            "images": images_data,
            "badge_headers": badge_headers,
            "upper_content": upper_content,
            "lower_content": lower_content
        }
        total_children = sum(len(group['children']) for group in children_by_class.values())
        log(f"Assembled display data for page {self.id}: {total_children} children in {len(children_by_class)} classes, {len(images_data)} images")
        trace_out()
        return response_data


    def _get_children_by_class(self) -> Dict[str, Dict[str, Any]]:
        from hh.gateway.connection.connection import r_query
        from hh.page.page_registry import get_page
        trace_in()
        children_by_class = {}
        # Get distinct classes of children (equivalent to legacy line 242)
        query = f"SELECT DISTINCT class FROM pages WHERE parent = {self.id}"
        results = r_query(self.conn, query, [])
        if results:
            for row in results:
                child_class = row['class']
                log(f"Found child class: {child_class}")
                # For each class, get its children using that class's query
                # This is where derived classes' get_children_query() gets called
                children_data = self._get_children_for_class(child_class)
                if children_data:
                    children_by_class[child_class] = {
                        'class': child_class,
                        'children': children_data
                    }
        log(f"Grouped children into {len(children_by_class)} classes: {list(children_by_class.keys())}")
        trace_out()
        return children_by_class


    def _get_children_for_class(self, child_class: str) -> List[Dict[str, Any]]:
        from hh.gateway.connection.connection import r_query
        from hh.page.page_registry import get_page
        from hh.page.page_class_registry import get_page_class
        trace_in()
        # Get the Page subclass for this child_class from the registry
        PageClass = get_page_class(child_class)
        if PageClass is None:
            warn(f"Page class '{child_class}' not found")
            report_error("action", f"Page class '{child_class}' not found")
            trace_out()
            return []
        # Call the class's static get_children_query() method
        query, params = PageClass.get_children_query(self.id)
        log(f"Using query for class '{child_class}': {query[:100]}...")
        results = r_query(self.conn, query, params)
        children_data = []
        if results:
            for row in results:
                child_page = get_page(page_id=row['id'])
                if child_page:
                    child_data = child_page.get_child_page_data()
                    # Add child count for this child page
                    child_count = child_page.get_child_count()
                    child_data['num_children'] = child_count
                    # Add field type for row rendering
                    child_data['field_type'] = child_page.get_child_row_field_type()
                    children_data.append(child_data)
        
        log(f"Loaded {len(children_data)} children for class '{child_class}'")
        trace_out()
        return children_data

