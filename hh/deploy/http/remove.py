import os
import shutil
import subprocess
import configparser
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.maintenance.maintenance_stop import run_maintenance_stop
from hh.deploy.users.install import _load_install_config

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

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

def _manifest_clear_all_sites(project_name: str) -> None:
    """Remove all sites from manifest_sites section."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if parser.has_section("manifest_sites"):
        parser.remove_section("manifest_sites")
        with open(cfg_path, 'w') as f:
            parser.write(f)
        os.chmod(cfg_path, 0o600)

def remove_nginx_config(domain: str, project_name: str, nginx_sites_available: Optional[Path] = None, nginx_sites_enabled: Optional[Path] = None) -> bool:
    """Remove Nginx configuration for domain."""
    trace_in()
    try:
        # Load nginx paths from config if not provided
        if nginx_sites_available is None or nginx_sites_enabled is None:
            from hh.deploy.users.install import _load_install_config
            install_config = _load_install_config(project_name)
            if install_config:
                nginx_sites_available_str = install_config.get("nginx_sites_available", "/etc/nginx/sites-available").strip()
                nginx_sites_available = Path(nginx_sites_available_str)
                nginx_sites_enabled_str = install_config.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
                nginx_sites_enabled = Path(nginx_sites_enabled_str)
            else:
                nginx_sites_available = Path("/etc/nginx/sites-available")
                nginx_sites_enabled = Path("/etc/nginx/sites-enabled")
        
        # Remove symlink from sites-enabled
        enabled_file = nginx_sites_enabled / domain
        if enabled_file.exists():
            enabled_file.unlink()
            log(f"Removed symlink: {enabled_file}")
        else:
            log(f"Symlink not found: {enabled_file}")
        
        # Remove config file from sites-available
        config_file = nginx_sites_available / domain
        if config_file.exists():
            config_file.unlink()
            log(f"Removed config: {config_file}")
        else:
            log(f"Config file not found: {config_file}")
        
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Failed to remove Nginx configuration for {domain}: {e}")
        trace_out()
        return False

def check_nginx_status(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Check current Nginx status."""
    trace_in()
    try:
        status_result = subprocess.run(['systemctl', 'is-active', 'nginx'], 
                                       capture_output=True, text=True)
        is_active = status_result.returncode == 0 and status_result.stdout.strip() == 'active'
        
        # Get enabled sites
        enabled_sites = []
        # Load nginx paths from config if project_name provided
        if project_name:
            from hh.deploy.users.install import _load_install_config
            install_config = _load_install_config(project_name)
            if install_config:
                nginx_sites_enabled_str = install_config.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
                sites_enabled_dir = Path(nginx_sites_enabled_str)
            else:
                sites_enabled_dir = Path('/etc/nginx/sites-enabled')
        else:
            sites_enabled_dir = Path('/etc/nginx/sites-enabled')
        if sites_enabled_dir.exists():
            for site_file in sites_enabled_dir.iterdir():
                if site_file.is_symlink() or not site_file.suffix:
                    enabled_sites.append(site_file.name)
        
        result = {
            'is_active': is_active,
            'enabled_sites': enabled_sites
        }
        log(f"Nginx status: active={is_active}, sites={len(enabled_sites)}")
        trace_out()
        return result
        
    except Exception as e:
        warn(f"Failed to check Nginx status: {e}")
        trace_out()
        return {'is_active': False, 'enabled_sites': []}

@register_action('remove')
@register_command('remove')
def remove() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Check if running in deployed Unix environment with privileges
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False

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
    
    log(f"Starting unified removal for project: {project_name}")
    
    # Load deployment configuration from install config
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        report_error("action", f"Install config not found: {cfg_path}")
        trace_out()
        return False
    
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        report_error("action", f"Missing [install] section in {cfg_path}")
        trace_out()
        return False
    
    sec = parser["install"]
    
    dest = Path("/srv") / project_name
    
    # Get all deployed sites from manifest
    deployed_domains = _manifest_get_all_sites(project_name)
    log(f"Found {len(deployed_domains)} deployed sites in manifest: {', '.join(deployed_domains) if deployed_domains else 'none'}")
    
    # Step 1: Remove NGINX configurations for all deployed sites
    nginx_removed = []
    nginx_failed = []
    if not is_error():
        for domain in deployed_domains:
            try:
                # Get nginx paths from config
                nginx_sites_available_str = sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip()
                nginx_sites_available = Path(nginx_sites_available_str)
                nginx_sites_enabled_str = sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
                nginx_sites_enabled = Path(nginx_sites_enabled_str)
                
                if remove_nginx_config(domain, project_name, nginx_sites_available, nginx_sites_enabled):
                    nginx_removed.append(domain)
                    log(f"Removed NGINX config for domain: {domain}")
                else:
                    nginx_failed.append(domain)
                    warn(f"Failed to remove NGINX config for domain: {domain}")
            except Exception as e:
                nginx_failed.append(domain)
                warn(f"Exception removing NGINX config for {domain}: {e}")
    
    # Test and reload NGINX if any configs were removed
    if nginx_removed and not is_error():
        try:
            test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
            if test_result.returncode != 0:
                warn(f"Nginx configuration test failed: {test_result.stderr}")
                report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
            else:
                log("Nginx configuration test passed")
                # Reload Nginx
                reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                if reload_result.returncode != 0:
                    # Try restart instead
                    restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                    if restart_result.returncode != 0:
                        warn(f"Failed to reload/restart Nginx: {restart_result.stderr}")
                        report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                    else:
                        log("Nginx restarted successfully")
                else:
                    log("Nginx reloaded successfully")
        except Exception as e:
            warn(f"Failed to test/reload Nginx: {e}")
            report_error("action", f"Failed to test/reload Nginx: {e}")

    # Clean up decoy server if no local deployments remain
    if nginx_removed and not is_error():
        try:
            # Get nginx paths from config
            nginx_sites_available_str = sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip()
            nginx_sites_available = Path(nginx_sites_available_str)
            nginx_sites_enabled_str = sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip()
            nginx_sites_enabled = Path(nginx_sites_enabled_str)

            # Check if any local deployments remain (files ending in .local)
            remaining_local_deployments = []
            if nginx_sites_available.exists():
                for site_file in nginx_sites_available.iterdir():
                    if site_file.is_file() and site_file.name.endswith('.local'):
                        remaining_local_deployments.append(site_file.name)

            # If no local deployments remain, remove the decoy
            if not remaining_local_deployments:
                decoy_available = nginx_sites_available / "decoy"
                decoy_enabled = nginx_sites_enabled / "decoy"
                decoy_removed = False

                # Remove decoy symlink
                if decoy_enabled.exists():
                    decoy_enabled.unlink()
                    log("Removed decoy symlink from sites-enabled")
                    decoy_removed = True

                # Remove decoy config
                if decoy_available.exists():
                    decoy_available.unlink()
                    log("Removed decoy config from sites-available")
                    decoy_removed = True

                if decoy_removed:
                    log("Cleaned up decoy server - no local deployments remain")
                    # Test and reload NGINX after removing decoy
                    try:
                        test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                        if test_result.returncode != 0:
                            warn(f"Nginx configuration test failed after decoy removal: {test_result.stderr}")
                        else:
                            reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                            if reload_result.returncode == 0:
                                log("Nginx reloaded successfully after decoy removal")
                            else:
                                restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                                if restart_result.returncode == 0:
                                    log("Nginx restarted successfully after decoy removal")
                                else:
                                    warn(f"Failed to reload/restart Nginx after decoy removal: {restart_result.stderr}")
                    except Exception as e:
                        warn(f"Failed to test/reload Nginx after decoy removal: {e}")
            else:
                log(f"Decoy preserved - {len(remaining_local_deployments)} local deployments still remain: {', '.join(remaining_local_deployments)}")

        except Exception as e:
            warn(f"Failed to clean up decoy server: {e}")

    # Step 2: Stop Flask daemons
    flask_stopped = False
    if not is_error():
        try:
            log("Stopping Flask daemons")
            flask_stop_info = run_flask_stop(project_name)
            flask_stopped = True
            log("Flask daemons stopped successfully")
        except Exception as e:
            warn(f"Failed to stop Flask daemons: {e}")
            report_error("backend", f"Failed to stop Flask daemons: {e}")
    
    # Step 3: Stop maintenance daemon
    maintenance_stopped = False
    if not is_error():
        try:
            log("Stopping maintenance daemon")
            maintenance_stop_info = run_maintenance_stop(project_name)
            maintenance_stopped = True
            log("Maintenance daemon stopped successfully")
        except Exception as e:
            warn(f"Failed to stop maintenance daemon: {e}")
            report_error("backend", f"Failed to stop maintenance daemon: {e}")
    
    # Step 4: Remove deployment files (everything except git folder and media directories)
    files_removed = False
    if not is_error():
        try:
            if dest.exists():
                log(f"Removing deployment files from: {dest}")
                # Remove all contents except git folder
                for item in dest.iterdir():
                    try:
                        # Skip git folder - it should remain
                        if item.name == 'git':
                            log(f"Preserving git folder: {item}")
                            continue
                        
                        if item.is_dir():
                            shutil.rmtree(item)
                            log(f"Removed directory: {item}")
                        else:
                            item.unlink()
                            log(f"Removed file: {item}")
                    except Exception as e:
                        warn(f"Failed to remove {item}: {e}")
                
                files_removed = True
                log(f"Removed all deployment files from: {dest}")
            else:
                log(f"Deployment directory does not exist: {dest}")
        except Exception as e:
            warn(f"Failed to remove deployment files: {e}")
            report_error("backend", f"Failed to remove deployment files: {e}")
    
    # Step 5: Clear manifest
    manifest_cleared = False
    if not is_error():
        try:
            _manifest_clear_all_sites(project_name)
            manifest_cleared = True
            log("Cleared all sites from manifest")
        except Exception as e:
            warn(f"Failed to clear manifest: {e}")
            report_error("backend", f"Failed to clear manifest: {e}")
    
    # Check NGINX status
    nginx_status = check_nginx_status(project_name)
    
    # Final result
    result = not is_error()
    if result:
        log("Unified removal completed successfully")
        result_data = {
            "project_name": project_name,
            "deployment_path": str(dest),
            "domains_removed": nginx_removed,
            "domains_failed": nginx_failed,
            "flask_stopped": flask_stopped,
            "maintenance_stopped": maintenance_stopped,
            "files_removed": files_removed,
            "manifest_cleared": manifest_cleared,
            "nginx_active": nginx_status.get('is_active', False),
            "nginx_enabled_sites": nginx_status.get('enabled_sites', []),
            "status": "removed"
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Unified removal encountered problems")
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return result

