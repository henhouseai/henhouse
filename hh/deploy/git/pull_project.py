import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from datetime import datetime

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

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            else:
                print(f"Error: {result.stdout}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"Exception running command: {cmd}")
        print(f"Exception: {e}")
        return False

def run_git(repo_path: str, args: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run git command and return result."""
    import shlex
    cmd = ["git", "-C", repo_path] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        raise RuntimeError(f"git command failed ({proc.returncode}):\n$ {' '.join(shlex.quote(a) for a in cmd)}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return proc.returncode, out, err

@register_action('pull_project')
@register_command('pull_project')
def pull_project() -> bool:
    """Pull latest project with hard reset to project head."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Detect project context
    from hh.deploy.utils import detect_project_context
    project_name, repo_root = detect_project_context()
    log(f"Using project: {project_name} at {repo_root}")
    
    # Check current branch
    branch_result = subprocess.run(
        "git branch --show-current",
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(repo_root)
    )
    
    if branch_result.returncode != 0:
        warn("Unable to check current branch")
        report_error("backend", "Unable to check current branch")
        trace_out()
        return False
    
    current_branch = branch_result.stdout.strip()
    log(f"Current branch: {current_branch}")
    
    # Switch to project branch if not already there
    branch_switched = False
    if current_branch != project_name:
        log(f"Switching to {project_name} branch...")
        if not run_command(f"git checkout {project_name}", cwd=str(repo_root)):
            report_error("backend", f"Failed to switch to {project_name} branch")
            trace_out()
            return False
        branch_switched = True
    
    # Fetch latest from remote
    log("Fetching latest from remote...")
    if not run_command("git fetch origin", cwd=str(repo_root)):
        report_error("backend", "Failed to fetch from origin")
        trace_out()
        return False
    
    # Hard reset to origin/project (clean state)
    log(f"Hard resetting to origin/{project_name}...")
    if not run_command(f"git reset --hard origin/{project_name}", cwd=str(repo_root)):
        report_error("backend", f"Failed to reset to origin/{project_name}")
        trace_out()
        return False
    
    # Get git information about the current commit
    git_info = {}
    try:
        # Get short hash (7 characters)
        hash_result = subprocess.run(
            "git rev-parse --short HEAD",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(repo_root)
        )
        if hash_result.returncode == 0:
            git_info['short_hash'] = hash_result.stdout.strip()
        
        # Get commit message (first line only)
        message_result = subprocess.run(
            "git log -1 --pretty=format:%s",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(repo_root)
        )
        if message_result.returncode == 0:
            git_info['commit_message'] = message_result.stdout.strip()
        
        # Get time ago
        time_result = subprocess.run(
            "git log -1 --pretty=format:%ar",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(repo_root)
        )
        if time_result.returncode == 0:
            git_info['time_ago'] = time_result.stdout.strip()
            
        log(f"Git info: {git_info}")
    except Exception as e:
        warn(f"Failed to get git information: {e}")
        git_info = {'short_hash': 'Unknown', 'commit_message': 'Unknown', 'time_ago': 'Unknown'}
    
    # Clear all caches using registry system
    cache_cleared = []
    try:
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        log("Clearing all caches using registry system...")
        cleanup_results = clean_all_caches()
        aggregated = cleanup_results.get('_aggregated', {})
        
        # Collect cleared cache files for reporting
        cache_cleared.extend(aggregated.get('cache_files_list', []))
        cache_cleared.extend(aggregated.get('pycache_dirs_list', []))
        cache_cleared.extend(aggregated.get('pyc_files_list', []))
        
        total_cleared = (aggregated.get('cache_files', 0) + 
                        aggregated.get('pycache_dirs', 0) + 
                        aggregated.get('pyc_files', 0))
        log(f"Cache cleanup complete: {total_cleared} items cleared")
    except Exception as e:
        warn(f"Failed to clear caches using registry: {e}")
        report_error("backend", f"Cache cleanup failed: {e}")
    
    # Final result
    result = not is_error()
    if result:
        log(f"Successfully pulled latest {project_name}")
        result_data = {
            "project_name": project_name,
            "project_path": str(repo_root),
            "current_branch": current_branch,
            "branch_switched": branch_switched,
            "short_hash": git_info.get('short_hash', 'Unknown'),
            "commit_message": git_info.get('commit_message', 'Unknown'),
            "time_ago": git_info.get('time_ago', 'Unknown'),
            "cache_cleared": cache_cleared,
            "status": "pulled"
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log(f"{project_name} pull encountered problems")
    
    trace_out()
    return result
