import subprocess
from typing import Dict, Any, List
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.error.error_store import report_error, is_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section, safe_str
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.deploy_utils import detect_project_context

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
        
        if gateway.files.file_exists(config_file):
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
            error_result = {'tier': tier, 'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        # Find process running app_{tier}.py using ProcessManager
        pm = gateway.os
        process_filter = f'{project_name}_{tier}.py'
        processes = pm.list_processes(process_filter)
        pids_to_kill = [p['pid'] for p in processes]
        
        if not pids_to_kill:
            not_running_result = {'tier': tier, 'status': 'not_running'}
            log(f"No Flask daemon found for {tier} tier")
            trace_out()
            return not_running_result
        
        # Kill the processes
        killed_pids = []
        for pid in pids_to_kill:
            if gateway.os.kill_process(pid, force=False):
                killed_pids.append(pid)
                log(f"Sent SIGTERM to PID {pid} (Flask {tier})")
        
        if killed_pids:
            return {'tier': tier, 'status': 'stopped', 'pids': killed_pids}
        else:
            return {'tier': tier, 'status': 'not_found'}
        
    except Exception as e:
        error_result = {'tier': tier, 'status': 'error', 'error': str(e)}
        warn(f"Error stopping Flask daemon for {tier}: {e}")
        trace_out()
        return error_result

def stop_media_server(project_name: str) -> Dict[str, Any]:
    """Stop media server Flask daemon."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            error_result = {'tier': 'media', 'status': 'error', 'error': 'Gateway or ProcessManager not available'}
            trace_out()
            return error_result
        
        # Find process running media server using ProcessManager
        pm = gateway.os
        process_filter = f'{project_name}_media.py'
        processes = pm.list_processes(process_filter)
        pids_to_kill = [p['pid'] for p in processes]
        
        if not pids_to_kill:
            not_running_result = {'tier': 'media', 'status': 'not_running'}
            log(f"No Media Server Flask daemon found")
            trace_out()
            return not_running_result
        
        # Kill the processes
        killed_pids = []
        for pid in pids_to_kill:
            if gateway.os.kill_process(pid, force=False):
                killed_pids.append(pid)
                log(f"Sent SIGTERM to PID {pid} (Media Server)")
        
        if killed_pids:
            return {'tier': 'media', 'status': 'stopped', 'pids': killed_pids}
        else:
            return {'tier': 'media', 'status': 'not_found'}
        
    except Exception as e:
        error_result = {'tier': 'media', 'status': 'error', 'error': str(e)}
        warn(f"Error stopping Media Server Flask daemon: {e}")
        trace_out()
        return error_result

def run_flask_stop(project_name: str) -> Dict[str, Any]:
    trace_in()
    results = []
    for tier in HENHOUSE_TIERS:
        result = stop_flask_daemon(project_name, tier)
        results.append(result)

    # Stop media server
    media_result = stop_media_server(project_name)
    results.append(media_result)

    stopped_count = sum(1 for r in results if r.get('status') == 'stopped')
    not_running_count = sum(1 for r in results if r.get('status') == 'not_running')
    failed_count = sum(1 for r in results if r.get('status') == 'error')

    if stopped_count > 0 or not_running_count == len(HENHOUSE_TIERS) + 1:  # +1 for media server
        remove_logrotate(project_name)

    data = {
        "project_name": project_name,
        "daemons": results,
        "summary": {
            "total": len(HENHOUSE_TIERS) + 1,  # +1 for media server
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


def _render_flask_daemons_stop(source_data, lines):
    """Helper function to render Flask daemon stop status table."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in _render_flask_daemons_stop")
        trace_out()
        return

    block = 'daemons'
    if not gateway.is_no(block):
        daemons_data = TableData()

        # Add header row to define column structure
        daemons_data.add_row('daemon_status_header', name='Tier')

        daemons = source_data.get('daemons', [])
        log(f"Rendering {len(daemons)} Flask daemons")

        for daemon in daemons:
            tier = daemon.get('tier', 'unknown')
            status = daemon.get('status', 'unknown')

            if status == 'stopped':
                daemons_data.add_row('daemon_stopped', name=safe_str(tier))
            elif status == 'not_running':
                daemons_data.add_row('daemon_not_running', name=safe_str(tier))
            elif status == 'error':
                daemons_data.add_row('daemon_error', name=safe_str(tier))

        lines.append(render_block(
            daemons_data,
            FieldConfig()
                .add_header('daemon_status_header')
                .add_simple(['daemon_stopped', 'daemon_not_running', 'daemon_error']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)

    trace_out()


@register_parser('flask_stop')
def render_flask_stop() -> bool:
    """Parser for flask_stop command."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    json_data = gateway.response.get_action_response()
    lines = []
    lines.append(render_header_block('l_flask_stop_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing Flask stop data")

    _render_flask_daemons_stop(source_data, lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

