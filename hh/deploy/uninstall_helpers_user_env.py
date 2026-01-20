"""
Uninstall helpers for user environment cleanup.

Handles cleanup of entry point scripts and .profile modifications.
"""

from pathlib import Path
from typing import Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


def cleanup_user_entry_points(project_name: str, project_path: Path, username: str, entry_point_script_name: Optional[str] = None, is_root: bool = False) -> None:
    """Clean up entry points (hen) for a user."""
    trace_in()
    try:
        log(f"Cleaning up entry points for {'root' if is_root else username}")

        # Default to standard name if not provided
        if not entry_point_script_name:
            entry_point_script_name = 'hen'

        # Determine home directory
        if is_root:
            user_home = Path('/root')
            user_display = "root"
            path_line = 'export PATH="/root:$PATH"\n'
        else:
            user_home = Path(f'/home/{username}')
            user_display = username
            path_line = f'export PATH="/home/{username}:$PATH"\n'

        if not user_home.exists():
            log(f"{user_display} home directory does not exist - skipping cleanup")
            trace_out()
            return

        # Remove entry point script if it exists and looks like our script (calls hen.py directly)
        entry_point_script = user_home / entry_point_script_name
        if entry_point_script.exists():
            try:
                with open(entry_point_script, 'r') as f:
                    content = f.read()

                # Check if it calls hen.py directly (root and human user behavior)
                if 'python3 hen.py' in content:
                    entry_point_script.unlink()
                    log(f"Removed entry point script ({entry_point_script_name}) from {user_display}'s home directory")
                else:
                    log(f"entry point script ({entry_point_script_name}) in {user_display}'s home directory doesn't match our pattern - skipping")
            except Exception as e:
                warn(f"Failed to remove entry point script from {user_display}'s home: {str(e)}")


        # Remove PATH modification from .profile
        profile_path = user_home / '.profile'
        if profile_path.exists():
            try:
                with open(profile_path, 'r') as f:
                    lines = f.readlines()

                # Remove both the user home and /root PATH lines we added
                original_lines = lines.copy()
                user_path_line = f'export PATH="{user_home}:/root:$PATH"\n'
                lines = [line for line in lines if line != user_path_line]

                # Only write back if we actually removed something
                if len(lines) != len(original_lines):
                    with open(profile_path, 'w') as f:
                        f.writelines(lines)
                    log(f"Removed PATH modification from {user_display}'s .profile")
                else:
                    log(f"No PATH modification found in {user_display}'s .profile")
            except Exception as e:
                warn(f"Failed to clean up .profile for {user_display}: {str(e)}")

        log(f"Entry points cleanup complete for {user_display}")

    except Exception as e:
        warn(f"Failed to cleanup entry points for {'root' if is_root else username}: {str(e)}")
    finally:
        trace_out()
