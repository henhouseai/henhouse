from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.mcp_whitelist import MCPWhitelist
from hh.page.page_registry import get_page

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_action('get_app_actions')
@register_command('get_app_actions')
def get_app_actions() -> bool:
    """Return available app actions for the current user tier level and page."""
    trace_in()
    gateway = get_gateway()
    
    if not gateway.is_set('id'):
        warn("No page id provided")
        report_error("action", "Page ID is required")
        trace_out()
        return False
    
    if not gateway.response:
        warn("No response object available")
        report_error("action", "Response object not available")
        trace_out()
        return False
    
    page_id: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg('id')
        log(f"Using page ID: {page_id_arg}")
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    
    page_obj = None
    if not is_error():
        page_obj = get_page(page_id=page_id)
        if not page_obj:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    try:
        user_tier_level = gateway.response.get_user_tier_level()
        
        # get_app_actions() adds 4 to user_tier_level and checks for app actions at that tier
        # Loading the page triggers mcp_utils loading which populates the registry with page-specific actions
        app_actions = MCPWhitelist.get_app_actions(user_tier_level)
        
        # Add source field to mark these as hot_cache
        for action in app_actions:
            action['source'] = 'hot_cache'
        
        response_data = {
            'available_actions': app_actions
        }
        
        gateway.response.set_action_response(success_payload(response_data))
        log(f"Returned {len(app_actions)} app actions for tier level {user_tier_level}, page {page_id}")
        
    except Exception as e:
        warn(f"Error getting app actions: {e}")
        report_error("action", f"Error getting app actions: {e}")
    
    trace_out()
    return not is_error()
