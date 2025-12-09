from typing import List, Dict, Any, TYPE_CHECKING
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.mcp_whitelist import MCPWhitelist
from hh.page.page_class_registry import get_page_class
from hh.page.page_registry import get_page
from hh.tp.tp import TextProcessor

if TYPE_CHECKING:
    from hh.page.page_base import BasePage
else:
    class BasePage:
        pass

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




class PageDisplayMixin(BasePage):
    children_by_class: Dict[str, Any]
    
    def _add_upper_content(self) -> List[str]:
        return []
    

    def _add_lower_content(self) -> List[str]:
        return []


    def _get_child_row_field_type(self) -> str:
        """Return the field type for this page when displayed as a child row.
        Override in subclasses to customize the label/icon shown in child tables.
        """
        return 'page'


    def _add_badge_headers(self) -> Dict[str, Any]:
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
    

    def show_page(self) -> Dict[str, Any]:
        trace_in()
        cache_ready = getattr(self, 'cache_hydrated', False) and self.children_by_class is not None
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
        badge_headers = self._add_badge_headers()
        upper_content = self._add_upper_content()
        lower_content = self._add_lower_content()

        prepared_payload = self.get_prepared_text()
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

        # Cache refresh will be handled by wrapper method system if flag is set

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
        # Check if field is already populated
        if hasattr(self, 'children_by_class') and self.children_by_class:
            debug(f"Page {self.id}: returning cached children_by_class")
            return self.children_by_class
        # Field is empty, need to hydrate from database
        trace_in()
        children_by_class = {}
        # Get distinct classes of children (equivalent to legacy line 242)
        query = f"SELECT DISTINCT class FROM pages WHERE parent = {self.id}"
        results = self.gateway.conn.read(query, [])
        if results:
            for row in results:
                child_class = row['class']
                log(f"Found child class: {child_class}")
                # For each class, get its children using that class's static getChildrenOf method
                # This is where derived classes' getChildrenOf() gets called
                PageClass = get_page_class(child_class)
                if PageClass is None:
                    warn(f"Page class '{child_class}' not found")
                    report_error("action", f"Page class '{child_class}' not found")
                    continue
                children_data = PageClass.getChildrenOf(self.id)
                if children_data:
                    children_by_class[child_class] = {
                        'class': child_class,
                        'children': children_data
                    }
        log(f"Grouped children into {len(children_by_class)} classes: {list(children_by_class.keys())}")
        self.children_by_class = children_by_class
        # Only flag cache refresh if we actually found children (data changed)
        # If we just confirmed there are no children (empty dict), no need to refresh
        if children_by_class:
            self._flag_cache_refresh()
        trace_out()
        return children_by_class


    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """
        Class method to get children of a specific class type for a parent page.
        Matches legacy getChildrenOf() pattern - called as class method on child class.
        Each child class can override this to customize default view_type and class-specific behavior.
        
        Uses the class's own _get_children_query() method to get children of that specific class.
        
        Args:
            parent_id: ID of the parent page
            view_type: 'table' or 'tile' (default 'tile' for base class)
        
        Returns:
            List of child page data dictionaries
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return []
        
        # Use the class's own _get_children_query() method
        query, params = cls._get_children_query(parent_id)  # type: ignore[arg-type,call-arg]
        log(f"Using query for class '{cls.__name__}': {query[:500]}...")
        results = gateway.conn.read(query, params)
        children_data = []
        
        if view_type == 'table':
            # Return data formatted for table rendering
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        # Add child count for this child page
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        # Add field type for row rendering
                        child_data['field_type'] = child_page._get_child_row_field_type()
                        # Add format metadata
                        child_data['_format'] = 'table'
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'page' (table format)")
        else:  # view_type == 'tile'
            # Return data formatted for tile rendering
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        # Add display_name (derived field)
                        display_name = child_page._get_display_name()
                        child_data['display_name'] = display_name
                        # Add first image for tile rendering
                        images_data = child_page.get_images_data()
                        if images_data and len(images_data) > 0:
                            child_data['images'] = [images_data[0]]  # Just first image
                        else:
                            child_data['images'] = []
                        # Add format metadata
                        child_data['_format'] = 'tile'
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'page' (tile format)")
        
        trace_out()
        return children_data

