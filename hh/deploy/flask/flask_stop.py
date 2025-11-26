import subprocess
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
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

def remove_logrotate(project_name: str) -> None:
    """Remove logrotate config for Flask daemon logs."""
    trace_in()
    
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            warn("Gateway or ProcessManager not available")
            trace_out()
            return
        
        config_file = f'/etc/logrotate.d/{project_name}-flask'
        
        if gateway.files and gateway.files.file_exists(config_file):
            gateway.files.schedule_delete(config_file)
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
        gateway = get_gateway()
        if not gateway or not gateway.os:
            result = {'tier': tier, 'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return result
        
        # Find process running app_{tier}.py
        cmd = ['ps', 'aux']
        ps_result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Look for the specific app
        lines = ps_result.stdout.split('\n')
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
            if gateway.os.kill_process(pid, force=False):
                killed_pids.append(pid)
                log(f"Sent SIGTERM to PID {pid} (Flask {tier})")
        
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

def run_flask_stop(project_name: str) -> Dict[str, Any]:
    trace_in()
    results = []
    for tier in HENHOUSE_TIERS:
        result = stop_flask_daemon(project_name, tier)
        results.append(result)

    stopped_count = sum(1 for r in results if r.get('status') == 'stopped')
    not_running_count = sum(1 for r in results if r.get('status') == 'not_running')
    failed_count = sum(1 for r in results if r.get('status') == 'error')

    if stopped_count > 0 or not_running_count == len(HENHOUSE_TIERS):
        remove_logrotate(project_name)

    data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS),
            "stopped": stopped_count,
            "not_running": not_running_count,
            "failed": failed_count,
        },
    }
    trace_out()
    return data


@register_action('flask_stop')
@register_command('flask_stop')
def flask_stop() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Check if running in deployed Unix environment
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False
    
    project_name, _ = detect_project_context()
    log(f"Project: {project_name}")
    
    result_data = run_flask_stop(project_name)
    gateway.response.set_action_response(success_payload(result_data))
    
    if result_data['summary']['failed'] > 0:
        warn(f"Flask daemon stop completed with {result_data['summary']['failed']} failures")
        report_error("action", f"Flask daemon stop: {result_data['summary']['failed']} failed")
    
    log(
        f"Flask daemon stop completed: "
        f"{result_data['summary']['stopped']} stopped, "
        f"{result_data['summary']['not_running']} not running"
    )
    
    # Clear registry cache
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return True

