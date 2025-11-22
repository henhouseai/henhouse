from __future__ import annotations
from typing import Dict, Any, List, Optional
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_method_registry import register_image_mixin_methods
from hh.page.page_registry import get_page

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


@register_image_mixin_methods
def _register_display_methods():
    return {
        'show_image': {'mixin_method': 'show_image', 'decorator': 'read'},
    }


class ImageDisplayMixin:

    def show_image(self) -> Dict[str, Any]:
        trace_in()
        cache_ready = getattr(self, 'cache_hydrated', False) and getattr(self, 'cached_usage', None) is not None
        response_data = {}
        extra_actions: List[Dict[str, Any]] = []

        if cache_ready:
            debug(f"Image {self.id}: serving show_image payload from cache")
            image_data = self.get_image_data()
            usage_data = self.cached_usage or []
            instances_data = self.get_instances_data()
        else:
            image_data = {}
            usage_data = []
            instances_data = []
            if not is_error():
                image_data = self.get_image_data()
                log(f"Retrieved image data for image {self.id}")
            if not is_error():
                usage_data = self._get_usage_data()
                log(f"Retrieved usage data: {len(usage_data)} pages using image {self.id}")
            if not is_error():
                instances_data = self.get_instances_data()
                log(f"Retrieved instances data: {len(instances_data)} instances for image {self.id}")
            if not is_error():
                self.cached_usage = usage_data
                self.cache_hydrated = True
                cache_payload = {
                    "image": image_data,
                    "usage": usage_data,
                    "instances": instances_data,
                }
                original_conn = self.conn
                self.conn = None
                try:
                    self.refresh_cached_image(cache_payload)
                finally:
                    self.conn = original_conn

        if not is_error():
            extra_actions = self._check_extra_actions()
            if extra_actions:
                log(f"Found {len(extra_actions)} extra actions for image {self.id}")

        response_data = {
            "image": image_data,
            "usage": usage_data,
            "instances": instances_data
        }
        if extra_actions:
            response_data["extra_actions"] = extra_actions
        log(f"Generated complete display data for image {self.id}: {self.caption}")
        trace_out()
        return response_data


    def _get_usage_data(self) -> List[Dict[str, Any]]:
        trace_in()
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
                results = r_query(self.conn, query, [self.id])
                for row in results:
                    page_id = row['page_id']
                    page_name = row['page_name'] or f"Page {page_id}"
                    page_class = row['page_class']
                    usage_count = row['usage_count']
                    ranks_str = row['ranks']
                    # Get the page path for breadcrumb display
                    page = get_page(page_id=page_id)
                    path_data = page.get_path() if page else []
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
        # Flag that cache needs refresh since we just hydrated
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
                        'details': orphaned_instances
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
                            'details': {
                                'instance': instance,
                                'filesize_mb': round(filesize / (1024 * 1024), 2)
                            }
                        })
                    # Check for unusual aspect ratios
                    if width > 0 and height > 0:
                        aspect_ratio = width / height
                        if aspect_ratio > 5 or aspect_ratio < 0.2:
                            extra_actions.append({
                                'type': 'info',
                                'message': f"Unusual aspect ratio: {aspect_ratio:.2f}",
                                'details': {
                                    'instance': instance,
                                    'aspect_ratio': aspect_ratio
                                }
                            })
            except Exception as e:
                warn(f"Failed to check image properties: {str(e)}")
        trace_out()
        return extra_actions
