from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.page.page_method_registry import register_page_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_page_ajax_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_mixin_methods
def _register_ajax_methods():
    return {
        'get_page': {'mixin_method': '_get_page', 'decorator': 'read'},
    }


class PageAjaxMixin:

    def _get_page(self, conn=None) -> Dict[str, Any]:
        """Assemble a minimal JSON-friendly payload for AJAX consumption."""
        trace_in()
        page_data = self.get_page_data()
        images_data = self.get_images_data()
        children_by_class = self._get_children_by_class() if hasattr(self, '_get_children_by_class') else {}
        
        # Add path data if available
        if 'path' not in page_data and hasattr(self, '_get_path'):
            path_data = self._get_path()
            if path_data:
                page_data['path'] = path_data

        # Minimal shape; client can expand later
        result: Dict[str, Any] = {
            'page': page_data,
            'images': images_data,
            'children_by_class': children_by_class,
        }
        trace_out()
        return result


