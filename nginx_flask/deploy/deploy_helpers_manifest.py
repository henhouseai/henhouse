"""
Manifest management helper for nginx_flask module.

Handles adding deployed sites to the manifest.
"""

import configparser
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


def _iso_now() -> str:
    import datetime
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _manifest_add_site(project_name: str, domain: str, mode: str) -> None:
    """Add a site to the manifest in the install config."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_sites"):
        parser.add_section("manifest_sites")
    entry = {"domain": domain, "mode": mode, "timestamp": _iso_now()}
    # Use domain as key, store mode and timestamp
    parser.set("manifest_sites", domain, f"{mode}:{_iso_now()}")
    with open(cfg_path, 'w') as f:
        parser.write(f)


@register_module_hook('deploy_manifest')
def add_site_to_manifest() -> dict:
    """Add the deployed site to the manifest with appropriate SSL mode."""
    # Access pre-validated config from the shared storage
    from nginx_flask.deploy.deploy_hooks import pre_validated_whitelists

    http_config = pre_validated_whitelists.get('http_config')
    if http_config is None:
        warn("nginx_flask manifest: HTTP pre-validation not completed - cannot add site to manifest")
        return {"status": "skipped", "reason": "no_config"}

    project_name = http_config['project_name']
    domain = http_config['domain']
    ssl_enabled = http_config.get('ssl_enabled', True)

    # Determine deployment mode based on SSL configuration
    deployment_mode = "https" if ssl_enabled else "http"

    try:
        _manifest_add_site(project_name, domain, deployment_mode)
        log(f"nginx_flask manifest: Added site to manifest: {project_name} ({domain}) - mode: {deployment_mode}")
        return {"status": "completed", "project_name": project_name, "domain": domain, "deployment_mode": deployment_mode}
    except Exception as e:
        warn(f"nginx_flask manifest: Failed to add site to manifest: {e}")
        return {"status": "error", "reason": str(e)}