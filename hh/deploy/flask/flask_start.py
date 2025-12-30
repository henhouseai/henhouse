import subprocess
import time
from typing import Dict, Any
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.flask.flask_stop import remove_logrotate
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

def setup_logrotate(project_name: str) -> None:
    """Configure logrotate for Flask daemon logs."""
    trace_in()
    
    try:
        logs_dir = f'/srv/{project_name}/logs'
        config_content = f'''# Flask daemon logs for {project_name}
{logs_dir}/*.log {{
    hourly
    rotate 24
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    copytruncate
}}
'''
        
        config_file = f'/etc/logrotate.d/{project_name}-flask'
        
        # Write logrotate config
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Restart logrotate service to apply configuration
        subprocess.run(['systemctl', 'restart', 'logrotate.service'], check=False)
        
        log(f"Configured logrotate for {project_name} Flask logs")
    except Exception as e:
        warn(f"Failed to configure logrotate: {e}")
    finally:
        trace_out()

def start_flask_daemon(project_name: str, tier: str, port: int) -> Dict[str, Any]:
    """Start Flask daemon for specific tier."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'tier': tier, 'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        user = f"{project_name}_{tier}"
        app_path = f"/srv/{project_name}/{project_name}_{tier}.py"
        
        # Check if app file exists
        if not gateway.files or not gateway.files.file_exists(app_path):
            result = {'tier': tier, 'status': 'not_found', 'error': f'App file not found: {app_path}'}
            trace_out()
            return result
        
        # Check if user exists
        if not gateway.os.user_exists(user):
            result = {'tier': tier, 'status': 'user_not_found', 'error': f'User not found: {user}'}
            trace_out()
            return result
        
        # Stop any existing processes for this tier (acts like restart)
        pm = gateway.os
        process_filter = f'{project_name}_{tier}.py'
        existing_processes = pm.list_processes(process_filter)
        pids_to_kill = [p['pid'] for p in existing_processes]
        killed_any = False
        for pid in pids_to_kill:
            if pm.kill_process(pid, force=False):
                log(f"Sent SIGTERM to PID {pid} (Flask {tier})")
                killed_any = True
        
        # Start Flask daemon as the appropriate Unix user using ProcessManager
        # Flask app now handles its own logging internally, so no need for shell redirection
        cmd = ['python3', app_path]
        cwd = f'/srv/{project_name}'
        debug(f"Starting Flask daemon: {cmd} in {cwd} as {user}")
        
        # Use ProcessManager to start background process
        started_pid = pm.start_background_process(cmd, cwd=cwd, log_file=None, user=user)
        
        if started_pid:
            debug(f"Started process with PID: {started_pid}")
        else:
            start_result: dict[str, str | int] = {'tier': tier, 'status': 'failed', 'error': 'Failed to start process'}
            warn(f"Flask daemon for {tier} tier failed to start")
            trace_out()
            return start_result
        
        # Give it a moment for the Flask daemon to start
        time.sleep(1)
        
        # Check if the Flask daemon is actually running using ProcessManager
        check_processes = pm.list_processes(process_filter)
        debug(f"Process check for '{process_filter}': found {len(check_processes)} processes")
        
        if check_processes:
            result_status = 'restarted' if killed_any else 'started'
            start_result = {'tier': tier, 'status': result_status, 'port': port, 'user': user}
            log(f"Started Flask daemon for {tier} tier on port {port}")
        else:
            start_result = {'tier': tier, 'status': 'failed', 'error': 'Process not found running'}
            warn(f"Flask daemon for {tier} tier failed to start")
        
        trace_out()
        return start_result
        
    except Exception as e:
        error_result = {'tier': tier, 'status': 'error', 'error': str(e)}
        warn(f"Error starting Flask daemon for {tier}: {e}")
        trace_out()
        return error_result

def start_media_server(project_name: str, port: int) -> Dict[str, Any]:
    """Start media server Flask daemon (runs as admin user)."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'tier': 'media', 'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        # Media server runs as admin user
        user = f"{project_name}_admin"
        app_path = f"/srv/{project_name}/{project_name}_media.py"
        
        # Check if app file exists
        if not gateway.files or not gateway.files.file_exists(app_path):
            result = {'tier': 'media', 'status': 'not_found', 'error': f'Media server app file not found: {app_path}'}
            trace_out()
            return result
        
        # Check if user exists
        if not gateway.os.user_exists(user):
            result = {'tier': 'media', 'status': 'user_not_found', 'error': f'User not found: {user}'}
            trace_out()
            return result
        
        # Stop any existing media server processes
        pm = gateway.os
        process_filter = f'{project_name}_media.py'
        existing_processes = pm.list_processes(process_filter)
        pids_to_kill = [p['pid'] for p in existing_processes]
        killed_any = False
        for pid in pids_to_kill:
            if pm.kill_process(pid, force=False):
                log(f"Sent SIGTERM to PID {pid} (Media Server)")
                killed_any = True
        
        # Start media server daemon as admin user using ProcessManager
        cmd = ['python3', app_path]
        cwd = f'/srv/{project_name}'
        debug(f"Starting Media Server: {cmd} in {cwd} as {user}")
        
        # Use ProcessManager to start background process
        started_pid = pm.start_background_process(cmd, cwd=cwd, log_file=None, user=user)
        
        if started_pid:
            debug(f"Started process with PID: {started_pid}")
        else:
            start_result: dict[str, str | int] = {'tier': 'media', 'status': 'failed', 'error': 'Failed to start process'}
            warn(f"Media Server Flask daemon failed to start")
            trace_out()
            return start_result
        
        time.sleep(1)
        
        # Check if the media server is actually running using ProcessManager
        check_processes = pm.list_processes(process_filter)
        debug(f"Process check for '{process_filter}': found {len(check_processes)} processes")
        
        if check_processes:
            result_status = 'restarted' if killed_any else 'started'
            start_result = {'tier': 'media', 'status': result_status, 'port': port, 'user': user}
            log(f"Started Media Server Flask daemon on port {port}")
        else:
            start_result = {'tier': 'media', 'status': 'failed', 'error': 'Process not found running'}
            warn(f"Media Server Flask daemon failed to start")
        
        trace_out()
        return start_result
        
    except Exception as e:
        error_result = {'tier': 'media', 'status': 'error', 'error': str(e)}
        warn(f"Error starting Media Server Flask daemon: {e}")
        trace_out()
        return error_result

def run_flask_start(project_name: str, start_port: int = 5001) -> Dict[str, Any]:
    trace_in()
    remove_logrotate(project_name)
    results = []
    for i, tier in enumerate(HENHOUSE_TIERS):
        port = start_port + i
        result = start_flask_daemon(project_name, tier, port)
        results.append(result)

    # Start media server on port after all tier apps
    media_port = start_port + len(HENHOUSE_TIERS)
    media_result = start_media_server(project_name, media_port)
    results.append(media_result)

    started_count = sum(1 for r in results if r.get('status') in {'started', 'restarted', 'already_running'})
    failed_count = sum(1 for r in results if r.get('status') in {'failed', 'error'})

    if started_count > 0:
        setup_logrotate(project_name)

    result_data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS) + 1,  # +1 for media server
            "started": started_count,
            "failed": failed_count,
        },
    }
    trace_out()
    return result_data


@register_action('flask_start')
@register_command('flask_start')
def flask_start() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Check if running with sudo privileges (also checks for Unix deployment)
    if not gateway.os or not gateway.os.require_privileged():
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
    
    result_data = run_flask_start(project_name, start_port)
    
    gateway.response.set_action_response(success_payload(result_data))
    
    if result_data['summary']['failed'] > 0:
        warn(f"Flask daemon startup completed with {result_data['summary']['failed']} failures")
        report_error("action", f"Flask daemon startup: {result_data['summary']['failed']} failed")
    
    log(
        f"Flask daemon startup completed: "
        f"{result_data['summary']['started']}/{len(HENHOUSE_TIERS)} started"
    )
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True

