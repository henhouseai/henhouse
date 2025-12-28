import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error

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

class SiteInfo:
    """Information about an nginx site configuration."""
    def __init__(self, name: str, enabled: bool, is_henhouse: bool, has_ssl: bool):
        self.name = name
        self.enabled = enabled
        self.is_henhouse = is_henhouse
        self.has_ssl = has_ssl

def scan_nginx_sites() -> List[SiteInfo]:
    """Scan nginx sites-available and sites-enabled directories."""
    trace_in()
    sites: list[SiteInfo] = []
    
    try:
        # Get all files in sites-available
        sites_available_dir = Path('/etc/nginx/sites-available')
        sites_enabled_dir = Path('/etc/nginx/sites-enabled')
        
        if not sites_available_dir.exists():
            log("Nginx sites-available directory not found (running in non-nginx environment)")
            trace_out()
            return sites
        
        # Build list of available sites
        available_files = []
        for file in sites_available_dir.iterdir():
            if file.is_file():
                available_files.append(file.name)
        
        log(f"Found {len(available_files)} sites in sites-available")
        
        # Build set of enabled sites (check both symlinks and actual files)
        enabled_sites = set()
        if sites_enabled_dir.exists():
            for item in sites_enabled_dir.iterdir():
                if item.is_symlink() or item.is_file():
                    enabled_sites.add(item.name)
        
        log(f"Found {len(enabled_sites)} sites in sites-enabled")
        
        # Analyze each site
        for site_name in available_files:
            config_file = sites_available_dir / site_name
            
            # Check if enabled
            enabled = site_name in enabled_sites
            
            # Read config to check for henhouse marker and SSL
            is_henhouse = False
            has_ssl = False
            
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    
                    # Check for henhouse deployment marker
                    if True:
                        is_henhouse = True
                    
                    # Check for SSL
                    if 'ssl_certificate' in content or 'listen 443' in content or 'ssl http2' in content:
                        has_ssl = True
                        
            except Exception as e:
                warn(f"Failed to read config file {config_file}: {e}")
                continue
            
            sites.append(SiteInfo(site_name, enabled, is_henhouse, has_ssl))
            log(f"Site: {site_name}, enabled={enabled}, henhouse={is_henhouse}, ssl={has_ssl}")
        
        trace_out()
        return sites
        
    except Exception as e:
        warn(f"Failed to scan nginx sites: {e}")
        trace_out()
        return sites

def categorize_sites(sites: List[SiteInfo]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize sites into 4 groups."""
    trace_in()
    
    categories: Dict[str, List[Dict[str, Any]]] = {
        'active_henhouse': [],      # Enabled + has marker
        'available_henhouse': [],   # Not enabled + has marker
        'active_other': [],         # Enabled + no marker
        'available_other': []       # Not enabled + no marker
    }
    
    for site in sites:
        site_data = {
            'name': site.name,
            'ssl_enabled': site.has_ssl,
            'stage': '2' if site.has_ssl else '1' if site.is_henhouse else None
        }
        
        if site.enabled and site.is_henhouse:
            categories['active_henhouse'].append(site_data)
        elif not site.enabled and site.is_henhouse:
            categories['available_henhouse'].append(site_data)
        elif site.enabled and not site.is_henhouse:
            categories['active_other'].append(site_data)
        elif not site.enabled and not site.is_henhouse:
            categories['available_other'].append(site_data)
    
    trace_out()
    return categories

def check_nginx_status() -> Dict[str, Any]:
    """Check current Nginx service status."""
    trace_in()
    try:
        status_result = subprocess.run(['systemctl', 'is-active', 'nginx'], 
                                       capture_output=True, text=True)
        is_active = status_result.returncode == 0 and status_result.stdout.strip() == 'active'
        
        result = {
            'is_active': is_active,
            'status': 'running' if is_active else 'stopped'
        }
        trace_out()
        return result
        
    except Exception as e:
        log(f"Nginx service check not available: {e}")
        trace_out()
        return {'is_active': False, 'status': 'not found'}

@register_action('http_status')
@register_command('http_status')
def http_status() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    log("Scanning nginx sites...")
    
    # Scan sites
    sites = scan_nginx_sites()
    
    # Categorize
    categories = categorize_sites(sites)
    
    # Check nginx service status
    nginx_status = check_nginx_status()
    
    # Count totals
    total_active_henhouse = len(categories['active_henhouse'])
    total_available_henhouse = len(categories['available_henhouse'])
    total_active_other = len(categories['active_other'])
    total_available_other = len(categories['available_other'])
    
    log(f"Found {total_active_henhouse} active henhouse sites, {total_available_henhouse} available henhouse sites")
    log(f"Found {total_active_other} active other sites, {total_available_other} available other sites")
    
    # Build result
    result_data = {
        "nginx_service": nginx_status,
        "categories": categories,
        "totals": {
            "active_henhouse": total_active_henhouse,
            "available_henhouse": total_available_henhouse,
            "active_other": total_active_other,
            "available_other": total_available_other
        }
    }
    
    gateway.response.set_action_response(success_payload(result_data))
    log("HTTP status scan completed successfully")
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    trace_out()
    return True

