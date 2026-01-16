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


@register_module_hook('deploy_render')
def render_deployment_summary():
    """Render the main deployment summary table."""
    from hh.render.render import TableData, FieldConfig, render_block

    # Get pre-validated config
    if pre_validated_config is None:
        return {"render_block": "<div>Pre-validation not completed</div>"}

    table_data = TableData()
    table_data.add_row('project_name', value=pre_validated_config['project_name'])
    table_data.add_row('source_path', value=str(pre_validated_config['source']))
    table_data.add_row('domain', value=pre_validated_config['domain'])
    table_data.add_row('ssl_enabled', value='Yes' if pre_validated_config['ssl_enabled'] else 'No')
    table_data.add_row('is_local', value='Yes' if pre_validated_config['is_local'] else 'No')

    field_config = FieldConfig()
    field_config.add_simple(['project_name', 'source_path', 'domain', 'ssl_enabled', 'is_local'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }