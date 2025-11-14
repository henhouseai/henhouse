from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.mcp_whitelist import MCPWhitelist
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
        
        # Add available app actions if HTTP backend
        gateway = get_gateway()
        
        # Debug information
        result['_debug'] = {
            'gateway_exists': gateway is not None,
            'backend': gateway.backend if gateway else None,
            'backend_is_http': gateway.backend == "http" if gateway else False,
            'response_exists': gateway.response is not None if gateway else False,
            'user_tier_level': gateway.response.get_user_tier_level() if (gateway and gateway.response) else None,
            'mcp_utils_loaded': False,  # Will be set below
            'app_actions_called': False,
            'app_actions_count': 0,
            'app_actions_result': None,
            'error': None
        }
        
        if gateway and gateway.backend == "http" and gateway.response:
            try:
                user_tier_level = gateway.response.get_user_tier_level()
                result['_debug']['user_tier_level'] = user_tier_level
                
                # Check if mcp_utils was loaded (check if any app actions exist in registry)
                from hh.gateway.registry.mcp_whitelist import _global_tool_registry
                result['_debug']['mcp_utils_loaded'] = len(_global_tool_registry) > 0
                result['_debug']['tool_registry_size'] = len(_global_tool_registry)
                
                # get_app_actions() adds 4 to user_tier_level and checks for app actions at that tier
                app_actions = MCPWhitelist.get_app_actions(user_tier_level)
                result['_debug']['app_actions_called'] = True
                result['_debug']['app_actions_count'] = len(app_actions) if app_actions else 0
                result['_debug']['app_actions_result'] = app_actions if app_actions else []
                
                if app_actions:
                    result['available_actions'] = app_actions
                    log(f"Added {len(app_actions)} app actions to get_page response")
            except Exception as e:
                result['_debug']['error'] = str(e)
                log(f"Error getting app actions: {e}")
        
        trace_out()
        return result


