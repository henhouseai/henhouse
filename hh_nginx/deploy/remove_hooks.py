"""
NGINX removal hooks for nginx_flask module (hh_nginx category).

Handles NGINX config removal, reload, and decoy cleanup.
"""
import subprocess
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.render.render import TableData, FieldConfig

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

def _install_config_path(project_name: str) -> Path:
    return Path(f"/root/.{project_name}-install.cnf")

def _manifest_get_all_sites(project_name: str) -> List[str]:
    """Get all domains from manifest_sites section."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return []
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_sites"):
        return []
    return list(parser.options("manifest_sites"))


@register_module_hook('remove_00_pre_validate', 'Pre-validate NGINX removal configuration')
def validate_nginx_removal_config() -> Dict[str, Any]:
    """Pre-validate NGINX removal configuration and store results for later hooks."""
    global pre_validated_config
    trace_in()

    log("Validating NGINX removal configuration")

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

    # Get NGINX configuration directories
    nginx_sites_available = Path(sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip())
    nginx_sites_enabled = Path(sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip())

    # Get all deployed sites from manifest
    deployed_domains = _manifest_get_all_sites(project_name)
    log(f"Found {len(deployed_domains)} deployed sites in manifest")

    # Store the parsed config for access by other hooks
    pre_validated_config = {
        'project_name': project_name,
        'deployed_domains': deployed_domains,
        'nginx_sites_available': nginx_sites_available,
        'nginx_sites_enabled': nginx_sites_enabled,
    }

    log(f"Pre-validated NGINX removal config for project: {project_name}")

    return trace_out({
        "project_name": project_name,
        "domains_count": len(deployed_domains),
        "domains": deployed_domains
    })


def _remove_nginx_config(domain: str, nginx_sites_available: Path, nginx_sites_enabled: Path) -> bool:
    """Remove Nginx configuration for a domain."""
    try:
        # Remove symlink from sites-enabled
        enabled_file = nginx_sites_enabled / domain
        if enabled_file.exists():
            enabled_file.unlink()
            log(f"Removed symlink: {enabled_file}")

        # Remove config file from sites-available
        config_file = nginx_sites_available / domain
        if config_file.exists():
            config_file.unlink()
            log(f"Removed config: {config_file}")

        return True

    except Exception as e:
        warn(f"Failed to remove NGINX config for {domain}: {e}")
        return False


@register_module_hook('remove_05_nginx_configs', 'Remove NGINX configurations')
def remove_nginx_configs() -> Dict[str, Any]:
    """Remove NGINX configurations for all deployed domains."""
    trace_in()

    if pre_validated_config is None:
        warn("Pre-validation not completed")
        return trace_out({"status": "skipped", "reason": "no_config"})

    config = pre_validated_config

    deployed_domains = config['deployed_domains']
    nginx_sites_available = config['nginx_sites_available']
    nginx_sites_enabled = config['nginx_sites_enabled']

    nginx_removed: List[str] = []
    nginx_failed: List[str] = []

    for domain in deployed_domains:
        if _remove_nginx_config(domain, nginx_sites_available, nginx_sites_enabled):
            nginx_removed.append(domain)
            log(f"Removed NGINX config for domain: {domain}")
        else:
            nginx_failed.append(domain)
            warn(f"Failed to remove NGINX config for domain: {domain}")

    return trace_out({
        "status": "completed",
        "component": "nginx_configs",
        "domains_removed": nginx_removed,
        "domains_failed": nginx_failed,
        "removed_count": len(nginx_removed)
    })


@register_module_hook('remove_10_nginx_reload', 'Reload NGINX')
def reload_nginx() -> Dict[str, Any]:
    """Test and reload NGINX after config removal."""
    trace_in()

    try:
        # Test NGINX config
        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if test_result.returncode != 0:
            warn(f"NGINX configuration test failed: {test_result.stderr}")
            report_error("action", f"NGINX configuration test failed: {test_result.stderr}")
            return trace_out({
                "status": "error",
                "component": "nginx_reload",
                "error": "config_test_failed",
                "stderr": test_result.stderr
            })

        log("NGINX configuration test passed")

        # Reload NGINX
        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
        if reload_result.returncode != 0:
            # Try restart instead
            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
            if restart_result.returncode != 0:
                warn(f"Failed to reload/restart NGINX: {restart_result.stderr}")
                report_error("action", f"Failed to reload/restart NGINX: {restart_result.stderr}")
                return trace_out({
                    "status": "error",
                    "component": "nginx_reload",
                    "error": "reload_failed"
                })
            log("NGINX restarted successfully")
        else:
            log("NGINX reloaded successfully")

        return trace_out({
            "status": "completed",
            "component": "nginx_reload",
            "nginx_reloaded": True
        })

    except Exception as e:
        warn(f"Failed to test/reload NGINX: {e}")
        report_error("action", f"Failed to test/reload NGINX: {e}")
        return trace_out({"status": "error", "component": "nginx_reload", "error": str(e)})


@register_module_hook('remove_15_nginx_decoy', 'Clean up NGINX decoy')
def cleanup_nginx_decoy() -> Dict[str, Any]:
    """Clean up decoy server if no local deployments remain."""
    trace_in()

    if pre_validated_config is None:
        warn("Pre-validation not completed")
        return trace_out({"status": "skipped", "reason": "no_config"})

    config = pre_validated_config

    nginx_sites_available = config['nginx_sites_available']
    nginx_sites_enabled = config['nginx_sites_enabled']

    try:
        # Check if any local deployments remain (files ending in .local)
        remaining_local = []
        if nginx_sites_available.exists():
            for site_file in nginx_sites_available.iterdir():
                if site_file.is_file() and site_file.name.endswith('.local'):
                    remaining_local.append(site_file.name)

        # If local deployments remain, preserve decoy
        if remaining_local:
            log(f"Decoy preserved - {len(remaining_local)} local deployments remain")
            return trace_out({
                "status": "completed",
                "component": "nginx_decoy",
                "decoy_removed": False,
                "reason": "local_deployments_remain",
                "remaining_local": remaining_local
            })

        # Remove decoy
        decoy_available = nginx_sites_available / "decoy"
        decoy_enabled = nginx_sites_enabled / "decoy"
        decoy_removed = False

        if decoy_enabled.exists():
            decoy_enabled.unlink()
            log("Removed decoy symlink from sites-enabled")
            decoy_removed = True

        if decoy_available.exists():
            decoy_available.unlink()
            log("Removed decoy config from sites-available")
            decoy_removed = True

        if decoy_removed:
            log("Cleaned up decoy server - no local deployments remain")
            # Reload NGINX after decoy removal
            subprocess.run(['nginx', '-t'], capture_output=True, text=True)
            subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)

        return trace_out({
            "status": "completed",
            "component": "nginx_decoy",
            "decoy_removed": decoy_removed
        })

    except Exception as e:
        warn(f"Failed to clean up decoy server: {e}")
        return trace_out({"status": "error", "component": "nginx_decoy", "error": str(e)})


@register_module_hook('remove_95_render', 'Render NGINX removal status')
def render_nginx_removal() -> Dict[str, Any]:
    """Render NGINX module's removal status (configs removed, reload status)."""
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Get nginx-specific data
    domains_removed = []
    nginx_reloaded = False

    for result in hook_results:
        if result.get('component') == 'nginx_configs':
            domains_removed = result.get('domains_removed', [])
        elif result.get('component') == 'nginx_reload':
            nginx_reloaded = result.get('nginx_reloaded', False)

    # Summary row
    summary_parts = []
    if domains_removed:
        summary_parts.append(f"{len(domains_removed)} domains removed")
    if nginx_reloaded:
        summary_parts.append("reloaded")
    summary = ', '.join(summary_parts) if summary_parts else 'No operations'
    table_data.add_row('nginx_summary', value=summary)

    field_config = FieldConfig()
    field_config.add_simple(['nginx_summary'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }
