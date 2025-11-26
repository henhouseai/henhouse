import subprocess
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.utils import detect_project_context

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

def get_flask_daemon_status(project_name: str, tier: str, port: int) -> Dict[str, Any]:
    """Get status of Flask daemon for specific tier."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.files:
            result = {'tier': tier, 'status': 'error', 'error': 'Gateway or FileSystem not available'}
            trace_out()
            return result
        
        app_path = f"/srv/{project_name}/{project_name}_{tier}.py"
        
        # Check if app file exists
        if not gateway.files.file_exists(app_path):
            result = {'tier': tier, 'status': 'not_deployed', 'error': f'App file not found: {app_path}'}
            trace_out()
            return result
        
        # Check if process is running
        cmd = ['ps', 'aux']
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the specific app
        lines = result.stdout.split('\n')
        pids = []
        
        for line in lines:
            if f'{project_name}_{tier}.py' in line and 'python' in line:
                parts = line.split()
                # PID is typically the 2nd column
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids.append(pid)
                    except ValueError:
                        pass
        
        if pids:
            result = {
                'tier': tier, 
                'status': 'running', 
                'pids': pids,
                'port': port
            }
            log(f"Flask daemon for {tier} tier is running (PIDs: {pids})")
        else:
            result = {'tier': tier, 'status': 'stopped', 'port': port}
            log(f"Flask daemon for {tier} tier is stopped")
        
        trace_out()
        return result
        
    except Exception as e:
        result = {'tier': tier, 'status': 'error', 'error': str(e)}
        warn(f"Error checking Flask daemon status for {tier}: {e}")
        trace_out()
        return result

@register_action('flask_status')
@register_command('flask_status')
def flask_status() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Detect project name
    project_name, _ = detect_project_context()
    log(f"Project: {project_name}")
    
    # Get status for Flask daemons for each tier
    results = []
    start_port = 5001  # Starting from 5001
    
    for i, tier in enumerate(HENHOUSE_TIERS):
        port = start_port + i
        result = get_flask_daemon_status(project_name, tier, port)
        results.append(result)
    
    # Build summary
    running_count = sum(1 for r in results if r.get('status') == 'running')
    stopped_count = sum(1 for r in results if r.get('status') == 'stopped')
    not_deployed_count = sum(1 for r in results if r.get('status') == 'not_deployed')
    error_count = sum(1 for r in results if r.get('status') == 'error')
    
    result_data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS),
            "running": running_count,
            "stopped": stopped_count,
            "not_deployed": not_deployed_count,
            "errors": error_count
        }
    }
    
    gateway.response.set_action_response(success_payload(result_data))
    
    log(f"Flask daemon status: {running_count} running, {stopped_count} stopped")
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True

