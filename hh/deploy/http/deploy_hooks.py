import configparser
from pathlib import Path
from typing import Optional
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, register_debug_init
from hh.deploy.users.install import _install_config_path

log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global log, warn
    log = get_log(True)
    warn = get_warn(True)

# Pre-validated configuration storage
pre_validated_config: Optional[dict] = None
project_name: Optional[str] = None
current_path: Optional[Path] = None
source: Optional[Path] = None
start_port: Optional[int] = None
domain: Optional[str] = None
ssl_enabled: Optional[bool] = None
ssl_cert_dir_letsencrypt: Optional[Path] = None
ssl_cert_dir_self_signed: Optional[Path] = None
local_allow_block: Optional[str] = None
nginx_sites_available: Optional[Path] = None
nginx_sites_enabled: Optional[Path] = None
certificate_path: Optional[Path] = None
is_local: Optional[bool] = None

@register_module_hook('deploy_pre_validate')
def validate_deployment_config():
    """Pre-validate general deployment configuration and store results for later hooks."""
    global pre_validated_config, project_name, current_path, source, start_port, domain
    global ssl_enabled, ssl_cert_dir_letsencrypt, ssl_cert_dir_self_signed, local_allow_block
    global nginx_sites_available, nginx_sites_enabled, certificate_path, is_local

    log("Validating general deployment configuration")

    # Detect project context
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            break
        current_path = current_path.parent
    else:
        project_name = Path.cwd().name
        current_path = Path.cwd()

    source = current_path

    # Load deployment configuration from install config
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        raise ValueError(f"Install config not found: {cfg_path}")

    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        raise ValueError(f"Missing [install] section in {cfg_path}")

    sec = parser["install"]

    # Get starting port
    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    start_port_arg = gateway.get_arg('start_port') if gateway else None
    if start_port_arg:
        start_port = int(start_port_arg)
    else:
        port_str = sec.get("flask_start_port", "5001").strip()
        try:
            start_port = int(port_str)
        except ValueError:
            start_port = 5001

    # Get domain (required for HTTP deployment)
    domain = sec.get("domain", "").strip()
    if not domain:
        warn("Domain not set in install config")
        raise ValueError("Domain not set in install config")

    # Get SSL enabled setting (required in config, defaults to 1)
    ssl_enabled_str = sec.get("ssl_enabled", "1").strip()
    try:
        ssl_enabled = int(ssl_enabled_str) != 0
    except ValueError:
        ssl_enabled = True  # Default to enabled if invalid value
        warn(f"Invalid ssl_enabled value '{ssl_enabled_str}', defaulting to 1 (enabled)")

    # Get SSL certificate directories
    ssl_cert_dir_letsencrypt_str = sec.get("ssl_cert_dir_letsencrypt", "/etc/letsencrypt/live").strip()
    ssl_cert_dir_letsencrypt = Path(ssl_cert_dir_letsencrypt_str)
    ssl_cert_dir_self_signed_str = sec.get("ssl_cert_dir_self_signed", "/etc/nginx/ssl").strip()
    ssl_cert_dir_self_signed = Path(ssl_cert_dir_self_signed_str)

    # Get local allow block (IP pattern for local deployments)
    local_allow_block = sec.get("local_allow_block", "192.168.1.").strip()

    # Get NGINX configuration directories
    nginx_sites_available_str = sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip()
    nginx_sites_available = Path(nginx_sites_available_str)
    nginx_sites_enabled_str = sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
    nginx_sites_enabled = Path(nginx_sites_enabled_str)

    # Determine certificate path based on certificate type (will be set later based on create_mode)
    # For Let's Encrypt: {ssl_cert_dir_letsencrypt}/{domain}/
    # For self-signed: {ssl_cert_dir_self_signed}/{domain}/
    certificate_path = None

    # Determine if local deployment
    is_local = (domain.endswith('.local') or
                domain.lower() in ['localhost', '127.0.0.1'] or
                domain.startswith('127.') or
                domain.startswith('192.168.') or
                domain.startswith('10.') or
                (domain.startswith('172.') and len(domain.split('.')) >= 2 and
                 domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))

    # Store the parsed config for access by other hooks
    pre_validated_config = {
        'project_name': project_name,
        'current_path': current_path,
        'source': source,
        'start_port': start_port,
        'domain': domain,
        'ssl_enabled': ssl_enabled,
        'ssl_cert_dir_letsencrypt': ssl_cert_dir_letsencrypt,
        'ssl_cert_dir_self_signed': ssl_cert_dir_self_signed,
        'local_allow_block': local_allow_block,
        'nginx_sites_available': nginx_sites_available,
        'nginx_sites_enabled': nginx_sites_enabled,
        'certificate_path': certificate_path,
        'is_local': is_local
    }

    log(f"Pre-validated deployment config for project: {project_name}")

    return {
        "project_name": project_name,
        "source": str(source),
        "domain": domain,
        "is_local": is_local,
        "ssl_enabled": ssl_enabled
    }


@register_module_hook('deploy_render')
def render_deployment_summary():
    """Render the main deployment summary table."""
    from hh.render.render import TableData, FieldConfig, render_block
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Project info - read from hook results (deploy_pre_validate)
    project_name = 'Unknown'
    for result in hook_results:
        if result.get('project_name'):
            project_name = result['project_name']
            break
    table_data.add_row('project_info', value=project_name)

    # Code deployment status - derived from hook results (deploy_modules)
    code_deployed = any(result.get('action') == 'deploy_modules' and result.get('status') == 'completed'
                       for result in hook_results)
    table_data.add_row('code_deployed', value='Yes' if code_deployed else 'No')

    # Deployment cleaning status - derived from hook results (deploy_framework_cleanup)
    deployment_cleaned = any(result.get('component') == 'framework_cleanup' and result.get('status') == 'completed'
                            for result in hook_results)
    table_data.add_row('deployment_cleaned', value='Yes' if deployment_cleaned else 'No')

    # Context deployed files - from hook results (deploy_context)
    for result in hook_results:
        if result.get('component') == 'context_deployment' and result.get('items'):
            for item in result['items']:
                table_data.add_row('context_deployed', value=item)

    # Ownership permissions - from hook results (base permissions)
    for result in hook_results:
        if result.get('component') == 'base' and result.get('ownership'):
            ownership_value = result['ownership']
            table_data.add_row('ownership_set', value=ownership_value)
            break

    # Logs permissions - from hook results (flask_logs, maintenance_logs)
    logs_permissions_set = any(result.get('component') in ['flask_logs', 'maintenance_logs']
                              for result in hook_results)
    if logs_permissions_set:
        table_data.add_row('logs_permissions_set', value='Yes')

    # Cache cleaning - from hook results (deploy_cache_cleanup)
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

    # Flask deployment - from hook results (deploy_flask_apps)
    for result in hook_results:
        if result.get('action') == 'deploy_apps' and result.get('flask_deployed'):
            flask_apps = result['flask_deployed']
            for app in flask_apps:
                table_data.add_row('flask_deployed', value=app)

    # Site deployment - from hook results (site deployment hooks)
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

    if js_count > 0:
        table_data.add_row('js_count', value=f"{js_count} files")
    if css_count > 0:
        table_data.add_row('css_count', value=f"{css_count} files")
    if misc_count > 0:
        table_data.add_row('misc_count', value=f"{misc_count} files")

    # Maintenance restart status - from hook results (deploy_restart_daemons)
    for result in hook_results:
        if (result.get('module') == 'maintenance' and
            result.get('action') == 'restart' and
            result.get('maintenance_restart')):
            maint_data = result['maintenance_restart']
            for daemon_type, daemon_info in maint_data.items():
                if isinstance(daemon_info, dict):
                    status = daemon_info.get('status', 'unknown')
                    log_file = daemon_info.get('log_file', '')
                    user = daemon_info.get('user', '')
                    display = f"{daemon_type}: {status}"
                    if user:
                        display += f" ({user})"
                    table_data.add_row('maintenance_restart', value=display)

    field_config = FieldConfig()
    field_config.add_simple(['project_info', 'code_deployed', 'deployment_cleaned',
                           'context_deployed', 'ownership_set', 'logs_permissions_set',
                           'cache_cleaned', 'flask_deployed', 'js_count', 'css_count', 'misc_count',
                           'maintenance_restart'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }