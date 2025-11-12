import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.users.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.flask.flask_stop import remove_logrotate
import pwd
import signal

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

def detect_project_name() -> str:
    """Detect project name from current directory."""
    trace_in()
    try:
        cwd = os.getcwd()
        if cwd.startswith('/srv/'):
            parts = cwd.split('/')
            if len(parts) >= 3:
                project_name = parts[2]
                trace_out()
                return project_name
        else:
            current_path = Path(cwd)
            while current_path != current_path.parent:
                hh_dir = current_path / 'hh'
                if hh_dir.exists() and hh_dir.is_dir():
                    project_name = current_path.name
                    trace_out()
                    return project_name
                current_path = current_path.parent
        trace_out()
        return "henhouse"
    except Exception as e:
        warn(f"Failed to detect project name: {e}")
        trace_out()
        return "henhouse"

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
        user = f"{project_name}_{tier}"
        app_path = f"/srv/{project_name}/{project_name}_{tier}.py"
        
        # Check if app file exists
        if not os.path.exists(app_path):
            result = {'tier': tier, 'status': 'not_found', 'error': f'App file not found: {app_path}'}
            trace_out()
            return result
        
        # Check if user exists
        try:
            pwd.getpwnam(user)
        except KeyError:
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
            try:
                os.kill(pid, signal.SIGTERM)
                log(f"Sent SIGTERM to PID {pid} (Flask {tier})")
                killed_any = True
            except ProcessLookupError:
                log(f"Process {pid} already terminated")
            except Exception as e:
                warn(f"Failed to kill PID {pid}: {e}")
        
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

@register_action('flask_start')
@register_command('flask_start')
def flask_start() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Check if running with sudo privileges
    if os.geteuid() != 0:
        warn("This command requires sudo privileges to switch Unix users")
        report_error("action", "This command requires sudo privileges to switch Unix users")
        trace_out()
        return False
    
    # Detect project name
    project_name = detect_project_name()
    log(f"Project: {project_name}")
    
    # Remove any existing logrotate config and restart the service before starting
    remove_logrotate(project_name)
    
    # Start Flask daemons for each tier
    results = []
    start_port = 5001  # Starting from 5001
    
    for i, tier in enumerate(HENHOUSE_TIERS):
        port = start_port + i
        result = start_flask_daemon(project_name, tier, port)
        results.append(result)
    
    # Build response
    started_count = sum(1 for r in results if r.get('status') == 'started' or r.get('status') == 'already_running')
    failed_count = sum(1 for r in results if r.get('status') == 'failed' or r.get('status') == 'error')
    
    # Configure logrotate for Flask logs
    if started_count > 0:
        setup_logrotate(project_name)
    
    result_data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS),
            "started": started_count,
            "failed": failed_count
        }
    }
    
    gateway.response.set_action_response(success_payload(result_data))
    
    if failed_count > 0:
        warn(f"Flask daemon startup completed with {failed_count} failures")
        report_error("action", f"Flask daemon startup: {failed_count} failed")
    
    log(f"Flask daemon startup completed: {started_count}/{len(HENHOUSE_TIERS)} started")
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True

