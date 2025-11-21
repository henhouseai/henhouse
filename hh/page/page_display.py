from typing import List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.mcp_whitelist import MCPWhitelist
from hh.page.page_method_registry import register_page_mixin_methods
from hh.tp.tp import TextProcessor

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
        if hasattr(self, 'cached_upper_content') and self.cached_upper_content is not None:
            debug(f"Page {self.id}: returning cached upper_content")
            return self.cached_upper_content
        return []
    

    def add_lower_content(self) -> List[str]:
        if hasattr(self, 'cached_lower_content') and self.cached_lower_content is not None:
            debug(f"Page {self.id}: returning cached lower_content")
            return self.cached_lower_content
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
        cache_ready = getattr(self, 'cache_hydrated', False) and self.cached_children_by_class is not None
        lightweight = False
        gateway = get_gateway()
        if gateway and gateway.backend == "mcp":
            lightweight = True
        if cache_ready and not lightweight:
            debug(f"Page {self.id}: cache available, methods will check cache independently")
        if lightweight:
            debug(f"Page {self.id}: cache miss or stale entry; rebuilding lightweight payload")
        else:
            debug(f"Page {self.id}: cache miss or stale entry; rebuilding show_page payload")
        page_data = self.get_page_data()
        images_data = self.get_images_data()
        files_data = self.get_files_data()
        children_by_class = self._get_children_by_class()
        badge_headers = self.add_badge_headers()
        upper_content = self.add_upper_content()
        lower_content = self.add_lower_content()

        prepared_payload = self.cached_prepared_text
        if prepared_payload is None:
            prepared_payload = self.get_cached_prepared_text_if_current()
        if prepared_payload is None:
            processor = TextProcessor()
            prepared_payload = processor.preprocess(self.text or "")
            if prepared_payload is None:
                warn(f"Failed to preprocess text for page {self.id} while rebuilding cache")
            else:
                self.cached_prepared_text = prepared_payload

        if prepared_payload is not None:
            page_data = dict(page_data)
            page_data['prepared_text'] = prepared_payload

        if lightweight:
            response_data = {
                "page": page_data,
                "images": images_data,
                "children_by_class": children_by_class,
                "files": files_data,
            }
            if gateway and gateway.backend == "mcp" and gateway.response:
                try:
                    user_tier_level = gateway.response.get_user_tier_level()
                    app_actions = MCPWhitelist.get_app_actions(user_tier_level)
                    if app_actions:
                        for action in app_actions:
                            action['source'] = 'hot_cache'
                        response_data['available_actions'] = app_actions
                except Exception as exc:
                    warn(f"Failed to load MCP actions: {exc}")
        else:
            response_data = {
                "page": page_data,
                "children_by_class": children_by_class,
                "images": images_data,
                "files": files_data,
                "badge_headers": badge_headers,
                "upper_content": upper_content,
                "lower_content": lower_content,
            }

        original_conn = self.conn
        self.conn = None
        try:
            self.refresh_cached_page(self.text, prepared_payload, cache_payload=response_data)
        finally:
            self.conn = original_conn

        total_children = sum(len(group['children']) for group in children_by_class.values())
        file_count = len(files_data)
        if lightweight:
            log(
                f"Assembled lightweight display data for page {self.id}: "
                f"{total_children} children in {len(children_by_class)} classes, "
                f"{len(images_data)} images, {file_count} files"
            )
        else:
            log(
                f"Assembled display data for page {self.id}: "
                f"{total_children} children in {len(children_by_class)} classes, "
                f"{len(images_data)} images, {file_count} files"
            )
        trace_out()
        return response_data


    def _get_children_by_class(self) -> Dict[str, Dict[str, Any]]:
        if hasattr(self, 'cached_children_by_class') and self.cached_children_by_class is not None:
            debug(f"Page {self.id}: returning cached children_by_class")
            return self.cached_children_by_class
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

