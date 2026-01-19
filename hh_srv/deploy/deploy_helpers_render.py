"""
SRV deployment render hooks for hh_srv module.

Provides summary contribution and detail table for server infrastructure deployment.
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


@register_module_hook('deploy_95_render', 'Contribute SRV summary')
def render_srv_summary_contribution() -> Dict[str, Any]:
    """Contribute SRV infrastructure summary to deployment summary table (1 line)."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Collect srv-related activity
    client_files_count = 0
    site_js_count = 0
    site_css_count = 0
    site_misc_count = 0
    directory_sterilized = False
    site_prepared = False
    permissions_set = False

    for result in hook_results:
        component = result.get('component', '')
        if component == 'client_files' and result.get('files'):
            client_files_count = len(result['files'])
        elif component == 'site_js' and result.get('js_count'):
            site_js_count = result['js_count']
        elif component == 'site_css' and result.get('count'):
            site_css_count = result['count']
        elif component == 'site_misc' and result.get('count'):
            site_misc_count = result['count']
        elif component == 'directory_sterilization':
            directory_sterilized = True
        elif component == 'site_prepare':
            site_prepared = True
        elif component in ('base', 'cache') and result.get('permissions'):
            permissions_set = True

    # If nothing happened, don't add a row
    total_site_files = site_js_count + site_css_count + site_misc_count
    if not (client_files_count > 0 or total_site_files > 0 or directory_sterilized or permissions_set):
        return trace_out({})

    # Build summary line
    summary_parts = []
    if directory_sterilized or site_prepared:
        summary_parts.append("directory prepared")
    if client_files_count > 0:
        summary_parts.append(f"{client_files_count} client files")
    if total_site_files > 0:
        summary_parts.append(f"{total_site_files} site files")
    if permissions_set:
        summary_parts.append("permissions set")

    summary = ", ".join(summary_parts)

    table_data = TableData()
    table_data.add_row('srv_summary', value=summary)

    field_config = FieldConfig()
    field_config.add_simple(['srv_summary'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Render SRV detail table')
def render_srv_detail_table() -> Dict[str, Any]:
    """Render SRV infrastructure details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()
    table_data.add_row('srv_detail_header', target='Target', result='Result')

    has_content = False

    # Add operations
    for result in hook_results:
        component = result.get('component', '')
        if component == 'directory_sterilization' and result.get('items_removed'):
            items_removed = result['items_removed']
            table_data.add_row('directory_sterilization', target='Deployment Directory', result=f"{items_removed} items removed")
            has_content = True
        elif component == 'site_prepare' and result.get('action'):
            action = result['action']
            table_data.add_row('site_prepare', target='Site Directory', result=action)
            has_content = True

    # Add permissions
    for result in hook_results:
        component = result.get('component', '')
        if component == 'base' and result.get('ownership'):
            ownership = result['ownership']
            permissions = result.get('permissions', '')
            table_data.add_row('base_permissions', target='System Files', result=f"{permissions} ({ownership})")
            has_content = True
        elif component == 'cache' and result.get('permissions'):
            dirs_count = result.get('render_cache_dirs_count', 0)
            permissions = result['permissions']
            table_data.add_row('cache_permissions', target=f"{dirs_count} directories", result=permissions)
            has_content = True

    # Add file deployment
    for result in hook_results:
        component = result.get('component', '')
        if component == 'client_files' and result.get('files'):
            files_count = len(result['files'])
            table_data.add_row('client_files_deploy', target='Deployment', result=f"{files_count} files deployed")
            has_content = True
        elif component == 'site_js' and result.get('js_count'):
            js_count = result['js_count']
            table_data.add_row('site_javascript', target='Site', result=f"{js_count} files")
            has_content = True
        elif component == 'site_css' and result.get('count'):
            css_count = result['count']
            table_data.add_row('site_css_deploy', target='Site', result=f"{css_count} files")
            has_content = True
        elif component == 'site_misc' and result.get('count'):
            misc_count = result['count']
            table_data.add_row('site_misc_deploy', target='Site', result=f"{misc_count} files")
            has_content = True

    if not has_content:
        return trace_out({})

    field_config = FieldConfig()
    field_config.add_header('srv_detail_header')
    field_config.add_simple(['directory_sterilization', 'site_prepare', 'base_permissions', 'cache_permissions',
                             'client_files_deploy', 'site_javascript', 'site_css_deploy', 'site_misc_deploy'])

    srv_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='srv_infrastructure')
    return trace_out({
        "render_block": srv_table_html
    })


