"""
Site deployment render hooks for hh_srv module.
"""
from typing import Dict, Any
from hh.render.render import TableData, FieldConfig, render_block
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init

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


@register_module_hook('deploy_95_render', 'Render site deployment summary')
def render_site_summary() -> Dict[str, Any]:
    """Render site deployment summary pieces for main deployment table."""
    trace_in()

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}

    table_data = TableData()

    # Get site deployment counts from hook results
    hook_results = source_data.get('hook_results', [])
    js_count = 0
    css_count = 0
    misc_count = 0

    for result in hook_results:
        if result.get('component') == 'site_js' and result.get('js_count'):
            js_count = result['js_count']
        elif result.get('component') == 'site_css' and result.get('count'):
            css_count = result['count']
        elif result.get('component') == 'site_misc' and result.get('count'):
            misc_count = result['count']

    # Site file counts
    if js_count > 0:
        table_data.add_row('js_count', value=f"{js_count} files")
    if css_count > 0:
        table_data.add_row('css_count', value=f"{css_count} files")
    if misc_count > 0:
        table_data.add_row('misc_count', value=f"{misc_count} files")

    field_config = FieldConfig()
    field_config.add_simple(['js_count', 'css_count', 'misc_count'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Render cache operations')
def render_cache_operations():
    """Render cache-specific deployment operations."""
    from hh.render.render import TableData, FieldConfig
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Cache cleaning details - read from hook results
    for result in hook_results:
        if result.get('component') == 'cache_cleanup' and result.get('cache_cleaned'):
            cache_cleaned = result['cache_cleaned']
            if isinstance(cache_cleaned, dict):
                if cache_cleaned.get('pycache_dirs', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['pycache_dirs']} __pycache__ dirs")
                if cache_cleaned.get('pyc_files', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['pyc_files']} .pyc files")
                if cache_cleaned.get('cache_files', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['cache_files']} cache files")
                if cache_cleaned.get('cache_dirs', 0) > 0:
                    table_data.add_row('cache_cleaned', value=f"{cache_cleaned['cache_dirs']} .cache dirs")
            break

    # Cache permissions - read from hook results
    cache_permissions_set = any(result.get('component') == 'cache' and result.get('status') == 'completed'
                               for result in hook_results)
    table_data.add_row('cache_permissions', value='Yes' if cache_permissions_set else 'No')

    field_config = FieldConfig()
    field_config.add_simple(['cache_cleaned', 'cache_permissions'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }
