"""
NGINX domain table render hook for hh_nginx module.
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


@register_module_hook('deploy_95_render', 'Contribute NGINX summary')
def render_nginx_summary_contribution() -> Dict[str, Any]:
    """Contribute NGINX summary to deployment summary table (1 line)."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Collect nginx activity
    domain = None
    ssl_enabled = False
    nginx_active = False

    for result in hook_results:
        if result.get('domain'):
            domain = result['domain']
            ssl_enabled = result.get('ssl_enabled', False)
        if result.get('nginx_active'):
            nginx_active = True

    if not domain:
        return trace_out({})

    # Build summary line
    protocol = "https" if ssl_enabled else "http"
    status = "active" if nginx_active else "deployed"
    summary = f"{protocol}://{domain} ({status})"

    table_data = TableData()
    table_data.add_row('nginx_summary', value=f"NGINX: {summary}")

    field_config = FieldConfig()
    field_config.add_simple(['nginx_summary'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Render domain table')
def render_nginx_domain_table() -> Dict[str, Any]:
    """Render the NGINX domain information as a separate full table."""
    trace_in()

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Get domain config from pre_validate hook results or nginx config hook
    domain = 'Unknown'
    ssl_enabled = False
    is_local = False
    for result in hook_results:
        if result.get('domain'):
            domain = result['domain']
            ssl_enabled = result.get('ssl_enabled', False)
            is_local = result.get('is_local', False)
            break

    if not domain or domain == 'Unknown':
        return trace_out({"render_block": "<div>No domain configured</div>"})

    # Build domain table
    table_data = TableData()
    table_data.add_row('domain_header', setting='Setting', value='Value', permissions='Permissions')

    # Port (443 for SSL, 80 for HTTP-only)
    port = '443' if ssl_enabled else '80'
    table_data.add_row('domain_setting', setting='Port', value=port, permissions='N/A')

    # Certificate path and creation status - read from nginx deployment hook results
    certificate_path = None
    certificate_created = False
    for result in hook_results:
        # Check for results from both old (nginx_flask) and new (hh_nginx) modules
        if ((result.get('module') == 'nginx_flask' and result.get('action') == 'deploy_nginx_ssl') or
            (result.get('module') == 'hh_nginx' and result.get('action') == 'deploy_ssl_certificates')):
            certificate_path = result.get('certificate_path')
            certificate_created = result.get('certificate_created', False)
            if certificate_path:
                break

    if certificate_path:
        cert_status = str(certificate_path)
        if certificate_created:
            cert_status += " (created)"
        table_data.add_row('domain_setting', setting='Certificate', value=cert_status, permissions='600')

    # Server IP binding and local access control - read from nginx config hook results
    server_ip = None
    local_allow_block = None
    for result in hook_results:
        # Check for results from both old (nginx_flask) and new (hh_nginx) modules
        if ((result.get('module') == 'nginx_flask' and result.get('action') == 'deploy_nginx_ssl') or
            (result.get('module') == 'hh_nginx' and result.get('action') == 'deploy_nginx_config')):
            server_ip = result.get('server_ip')
            local_allow_block = result.get('local_allow_block')
            if server_ip:
                break

    if server_ip and isinstance(server_ip, str):
        table_data.add_row('domain_setting', setting='Server IP', value=server_ip, permissions='644')

    if is_local and local_allow_block:
        table_data.add_row('domain_setting', setting='Local Access', value=local_allow_block, permissions='N/A')

    # NGINX deployment status from hook results
    nginx_deployed = False
    nginx_active = False
    nginx_enabled_sites = []

    for result in hook_results:
        # Check for results from both old (nginx_flask) and new (hh_nginx) modules
        if ((result.get('module') == 'nginx_flask' and result.get('action') == 'deploy_nginx_ssl') or
            (result.get('module') == 'hh_nginx' and result.get('action') == 'restart_nginx')):
            if result.get('nginx_deployed') is not None:
                nginx_deployed = result.get('nginx_deployed', False)
            if result.get('nginx_restarted') is not None:
                nginx_deployed = result.get('nginx_restarted', False)
            nginx_active = result.get('nginx_active', False)
            nginx_enabled_sites = result.get('nginx_enabled_sites', [])
            if nginx_active:
                break

    # NGINX status
    table_data.add_row('domain_setting', setting='NGINX Deployed', value='Yes' if nginx_deployed else 'No', permissions='755')
    nginx_status = 'Yes (nginx service running)' if nginx_active else 'No'
    table_data.add_row('domain_setting', setting='NGINX Active', value=nginx_status, permissions='N/A')

    field_config = FieldConfig()
    field_config.add_header('domain_header')
    field_config.add_simple(['domain_setting'])

    # Return as full render_block instead of table pieces
    domain_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='domain')
    return trace_out({
        "render_block": domain_table_html
    })
