"""
NGINX/Flask deployment render hooks
"""
from typing import Dict, Any
from hh.render.render import TableData, FieldConfig, render_block
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_module_hook('deploy_render')
def render_nginx_flask_summary() -> Dict[str, Any]:
    """Render NGINX/Flask summary pieces for main deployment table."""
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

    # Flask deployment
    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'deploy_apps' and
            result.get('flask_deployed')):
            flask_apps = result['flask_deployed']
            for app in flask_apps:
                table_data.add_row('flask_deployed', value=app)

    # Flask restart status
    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'restart' and
            result.get('flask_restart')):
            flask_data = result['flask_restart']
            daemons = flask_data.get('daemons', [])
            for daemon in daemons:
                tier = daemon.get('tier', 'unknown')
                status = daemon.get('status', 'unknown')
                port = daemon.get('port', 'unknown')
                user = daemon.get('user', 'unknown')
                display = f"{tier}: {status}"
                table_data.add_row('flask_restart', value=display)

    # Site file counts
    if js_count > 0:
        table_data.add_row('js_count', value=f"{js_count} files")
    if css_count > 0:
        table_data.add_row('css_count', value=f"{css_count} files")
    if misc_count > 0:
        table_data.add_row('misc_count', value=f"{misc_count} files")

    field_config = FieldConfig()
    field_config.add_simple(['flask_deployed', 'flask_restart', 'js_count', 'css_count', 'misc_count'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_render')
def render_nginx_domain_table() -> Dict[str, Any]:
    """Render the NGINX domain information as a separate full table."""
    trace_in()

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Get domain config from pre_validate hook results
    domain = 'Unknown'
    ssl_enabled = False
    is_local = False
    for result in hook_results:
        if result.get('domain'):
            domain = result['domain']
            ssl_enabled = result.get('ssl_enabled', False)
            is_local = result.get('is_local', False)
            break

    if not domain:
        return trace_out({"render_block": "<div>No domain configured</div>"})

    # Build domain table
    table_data = TableData()
    table_data.add_row('domain_header', value=domain)

    # Port (443 for SSL, 80 for HTTP-only)
    port = '443' if ssl_enabled else '80'
    table_data.add_row('port', value=port)

    # Certificate path and creation status - read from nginx deployment hook results
    certificate_path = None
    certificate_created = False
    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'deploy_nginx_ssl'):
            certificate_path = result.get('certificate_path')
            certificate_created = result.get('certificate_created', False)
            break

    if certificate_path:
        cert_status = str(certificate_path)
        if certificate_created:
            cert_status += " (created)"
        table_data.add_row('certificate_path', value=cert_status)

    # Server IP binding and local access control - read from nginx deployment hook results
    server_ip = None
    local_allow_block = None
    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'deploy_nginx_ssl'):
            server_ip = result.get('server_ip')
            local_allow_block = result.get('local_allow_block')
            break

    if server_ip and isinstance(server_ip, str):
        table_data.add_row('bind_ips', value=server_ip)

    if is_local and local_allow_block:
        table_data.add_row('client_ip_access', value=local_allow_block)

    # NGINX deployment status from hook results
    hook_results = source_data.get('hook_results', [])
    nginx_deployed = False
    nginx_active = False
    nginx_enabled_sites = []

    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'deploy_nginx_ssl'):
            nginx_deployed = result.get('nginx_deployed', False)
            nginx_active = result.get('nginx_active', False)
            nginx_enabled_sites = result.get('nginx_enabled_sites', [])
            break

    # NGINX status
    table_data.add_row('nginx_deployed', value='Yes' if nginx_deployed else 'No')
    nginx_status = 'Yes (nginx service running)' if nginx_active else 'No'
    table_data.add_row('nginx_active', value=nginx_status)

    field_config = FieldConfig()
    field_config.add_header('domain_header')
    field_config.add_simple(['port', 'certificate_path', 'bind_ips', 'client_ip_access', 'nginx_deployed', 'nginx_active'])

    # Return as full render_block instead of table pieces
    domain_table_html = render_block(table_data, field_config, block_type='domain')
    return trace_out({
        "render_block": domain_table_html
    })