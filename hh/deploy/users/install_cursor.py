import subprocess
from pathlib import Path
from typing import List, Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload

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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

@register_action('install_cursor')
@register_command('install_cursor')
def install_cursor() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Check if running in deployed Unix environment with privileges
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False

    try:
        # Detect project context
        project_name, project_path = detect_project_context()
        log(f"Installing Cursor for {project_name} users")
        
        # Install Cursor for all project users
        cursor_results = install_cursor_for_users(project_name)
        
        # Prepare response data
        result_data = {
            "project_name": project_name,
            "project_path": str(project_path),
            "users_processed": len(cursor_results),
            "users_successful": len([r for r in cursor_results if r.get("status") == "success"]),
            "users_failed": len([r for r in cursor_results if r.get("status") == "failed"]),
            "cursor_results": cursor_results,
            "status": "completed"
        }
        
        gateway.response.set_action_response(success_payload(result_data))
        log("Cursor installation completed")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Cursor installation failed: {str(e)}")
        report_error("backend", f"Cursor installation failed: {str(e)}")
        trace_out()
        return False

# Import detect_project_context from utils
from hh.deploy.utils import detect_project_context
from hh.gateway.error.error_store import report_error

def install_cursor_for_users(project_name: str) -> List[Dict[str, Any]]:
    """Install Cursor in each user's home directory."""
    trace_in()
    gateway = get_gateway()
    results = []
    
    try:
        log("Installing Cursor for all users")
        
        users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in users:
            result = {
                "username": user,
                "status": "failed",
                "error": None,
                "home_directory": f"/home/{user}"
            }
            
            try:
                user_home = Path(f'/home/{user}')
                log(f"Installing Cursor for user: {user}")
                
                # Run the Cursor installation command as the user
                install_result = subprocess.run([
                    'su', '-', user, '-c', 'curl https://cursor.com/install -fsS | bash'
                ], capture_output=True, text=True, timeout=300)
                
                debug(f"Cursor install result for {user}: returncode={install_result.returncode}")
                debug(f"Cursor install stdout for {user}: {install_result.stdout}")
                debug(f"Cursor install stderr for {user}: {install_result.stderr}")
                
                if install_result.returncode == 0:
                    log(f"Cursor installed successfully for {user}")
                    
                    # Check what was actually created in the user's home directory
                    debug(f"Contents of {user_home} after Cursor install:")
                    for item in user_home.iterdir():
                        if item.name.startswith('.'):
                            debug(f"  Hidden item: {item.name}")
                    
                    # Fix ownership of .local directory and all contents
                    local_dir = user_home / '.local'
                    if local_dir.exists():
                        gateway.files.chown(str(local_dir), user, recursive=True)
                        log(f"Fixed ownership of .local directory for {user}")
                    else:
                        debug(f"No .local directory found for {user}")
                    
                    # Also check for any other Cursor-related directories that might have been created
                    cursor_dirs = ['.cursor', '.config/cursor', '.cache/cursor']
                    for cursor_dir in cursor_dirs:
                        cursor_path = user_home / cursor_dir
                        if cursor_path.exists():
                            gateway.files.chown(str(cursor_path), user, recursive=True)
                            log(f"Fixed ownership of {cursor_dir} for {user}")
                        else:
                            debug(f"No {cursor_dir} directory found for {user}")
                    
                    result["status"] = "success"
                else:
                    error_msg = install_result.stderr or "Unknown error"
                    warn(f"Failed to install Cursor for {user}: {error_msg}")
                    result["error"] = error_msg
                    
            except subprocess.TimeoutExpired:
                error_msg = "Installation timed out"
                warn(f"Cursor installation timed out for {user}")
                result["error"] = error_msg
            except Exception as e:
                error_msg = str(e)
                warn(f"Error installing Cursor for {user}: {error_msg}")
                result["error"] = error_msg
            
            results.append(result)
        
        log(f"Cursor installation process completed: {len([r for r in results if r['status'] == 'success'])} successful, {len([r for r in results if r['status'] == 'failed'])} failed")
        
    except Exception as e:
        warn(f"Failed to install Cursor for users: {str(e)}")
    finally:
        trace_out()
    
    return results
