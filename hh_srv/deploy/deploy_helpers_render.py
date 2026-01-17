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
    table_data.add_row('context_detail_header', item='Context Item', operation='Operation', status='Status')

    for item in context_items:
        table_data.add_row('context_item', item=item, operation='Deployed', status='Success')

    # Add operations info
    for result in hook_results:
        component = result.get('component', '')
        if component == 'directory_sterilization' and result.get('items_removed'):
            items_removed = result['items_removed']
            table_data.add_row('context_item', item='Directory Cleanup', operation='Sterilized', status=f"{items_removed} items removed")
        elif component == 'framework_cleanup' and result.get('modules_count'):
            modules_count = result['modules_count']
            table_data.add_row('context_item', item='Framework', operation='Cleaned', status=f"{modules_count} modules")
        elif component == 'site_prepare' and result.get('action'):
            action = result['action']
            table_data.add_row('context_item', item='Site Directory', operation='Prepared', status=action)

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


@register_module_hook('deploy_95_render', 'Render Permissions detail table')
def render_permissions_detail_table() -> Dict[str, Any]:
    """Render Permissions details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()
    table_data.add_row('perms_header', component='Component', directory='Directory', permissions='Permissions')

    # Collect all permission-related results
    for result in hook_results:
        component = result.get('component', '')

        if component == 'base' and result.get('ownership'):
            ownership = result['ownership']
            permissions = result.get('permissions', '')
            table_data.add_row('perm_row', component='Base', directory='System Files', permissions=f"{permissions} ({ownership})")

        elif component == 'flask_logs' and result.get('permissions'):
            directory = result.get('directory', '')
            permissions = result['permissions']
            table_data.add_row('perm_row', component='Flask Logs', directory=directory, permissions=permissions)

        elif component == 'git' and result.get('permissions'):
            ownership = result.get('ownership', '')
            permissions = result['permissions']
            table_data.add_row('perm_row', component='Git', directory='Repository', permissions=f"{permissions} ({ownership})")

        elif component == 'site' and result.get('permissions'):
            directory = result.get('directory', '')
            permissions = result['permissions']
            table_data.add_row('perm_row', component='Site', directory=directory, permissions=permissions)

        elif component == 'cache' and result.get('permissions'):
            dirs_count = result.get('render_cache_dirs_count', 0)
            permissions = result['permissions']
            table_data.add_row('perm_row', component='Cache', directory=f"{dirs_count} directories", permissions=permissions)

        elif component == 'maintenance_logs':
            note = result.get('note', 'shared')
            table_data.add_row('perm_row', component='Maintenance Logs', directory='', permissions=note)

    field_config = FieldConfig()
    field_config.add_header('perms_header')
    field_config.add_simple(['perm_row'])

    perms_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='permissions')
    return trace_out({
        "render_block": perms_table_html
    })
