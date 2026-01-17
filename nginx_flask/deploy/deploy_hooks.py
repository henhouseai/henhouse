from typing import Dict, Any, List
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.deploy.deploy_utils import load_whitelist_with_extensions

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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

# Pre-validated configuration storage for nginx_flask module
pre_validated_whitelists: Dict[str, List[str]] = {}

@register_module_hook('deploy_00_pre_validate')
def validate_nginx_flask_config():
    """Pre-validate NGINX/Flask specific configuration including whitelists."""
    global pre_validated_whitelists

    log("Validating NGINX/Flask deployment configuration")

    # Load whitelists that will be used by site deployment hooks
    try:
        pre_validated_whitelists['JS_WHITELIST'] = load_whitelist_with_extensions('js_whitelist', 'JS_WHITELIST')
        pre_validated_whitelists['CSS_WHITELIST'] = load_whitelist_with_extensions('css_whitelist', 'CSS_WHITELIST')
        pre_validated_whitelists['JS_PAGE_CLASSES_WHITELIST'] = load_whitelist_with_extensions('js_page_classes_whitelist', 'JS_PAGE_CLASSES_WHITELIST')
        pre_validated_whitelists['MISC_WHITELIST'] = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')

        log("Pre-validated NGINX/Flask whitelists")
    except Exception as e:
        warn(f"Failed to load NGINX/Flask whitelists: {e}")
        raise ValueError(f"Failed to load NGINX/Flask whitelists: {e}")

