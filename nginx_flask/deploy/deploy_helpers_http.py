"""
HTTP configuration helper for nginx_flask module.

Handles HTTP-specific configuration validation.
"""

from pathlib import Path
from typing import Dict, Any
from hh.deploy.users.install import _install_config_path
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.registry.module_hooks import register_module_hook

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


@register_module_hook('deploy_pre_validate')
def validate_http_config():
    """Pre-validate HTTP deployment configuration and store results for later hooks."""
    # Access shared storage from deploy_hooks
    from nginx_flask.deploy.deploy_hooks import pre_validated_whitelists

    log("Validating HTTP deployment configuration")

    # Detect project context
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            break
    else:
        project_name = Path.cwd().name
        current_path = Path.cwd()

    source = current_path

    # Load deployment configuration from install config
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        raise ValueError(f"Install config not found: {cfg_path}")

    import configparser
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

    # Store the parsed config in shared storage
    pre_validated_whitelists['http_config'] = {
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

    log(f"Pre-validated HTTP deployment config for project: {project_name}")

    return {
        "project_name": project_name,
        "source": str(source),
        "domain": domain,
        "is_local": is_local,
        "ssl_enabled": ssl_enabled
    }