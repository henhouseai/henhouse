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
            result = {'tier': tier, 'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return result
        
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
        check_cmd = ['ps', 'aux']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        lines = check_result.stdout.split('\n')
        pids_to_kill = []
        for line in lines:
            if f'{project_name}_{tier}.py' in line and 'python' in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids_to_kill.append(pid)
                    except ValueError:
                        pass
        killed_any = False
        for pid in pids_to_kill:
            if gateway.os.kill_process(pid, force=False):
                log(f"Sent SIGTERM to PID {pid} (Flask {tier})")
                killed_any = True
        
        # Start Flask daemon as the appropriate Unix user
        # Flask app now handles its own logging internally, so no need for shell redirection
        cmd = f'sudo -u {user} bash -c "cd /srv/{project_name} && nohup python3 {app_path} < /dev/null &> /dev/null &"'
        debug(f"Running command: {cmd}")
        
        # Use Popen for background processes to avoid timeout issues
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        debug(f"Started process with PID: {process.pid}")
        
        # Give it a moment for the Flask daemon to start
        time.sleep(1)
        
        # Check if the Flask daemon is actually running (via ps)
        check_cmd = ['ps', 'aux']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        debug(f"Process check for '{project_name}_{tier}.py'")
        
        if f'{project_name}_{tier}.py' in check_result.stdout:
            result_status = 'restarted' if killed_any else 'started'
            result = {'tier': tier, 'status': result_status, 'port': port, 'user': user}
            log(f"Started Flask daemon for {tier} tier on port {port}")
        else:
            result = {'tier': tier, 'status': 'failed', 'error': 'Process not found running'}
            warn(f"Flask daemon for {tier} tier failed to start")
        
        trace_out()
        return result
        
    except Exception as e:
        result = {'tier': tier, 'status': 'error', 'error': str(e)}
        warn(f"Error starting Flask daemon for {tier}: {e}")
        trace_out()
        return result

def run_flask_start(project_name: str, start_port: int = 5001) -> Dict[str, Any]:
    trace_in()
    remove_logrotate(project_name)
    results = []
    for i, tier in enumerate(HENHOUSE_TIERS):
        port = start_port + i
        result = start_flask_daemon(project_name, tier, port)
        results.append(result)

    started_count = sum(1 for r in results if r.get('status') in {'started', 'restarted', 'already_running'})
    failed_count = sum(1 for r in results if r.get('status') in {'failed', 'error'})

    if started_count > 0:
        setup_logrotate(project_name)

    result_data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS),
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
    
    start_port = 5001  # Starting from 5001
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

