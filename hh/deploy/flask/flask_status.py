from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.users.install import _install_config_path

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
            error_result = {'tier': tier, 'status': 'error', 'error': 'Gateway or FileSystem not available'}
            trace_out()
            return error_result
        
        app_path = f"/srv/{project_name}/{project_name}_{tier}.py"
        
        # Check if app file exists
        if not gateway.files.file_exists(app_path):
            not_deployed_result = {'tier': tier, 'status': 'not_deployed', 'error': f'App file not found: {app_path}'}
            trace_out()
            return not_deployed_result
        
        # Check if process is running using ProcessManager
        pm = gateway.os
        process_filter = f'{project_name}_{tier}.py'
        processes = pm.list_processes(process_filter)
        pids = [p['pid'] for p in processes]
        
        if pids:
            # Get full username using ProcessManager helper (ps aux truncates long usernames)
            users = []
            for pid in pids:
                username = pm.get_process_username(pid)
                if username:
                    users.append(username)
            
            # Get unique users (should be same for all PIDs of same daemon)
            unique_users = list(set(users)) if users else ['unknown']
            user = unique_users[0] if unique_users else 'unknown'
            status_result: dict[str, str | int | list[int]] = {
                'tier': tier, 
                'status': 'running', 
                'pids': pids,
                'port': port,
                'user': user
            }
            log(f"Flask daemon for {tier} tier is running (PIDs: {pids}, User: {user}, Port: {port})")
            trace_out()
            return status_result
        else:
            stopped_result: dict[str, str | int | None] = {'tier': tier, 'status': 'stopped', 'port': port, 'user': None}
            log(f"Flask daemon for {tier} tier is stopped")
            trace_out()
            return stopped_result
        
    except Exception as e:
        error_result = {'tier': tier, 'status': 'error', 'error': str(e)}
        warn(f"Error checking Flask daemon status for {tier}: {e}")
        trace_out()
        return error_result

def get_media_server_status(project_name: str, port: int) -> Dict[str, Any]:
    """Get status of media server Flask daemon."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.files:
            error_result = {'tier': 'media', 'status': 'error', 'error': 'Gateway or FileSystem not available'}
            trace_out()
            return error_result
        
        app_path = f"/srv/{project_name}/{project_name}_media.py"
        
        # Check if app file exists
        if not gateway.files.file_exists(app_path):
            not_deployed_result = {'tier': 'media', 'status': 'not_deployed', 'error': f'Media server app file not found: {app_path}'}
            trace_out()
            return not_deployed_result
        
        # Check if process is running using ProcessManager
        pm = gateway.os
        process_filter = f'{project_name}_media.py'
        processes = pm.list_processes(process_filter)
        pids = [p['pid'] for p in processes]
        
        if pids:
            # Get full username using ProcessManager helper (ps aux truncates long usernames)
            users = []
            for pid in pids:
                username = pm.get_process_username(pid)
                if username:
                    users.append(username)
            
            # Get unique users (should be same for all PIDs of same daemon)
            unique_users = list(set(users)) if users else ['unknown']
            user = unique_users[0] if unique_users else 'unknown'
            status_result: dict[str, str | int | list[int]] = {
                'tier': 'media', 
                'status': 'running', 
                'pids': pids,
                'port': port,
                'user': user
            }
            log(f"Media Server Flask daemon is running (PIDs: {pids}, User: {user}, Port: {port})")
            trace_out()
            return status_result
        else:
            stopped_result: dict[str, str | int | None] = {'tier': 'media', 'status': 'stopped', 'port': port, 'user': None}
            log(f"Media Server Flask daemon is stopped")
            trace_out()
            return stopped_result
        
    except Exception as e:
        error_result = {'tier': 'media', 'status': 'error', 'error': str(e)}
        warn(f"Error checking Media Server Flask daemon status: {e}")
        trace_out()
        return error_result

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
    
    # Load flask_start_port from install config
    start_port = 5001  # Default
    try:
        import configparser
        cfg_path = _install_config_path(project_name)
        if cfg_path.exists():
            parser = configparser.ConfigParser()
            parser.read(cfg_path)
            if "install" in parser:
                port_str = parser["install"].get("flask_start_port", "5001").strip()
                try:
                    start_port = int(port_str)
                except ValueError:
                    warn(f"Invalid flask_start_port in config, using default 5001")
    except Exception as e:
        warn(f"Failed to load flask_start_port from config: {e}, using default 5001")
    
    # Get status for Flask daemons for each tier
    results = []
    
    for i, tier in enumerate(HENHOUSE_TIERS):
        port = start_port + i
        result = get_flask_daemon_status(project_name, tier, port)
        results.append(result)
    
    # Get status for media server
    media_port = start_port + len(HENHOUSE_TIERS)
    media_result = get_media_server_status(project_name, media_port)
    results.append(media_result)
    
    # Build summary
    running_count = sum(1 for r in results if r.get('status') == 'running')
    stopped_count = sum(1 for r in results if r.get('status') == 'stopped')
    not_deployed_count = sum(1 for r in results if r.get('status') == 'not_deployed')
    error_count = sum(1 for r in results if r.get('status') == 'error')
    
    result_data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS) + 1,  # +1 for media server
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

