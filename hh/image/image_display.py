from __future__ import annotations
from typing import Dict, Any, List, Optional, cast, TYPE_CHECKING
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page

if TYPE_CHECKING:
    from hh.image.image_base import BaseImage
else:
    class BaseImage:
        pass

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_image_display_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class ImageDisplayMixin(BaseImage):
    cached_usage: Optional[List[Dict[str, Any]]]

    def show_image(self) -> Dict[str, Any]:
        trace_in()
        cache_ready = getattr(self, 'cache_hydrated', False) and getattr(self, 'cached_usage', None) is not None
        if cache_ready:
            debug(f"Image {self.id}: cache available, methods will check cache independently")
        else:
            debug(f"Image {self.id}: cache miss or stale entry; rebuilding show_image payload")
        
        image_data = self.get_image_data()
        usage_data = self._get_usage_data()
        self.get_instances()  # Ensure instances are loaded before get_instances_data()
        instances_data = self.get_instances_data()
        
        extra_actions: List[Dict[str, Any]] = []
        if not is_error():
            extra_actions = self._check_extra_actions()
            if extra_actions:
                log(f"Found {len(extra_actions)} extra actions for image {self.id}")

        response_data: Dict[str, Any] = {
            "image": image_data,
            "usage": usage_data,
            "instances": instances_data
        }
        if extra_actions:
            response_data["extra_actions"] = extra_actions
        
        # Cache refresh will be handled by wrapper method system if flag is set
        log(f"Generated complete display data for image {self.id}: {self.caption}")
        trace_out()
        return response_data


    def _get_usage_data(self) -> List[Dict[str, Any]]:
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'cached_usage') and self.cached_usage is not None:
            debug(f"Image {self.id}: returning cached usage data")
            trace_out()
            return self.cached_usage
        # Field is empty, need to hydrate from database
        usage_data = []
        if not is_error():
            try:
                query = """
                    SELECT 
                        ig.page_id,
                        p.name as page_name,
                        p.class as page_class,
                        COUNT(*) as usage_count,
                        GROUP_CONCAT(ig.image_rank ORDER BY ig.image_rank SEPARATOR ', ') as ranks
                    FROM image_groups ig
                    JOIN pages p ON ig.page_id = p.id
                    WHERE ig.image_id = %s
                    GROUP BY ig.page_id, p.name, p.class
                    ORDER BY p.name
                """
                results = self.gateway.conn.read(query, [self.id])
                for row in results:
                    page_id = row['page_id']
                    page_name = row['page_name'] or f"Page {page_id}"
                    page_class = row['page_class']
                    usage_count = row['usage_count']
                    ranks_str = row['ranks']
                    
                    # Proactively check if page exists before trying to load it
                    page_exists = self.gateway.conn.read(
                        "SELECT 1 FROM pages WHERE id = %s",
                        (page_id,)
                    )
                    if not page_exists:
                        warn(f"Skipping orphaned image_group entry: page {page_id} does not exist")
                        continue
                    
                    # Get the page path for breadcrumb display
                    # Handle failures gracefully - we can still show usage without the path
                    path_data = []
                    try:
                        page = get_page(page_id=page_id)
                        if page:
                            path_data = page.get_path()
                        else:
                            debug(f"Page {page_id} exists but could not be loaded (class={page_class})")
                    except Exception as path_exc:
                        # If we can't load the page for path data, that's okay - we still have usage info
                        debug(f"Could not load page {page_id} for path data (class={page_class}): {path_exc}")
                    usage_item = {
                        'page_id': page_id,
                        'page_name': page_name,
                        'page_class': page_class,
                        'usage_count': usage_count,
                        'ranks': ranks_str,
                        'path': path_data
                    }
                    usage_data.append(usage_item)
                    log(f"Found usage: page {page_id} ({page_name}) - {usage_count} times (ranks {ranks_str})")
                log(f"Found {len(usage_data)} pages using image {self.id}")
            except Exception as e:
                warn(f"Failed to get usage data for image {self.id}: {str(e)}")
                report_error("backend", f"Failed to get usage data: {str(e)}")
        self.cached_usage = usage_data
        # Only flag cache refresh if we actually found usage data (data changed)
        if usage_data:  # Only flag if actual usage data was found
            self._flag_cache_refresh()
        trace_out()
        return usage_data


    def _check_extra_actions(self) -> List[Dict[str, Any]]:
        trace_in()
        extra_actions = []
        if not is_error():
            # Check for orphaned image instances (instances without files)
            try:
                orphaned_instances = []
                instances = self.get_instances()
                for instance in instances:
                    if not instance.get('src') or not instance.get('filesize', 0) > 0:
                        orphaned_instances.append(instance)
                if orphaned_instances:
                    extra_actions.append({
                        'type': 'warning',
                        'message': f"Found {len(orphaned_instances)} orphaned image instances",
                        'details': cast(Any, orphaned_instances)
                    })
            except Exception as e:
                warn(f"Failed to check for orphaned instances: {str(e)}")
        if not is_error():
            # Check for images with no usage (orphaned images)
            try:
                usage_count = self.get_usage_count()
                if usage_count == 0:
                    extra_actions.append({
                        'type': 'info',
                        'message': "Image is not used by any pages",
                        'details': {"usage_count": usage_count}
                    })
            except Exception as e:
                warn(f"Failed to check usage count: {str(e)}")
        if not is_error():
            # Check for images with unusual file sizes or dimensions
            try:
                instances = self.get_instances()
                for instance in instances:
                    width = instance.get('width', 0)
                    height = instance.get('height', 0)
                    filesize = instance.get('filesize', 0)
                    # Check for unusually large files
                    if filesize > 10 * 1024 * 1024:  # 10MB
                        extra_actions.append({
                            'type': 'warning',
                            'message': f"Large file detected: {filesize} bytes",
                            'details': cast(Any, {
                                'instance': instance,
                                'filesize_mb': round(filesize / (1024 * 1024), 2)
                            })
                        })
                    # Check for unusual aspect ratios
                    if width > 0 and height > 0:
                        aspect_ratio = width / height
                        if aspect_ratio > 5 or aspect_ratio < 0.2:
                            extra_actions.append({
                                'type': 'info',
                                'message': f"Unusual aspect ratio: {aspect_ratio:.2f}",
                                'details': cast(Any, {
                                    'instance': instance,
                                    'aspect_ratio': aspect_ratio
                                })
                            })
            except Exception as e:
                warn(f"Failed to check image properties: {str(e)}")
        trace_out()
        return extra_actions
