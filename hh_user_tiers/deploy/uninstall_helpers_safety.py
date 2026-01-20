"""
Uninstall safety validation helpers for tier user deletion.

Provides safety checks to ensure only project agent users are removed.
"""

from pathlib import Path
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init

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


def validate_user_for_deletion(user: str, project_name: str, gateway) -> bool:
    """Validate that a user is safe to delete (appears to be a project agent user)."""
    trace_in()
    try:
        # Check if user exists
        user_info = gateway.os.get_user_by_name(user) if gateway and gateway.os else None
        if not user_info:
            log(f"User {user} does not exist - safe to proceed")
            trace_out()
            return True

        # Safety check 1: User must be a system user (UID < 1000)
        if user_info["uid"] >= 1000:
            warn(f"User {user} has UID {user_info['uid']} (>= 1000) - SKIPPING")
            debug(f"User UID: {user_info['uid']}")
            debug(f"Expected UID < 1000: {user_info['uid'] < 1000}")
            debug(f"User info: {user_info}")
            trace_out()
            return False

        # Safety check 2: User must have /bin/bash as shell
        if user_info["shell"] != '/bin/bash':
            warn(f"User {user} has shell {user_info['shell']} (not /bin/bash) - SKIPPING")
            debug(f"User shell: {user_info['shell']}")
            debug(f"Expected shell: /bin/bash")
            debug(f"User info: {user_info}")
            trace_out()
            return False

        # Safety check 3: User must have expected home directory path
        expected_home = f'/home/{user}'
        if user_info["home"] != expected_home:
            warn(f"User {user} has unexpected home directory {user_info['home']} - SKIPPING")
            debug(f"Expected home: {expected_home}")
            debug(f"Actual home: {user_info['home']}")
            trace_out()
            return False

        # Safety check 4: User must be a project agent user (matches naming pattern)
        if not user.startswith(f"{project_name}_"):
            warn(f"User {user} does not match project naming pattern - SKIPPING")
            debug(f"Expected pattern: {project_name}_*")
            debug(f"Actual user: {user}")
            trace_out()
            return False

        log(f"User {user} passed all safety checks")
        trace_out()
        return True

    except Exception as e:
        warn(f"Error validating user {user}: {str(e)} - SKIPPING")
        trace_out()
        return False


def validate_user_directory_for_deletion(user: str, project_name: str, user_home: Path, gateway) -> bool:
    """Validate that a user directory is safe to delete (for leftover directories)."""
    trace_in()
    try:
        # Safety check 1: Directory must exist
        if not user_home.exists():
            warn(f"Directory {user_home} does not exist - SKIPPING")
            debug(f"Directory path: {user_home}")
            debug(f"Directory exists: {user_home.exists()}")
            debug(f"Directory is_dir: {user_home.is_dir()}")
            trace_out()
            return False

        # Safety check 2: Directory must be under /home/
        if not str(user_home).startswith('/home/'):
            warn(f"Directory {user_home} is not under /home/ - SKIPPING")
            debug(f"Directory path: {user_home}")
            debug(f"Directory starts with /home/: {str(user_home).startswith('/home/')}")
            trace_out()
            return False

        # Safety check 3: Directory must be owned by the expected user
        stat_info = user_home.stat()
            # Check if the expected user exists and get their UID
        user_info = gateway.os.get_user_by_name(user) if gateway and gateway.os else None
        if not user_info:
            # User doesn't exist, so we can't validate ownership
            warn(f"User {user} does not exist - cannot validate directory ownership")
            trace_out()
            return False
        expected_uid = user_info["uid"]

        if stat_info.st_uid != expected_uid:
            warn(f"Directory {user_home} is not owned by expected user - SKIPPING")
            debug(f"Expected UID: {expected_uid}, Actual UID: {stat_info.st_uid}")
            debug(f"Directory path: {user_home}")
            debug(f"Directory stat: {stat_info}")
            debug(f"Directory full mode: {oct(stat_info.st_mode)}")
            trace_out()
            return False

        # Safety check 4: Must have expected project agent structure
        required_files = {
            '.profile',           # Our custom .profile
            'gateway.py',         # User's gateway script
            'hen',                 # User's entry point wrapper script
            '.ssh',               # SSH directory
            f'.{project_name}.cnf' # Project-specific config
        }

        # Check if directory has the required files
        actual_files = set()
        for item in user_home.iterdir():
            if item.is_file():
                if item.name in required_files or not item.name.startswith('.'):
                    actual_files.add(item.name)
            elif item.is_dir() and item.name == '.ssh':
                actual_files.add('.ssh')
                # Check .ssh has expected contents
                ssh_files = {f.name for f in item.iterdir() if f.is_file()}
                if not ssh_files.issubset({'id_rsa', 'id_rsa.pub', 'authorized_keys'}):
                    warn(f"Directory {user_home} .ssh directory has unexpected files - SKIPPING")
                    debug(f"SSH files found: {sorted(ssh_files)}")
                    debug(f"Expected SSH files: id_rsa, id_rsa.pub, authorized_keys")
                    trace_out()
                    return False

        # Must have all required files and no extra non-hidden files
        missing_files = required_files - actual_files
        extra_files = actual_files - required_files
        extra_non_hidden_files = {f for f in extra_files if not f.startswith('.')}

        if missing_files or extra_non_hidden_files:
            warn(f"Directory {user_home} structure doesn't match expected agent user - SKIPPING")
            debug(f"Required files: {sorted(required_files)}")
            debug(f"Actual files: {sorted(actual_files)}")
            debug(f"Missing files: {sorted(missing_files)}")
            debug(f"Extra files: {sorted(extra_files)}")
            debug(f"Extra non-hidden files: {sorted(extra_non_hidden_files)}")
            debug(f"Directory path: {user_home}")
            debug(f"Directory contents: {[f.name for f in user_home.iterdir()]}")
            trace_out()
            return False

        log(f"Directory {user_home} passed all safety checks")
        trace_out()
        return True

    except Exception as e:
        warn(f"Error validating directory {user_home}: {str(e)} - SKIPPING")
        debug(f"Exception details: {str(e)}")
        trace_out()
        return False
