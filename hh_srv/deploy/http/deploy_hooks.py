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


@register_module_hook('deploy_95_render', 'Render deployment summary')
def render_deployment_summary():
    """Render the main deployment summary table - ONE row per category max."""
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Project header
    project_name = 'Unknown'
    for result in hook_results:
        if result.get('project_name'):
            project_name = result['project_name']
            break
    table_data.add_row('project_header', value=project_name)

    # Modules deployed - consolidated count
    for result in hook_results:
        if result.get('action') == 'deploy_modules' and result.get('modules_count'):
            table_data.add_row('modules_deployed', value=f"{result['modules_count']} modules")
            break

    # Context deployed - consolidated count
    for result in hook_results:
        if result.get('component') == 'context_deployment' and result.get('total_items'):
            table_data.add_row('context_deployed', value=f"{result['total_items']} items")
            break

    # Site files - consolidated (js + css + misc)
    js_count = css_count = misc_count = 0
    for result in hook_results:
        if result.get('component') == 'site_js':
            js_count = result.get('js_count', 0)
        elif result.get('component') == 'site_css':
            css_count = result.get('count', 0)
        elif result.get('component') == 'site_misc':
            misc_count = result.get('count', 0)
    total_site = js_count + css_count + misc_count
    if total_site > 0:
        table_data.add_row('site_files', value=f"{total_site} files ({js_count} js, {css_count} css, {misc_count} misc)")

    # Cache cleaned - consolidated
    for result in hook_results:
        if result.get('component') == 'cache_cleanup' and result.get('cache_cleaned'):
            cc = result['cache_cleaned']
            if isinstance(cc, dict):
                parts = []
                if cc.get('pycache_dirs', 0) > 0:
                    parts.append(f"{cc['pycache_dirs']} dirs")
                if cc.get('cache_files', 0) > 0:
                    parts.append(f"{cc['cache_files']} files")
                if parts:
                    table_data.add_row('cache_cleaned', value=', '.join(parts))
            break

    # Flask summary - consolidated (detail in Flask module table)
    for result in hook_results:
        if result.get('module') == 'hh_flask' and result.get('action') == 'restart':
            flask_data = result.get('flask_restart', {})
            summary = flask_data.get('summary', {})
            total = summary.get('total', 0)
            started = summary.get('started', 0)
            failed = summary.get('failed', 0)
            if total > 0:
                table_data.add_row('flask_summary', value=f"{total} daemons ({started} started, {failed} failed)")
            break

    # Maintenance summary - consolidated (detail in Maintenance module table)
    for result in hook_results:
        if result.get('module') == 'maintenance' and result.get('action') == 'restart':
            maint_data = result.get('maintenance_restart', {})
            daemon_count = len([k for k, v in maint_data.items() if isinstance(v, dict) and v])
            if daemon_count > 0:
                main_status = maint_data.get('main', {}).get('status', 'unknown')
                table_data.add_row('maintenance_summary', value=f"{daemon_count} daemon ({main_status})")
            break

    # NGINX summary - consolidated (detail in NGINX module table)
    for result in hook_results:
        if result.get('module') == 'hh_nginx' and result.get('action') == 'restart_nginx':
            nginx_active = result.get('nginx_active', False)
            # Get domain from pre_validate
            domain = 'unknown'
            ssl_enabled = False
            for r in hook_results:
                if r.get('domain'):
                    domain = r['domain']
                    ssl_enabled = r.get('ssl_enabled', False)
                    break
            port = '443' if ssl_enabled else '80'
            status = 'Active' if nginx_active else 'Inactive'
            table_data.add_row('nginx_summary', value=f"{status} ({domain}:{port})")
            break

    field_config = FieldConfig()
    field_config.add_simple(['project_header', 'modules_deployed', 'context_deployed', 'site_files',
                            'cache_cleaned', 'flask_summary', 'maintenance_summary', 'nginx_summary'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }
