"""
HTTP deployment hooks for hh_srv module.

Pre-validation, manifest management, and deployment summary rendering.
"""

import configparser
from pathlib import Path
from typing import Optional
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.render import TableData, FieldConfig, render_block
from hh.deploy.users.install import _install_config_path

# Debug initialization
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

# Pre-validated configuration storage
pre_validated_config: Optional[dict] = None
project_name: Optional[str] = None
current_path: Optional[Path] = None
source: Optional[Path] = None
start_port: Optional[int] = None
domain: Optional[str] = None
ssl_enabled: Optional[bool] = None
is_local: Optional[bool] = None


@register_module_hook('deploy_00_pre_validate', 'Pre-validate general deployment configuration')
def validate_deployment_config():
    """Pre-validate general deployment configuration and store results for later hooks."""
    global pre_validated_config, project_name, current_path, source, start_port, domain
    global ssl_enabled, is_local

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


@register_module_hook('deploy_90_manifest', 'Add deployed site to manifest with SSL mode')
def add_site_to_manifest():
    """Add the deployed site to the manifest with appropriate SSL mode."""
    from .deploy_helpers import _manifest_add_site

    if pre_validated_config is None:
        warn("Pre-validation not completed - cannot add site to manifest")
        return {"status": "skipped", "reason": "no_config"}

    project_name = pre_validated_config['project_name']
    domain = pre_validated_config['domain']
    ssl_enabled = pre_validated_config.get('ssl_enabled', True)

    # Determine deployment mode based on SSL configuration
    deployment_mode = "https" if ssl_enabled else "http"

    try:
        _manifest_add_site(project_name, domain, deployment_mode)
        log(f"Added site to manifest: {project_name} ({domain}) - mode: {deployment_mode}")
        return {"status": "completed", "project_name": project_name, "domain": domain, "deployment_mode": deployment_mode}
    except Exception as e:
        warn(f"Failed to add site to manifest: {e}")
        return {"status": "error", "reason": str(e)}
