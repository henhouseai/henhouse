"""
SRV deployment render hooks for hh_srv module.

Detail tables showing context items, client files, permissions, and operations.
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


@register_module_hook('deploy_95_render', 'Render Context detail table')
def render_context_detail_table() -> Dict[str, Any]:
    """Render Context deployment details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find context deployment data
    context_items = []
    for result in hook_results:
        if result.get('component') == 'context_deployment' and result.get('items'):
            context_items = result['items']
            break

    if not context_items:
        return trace_out({})

    table_data = TableData()
    table_data.add_row('context_detail_header', value='')

    for item in context_items:
        table_data.add_row('context_item', value=item)

    field_config = FieldConfig()
    field_config.add_header('context_detail_header')
    field_config.add_simple(['context_item'])

    context_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='context_items')
    return trace_out({
        "render_block": context_table_html
    })


@register_module_hook('deploy_95_render', 'Render Client Files detail table')
def render_client_files_detail_table() -> Dict[str, Any]:
    """Render Client files deployment details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find client files data
    client_files = []
    for result in hook_results:
        if result.get('component') == 'client_files' and result.get('files'):
            client_files = result['files']
            break

    if not client_files:
        return trace_out({})

    table_data = TableData()
    table_data.add_row('client_detail_header', value='')

    for f in client_files:
        table_data.add_row('client_file', value=f)

    field_config = FieldConfig()
    field_config.add_header('client_detail_header')
    field_config.add_simple(['client_file'])

    client_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='client_files')
    return trace_out({
        "render_block": client_table_html
    })




@register_module_hook('deploy_95_render', 'Render Site Files detail table')
def render_site_files_detail_table() -> Dict[str, Any]:
    """Render Site files (JS, CSS, Misc) details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()
    table_data.add_row('site_detail_header', value='')

    field_names = []

    for result in hook_results:
        component = result.get('component', '')

        if component == 'site_js' and result.get('js_count'):
            count = result['js_count']
            table_data.add_row('site_js', value=f"{count} files")
            field_names.append('site_js')

        elif component == 'site_css' and result.get('count'):
            count = result['count']
            table_data.add_row('site_css', value=f"{count} files")
            field_names.append('site_css')

        elif component == 'site_misc' and result.get('count'):
            count = result['count']
            table_data.add_row('site_misc', value=f"{count} files")
            field_names.append('site_misc')

    if not field_names:
        return trace_out({})

    field_config = FieldConfig()
    field_config.add_header('site_detail_header')
    field_config.add_simple(field_names)

    site_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='site_files')
    return trace_out({
        "render_block": site_table_html
    })


@register_module_hook('deploy_95_render', 'Contribute SRV permissions to summary')
def render_srv_permissions_contribution() -> Dict[str, Any]:
    """Contribute SRV-related permissions to deployment summary table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find SRV-related permission data
    srv_perms = []
    for result in hook_results:
        component = result.get('component', '')
        if component == 'base' and result.get('ownership'):
            ownership = result['ownership']
            permissions = result.get('permissions', '')
            srv_perms.append(f"Base: {permissions} ({ownership})")
        elif component == 'cache' and result.get('permissions'):
            dirs_count = result.get('render_cache_dirs_count', 0)
            permissions = result['permissions']
            srv_perms.append(f"Cache: {permissions} ({dirs_count} directories)")
        elif component == 'maintenance_logs' and result.get('permissions'):
            permissions = result.get('permissions', 'shared')
            srv_perms.append(f"Maintenance Logs: {permissions}")

    if not srv_perms:
        return trace_out({})

    table_data = TableData()
    for perm in srv_perms:
        table_data.add_row('srv_permissions', value=perm)

    field_config = FieldConfig()
    field_config.add_simple(['srv_permissions'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Contribute SRV operations to summary')
def render_srv_operations_contribution() -> Dict[str, Any]:
    """Contribute SRV-related operations to deployment summary table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find SRV-related operation data
    srv_ops = []
    for result in hook_results:
        component = result.get('component', '')
        if component == 'directory_sterilization' and result.get('items_removed'):
            items_removed = result['items_removed']
            srv_ops.append(f"Directory sterilized: {items_removed} items removed")
        elif component == 'framework_cleanup' and result.get('modules_count'):
            modules_count = result['modules_count']
            srv_ops.append(f"Framework cleaned: {modules_count} modules")
        elif component == 'site_prepare' and result.get('action'):
            action = result['action']
            srv_ops.append(f"Site directory: {action}")

    if not srv_ops:
        return trace_out({})

    table_data = TableData()
    for op in srv_ops:
        table_data.add_row('srv_operations', value=op)

    field_config = FieldConfig()
    field_config.add_simple(['srv_operations'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Contribute module deployment status')
def render_module_deployment_contribution() -> Dict[str, Any]:
    """Contribute module deployment status to summary."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find modules deployed data
    modules_deployed = []
    for result in hook_results:
        if result.get('action') == 'deploy_modules' and result.get('modules_deployed'):
            modules_deployed = result['modules_deployed']
            break

    if not modules_deployed:
        return trace_out({})

    table_data = TableData()
    table_data.add_row('modules_deployed', value=f"{len(modules_deployed)} modules deployed")

    field_config = FieldConfig()
    field_config.add_simple(['modules_deployed'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
