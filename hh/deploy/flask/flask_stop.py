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
from hh.deploy.users.user_account_suffixes import HENHOUSE_TIERS
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

def remove_logrotate(project_name: str) -> None:
    """Remove logrotate config for Flask daemon logs."""
    trace_in()
    
    try:
        config_file = f'/etc/logrotate.d/{project_name}-flask'
        
        if os.path.exists(config_file):
            os.remove(config_file)
            subprocess.run(['systemctl', 'restart', 'logrotate.service'], check=False)
            log(f"Removed logrotate config for {project_name}")
        else:
            log(f"Logrotate config not found for {project_name}")
    except Exception as e:
        warn(f"Failed to remove logrotate config: {e}")
    finally:
        trace_out()

def stop_flask_daemon(project_name: str, tier: str) -> Dict[str, Any]:
    """Stop Flask daemon for specific tier."""
    trace_in()
    try:
        # Find process running app_{tier}.py
        cmd = ['ps', 'aux']
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the specific app
        lines = result.stdout.split('\n')
        pids_to_kill = []
        
        for line in lines:
            if f'{project_name}_{tier}.py' in line and 'python' in line:
                parts = line.split()
                # PID is typically the 2nd column
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids_to_kill.append(pid)
                    except ValueError:
                        pass
        
        if not pids_to_kill:
            result = {'tier': tier, 'status': 'not_running'}
            log(f"No Flask daemon found for {tier} tier")
            trace_out()
            return result
        
        # Kill the processes
        killed_pids = []
        for pid in pids_to_kill:
            try:
                os.kill(pid, signal.SIGTERM)
                killed_pids.append(pid)
                log(f"Sent SIGTERM to PID {pid} (Flask {tier})")
            except ProcessLookupError:
                log(f"Process {pid} already terminated")
            except Exception as e:
                warn(f"Failed to kill PID {pid}: {e}")
        
        if killed_pids:
            result = {'tier': tier, 'status': 'stopped', 'pids': killed_pids}
        else:
            result = {'tier': tier, 'status': 'not_found'}
        
        trace_out()
        return result
        
    except Exception as e:
        result = {'tier': tier, 'status': 'error', 'error': str(e)}
        warn(f"Error stopping Flask daemon for {tier}: {e}")
        trace_out()
        return result

@register_action('flask_stop')
@register_command('flask_stop')
def flask_stop() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Detect project name
    project_name = detect_project_name()
    log(f"Project: {project_name}")
    
    # Stop Flask daemons for each tier
    results = []
    
    for tier in HENHOUSE_TIERS:
        result = stop_flask_daemon(project_name, tier)
        results.append(result)
    
    # Build response
    stopped_count = sum(1 for r in results if r.get('status') == 'stopped')
    not_running_count = sum(1 for r in results if r.get('status') == 'not_running')
    failed_count = sum(1 for r in results if r.get('status') == 'error')
    
    # Remove logrotate config for Flask logs
    if stopped_count > 0 or not_running_count == len(HENHOUSE_TIERS):
        remove_logrotate(project_name)
    
    result_data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS),
            "stopped": stopped_count,
            "not_running": not_running_count,
            "failed": failed_count
        }
    }
    
    gateway.response.set_action_response(success_payload(result_data))
    
    if failed_count > 0:
        warn(f"Flask daemon stop completed with {failed_count} failures")
        report_error("action", f"Flask daemon stop: {failed_count} failed")
    
    log(f"Flask daemon stop completed: {stopped_count} stopped, {not_running_count} not running")
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True

