"""Cross-platform process management utilities."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)

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


from hh.gateway.system.dependency import check_dependency, register_dependency, require

_PSUTIL_DEPENDENCY = "psutil"
_PWD_DEPENDENCY = "pwd"
_GRP_DEPENDENCY = "grp"


@register_dependency(_PSUTIL_DEPENDENCY)
def _import_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        return None


@register_dependency(_PWD_DEPENDENCY)
def _import_pwd():
    try:
        import pwd
        return pwd
    except ImportError:
        return None


@register_dependency(_GRP_DEPENDENCY)
def _import_grp():
    try:
        import grp
        return grp
    except ImportError:
        return None


psutil = _import_psutil()
pwd = _import_pwd()
grp = _import_grp()


class ProcessManager:
    """Cross-platform process management with graceful error handling."""

    def __init__(self):
        trace_in()
        self._os_type = self._detect_os()
        log(f"ProcessManager initialized (OS: {self._os_type})")
        trace_out()

    def _detect_os(self) -> str:
        """Detect the operating system. Returns 'windows', 'macos', 'linux', or 'unknown'."""
        import platform
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        else:
            return 'unknown'

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self._os_type == 'windows'

    @property
    def is_unix(self) -> bool:
        """Check if running on a Unix-like system (Linux, macOS)."""
        return self._os_type in ('linux', 'macos')

    def is_deployed(self, project_name: str) -> bool:
        """Check if the project is deployed (has /srv/{project} directory)."""
        trace_in()
        deployed_path = Path(f"/srv/{project_name}")
        result = deployed_path.exists() and deployed_path.is_dir()
        log(f"Deployment check for {project_name}: {result}")
        trace_out()
        return result

    def is_privileged(self) -> bool:
        """Check if running with elevated privileges (root on Unix, always False on Windows)."""
        trace_in()
        if self.is_windows:
            # On Windows, we don't use privilege escalation for maintenance
            trace_out()
            return False
        try:
            result = os.geteuid() == 0
            log(f"Privilege check: {result}")
            trace_out()
            return result
        except AttributeError:
            # geteuid doesn't exist on Windows
            trace_out()
            return False

    def require_privileged(self) -> bool:
        """Require elevated privileges. Reports appropriate error if not met.
        
        - On Windows: reports deployment error (requires Unix)
        - On Unix as non-root: reports action error (needs sudo)
        - On Unix as root: returns True
        """
        trace_in()
        from hh.gateway.error.error_store import report_error
        
        if self.is_windows:
            report_error("deployment", "This command requires a deployed Unix environment (cannot run on Windows)")
            trace_out()
            return False
        
        if not self.is_privileged():
            report_error("action", "This command requires sudo privileges to switch Unix users")
            trace_out()
            return False
        
        trace_out()
        return True

    def list_processes(self, name_filter: str) -> List[Dict[str, Any]]:
        """List processes matching a name filter.
        
        Returns list of dicts with 'pid', 'name', 'cmdline' keys.
        """
        trace_in()
        processes = []

        if not require("psutil"):
            trace_out()
            return processes

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    info = proc.info
                    cmdline = info.get('cmdline') or []
                    cmdline_str = ' '.join(cmdline) if cmdline else ''
                    
                    # Check if filter matches name or cmdline
                    if name_filter in (info.get('name') or '') or name_filter in cmdline_str:
                        processes.append({
                            'pid': info['pid'],
                            'name': info.get('name', ''),
                            'cmdline': cmdline_str,
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            log(f"Found {len(processes)} processes matching '{name_filter}'")
        except Exception as e:
            warn(f"Error listing processes: {e}")

        trace_out()
        return processes

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a process by PID. Returns True if successful."""
        trace_in()
        if not require("psutil"):
            trace_out()
            return False
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            log(f"Killed process {pid} (force={force})")
            trace_out()
            return True
        except Exception as e:
            warn(f"Failed to kill process {pid}: {e}")
            trace_out()
            return False

    def start_background_process(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        log_file: Optional[str] = None,
        user: Optional[str] = None,
    ) -> Optional[int]:
        """Start a background process. Returns PID if successful, None otherwise.
        
        Args:
            cmd: Command and arguments to run
            cwd: Working directory
            log_file: File to redirect stdout/stderr to
            user: Unix user to run as (only works if privileged, ignored on Windows)
        """
        trace_in()
        try:
            # Build the actual command
            actual_cmd = cmd.copy()
            
            # Handle user switching on Unix (deployed mode)
            debug(f"User switching check: user={user}, is_unix={self.is_unix}, is_privileged={self.is_privileged()}")
            if user and self.is_unix and self.is_privileged():
                # Wrap command with sudo -u
                cmd_str = ' '.join(actual_cmd)
                if log_file:
                    cmd_str = f'{cmd_str} >> {log_file} 2>&1'
                actual_cmd = ['sudo', '-u', user, 'bash', '-c', f'cd {cwd or "."} && nohup {cmd_str} &']
                
                debug(f"User switching command: {' '.join(actual_cmd)}")
                
                # Use array form for proper argument handling
                process = subprocess.Popen(
                    actual_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=cwd,
                )
                log(f"Started background process as user {user}")
                trace_out()
                return process.pid
            else:
                debug(f"Not switching users - running as current user")
            
            # Standard background process (Windows or non-privileged Unix)
            # Let smart processes handle their own logging - no stdout redirect
            stdout_target = subprocess.DEVNULL
            stderr_target = subprocess.DEVNULL
            
            # Platform-specific background process creation
            if self.is_windows:
                # Windows: use CREATE_NO_WINDOW and DETACHED_PROCESS
                CREATE_NO_WINDOW = 0x08000000
                DETACHED_PROCESS = 0x00000008
                process = subprocess.Popen(
                    actual_cmd,
                    stdout=stdout_target,
                    stderr=stderr_target,
                    cwd=cwd,
                    creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                )
            else:
                # Unix: use start_new_session for daemon-like behavior
                process = subprocess.Popen(
                    actual_cmd,
                    stdout=stdout_target,
                    stderr=stderr_target,
                    cwd=cwd,
                    start_new_session=True,
                )
            
            log(f"Started background process with PID {process.pid}")
            trace_out()
            return process.pid
            
        except Exception as e:
            warn(f"Failed to start background process: {e}")
            trace_out()
            return None

    def get_cwd(self) -> str:
        """Get current working directory (cross-platform)."""
        return os.getcwd()

    def find_project_root(self) -> Optional[Path]:
        """Find the project root by looking for hh/ directory."""
        current = Path(__file__).resolve()
        while current != current.parent:
            if (current / "hh").is_dir():
                return current
            current = current.parent
        return None

    def get_project_name(self) -> Optional[str]:
        """Get project name from project root directory."""
        root = self.find_project_root()
        return root.name if root else None

    # --- Unix user info methods (pwd wrappers) ---

    def get_user_by_name(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user info by username. Returns dict with uid, gid, home, shell, or None.
        
        Only works on Unix systems where pwd module is available.
        """
        trace_in()
        if not require("pwd"):
            trace_out()
            return None
        try:
            info = pwd.getpwnam(username)
            result = {
                "uid": info.pw_uid,
                "gid": info.pw_gid,
                "name": info.pw_name,
                "home": info.pw_dir,
                "shell": info.pw_shell,
            }
            log(f"Got user info for {username}: uid={info.pw_uid}")
            trace_out()
            return result
        except KeyError:
            warn(f"User not found: {username}")
            trace_out()
            return None
        except Exception as e:
            warn(f"Error getting user info for {username}: {e}")
            trace_out()
            return None

    def get_user_by_uid(self, uid: int) -> Optional[Dict[str, Any]]:
        """Get user info by UID. Returns dict with uid, gid, name, home, shell, or None.
        
        Only works on Unix systems where pwd module is available.
        """
        trace_in()
        if not require("pwd"):
            trace_out()
            return None
        try:
            info = pwd.getpwuid(uid)
            result = {
                "uid": info.pw_uid,
                "gid": info.pw_gid,
                "name": info.pw_name,
                "home": info.pw_dir,
                "shell": info.pw_shell,
            }
            log(f"Got user info for uid {uid}: name={info.pw_name}")
            trace_out()
            return result
        except KeyError:
            warn(f"UID not found: {uid}")
            trace_out()
            return None
        except Exception as e:
            warn(f"Error getting user info for uid {uid}: {e}")
            trace_out()
            return None

    # --- Unix group info methods (grp wrappers) ---

    def get_group_by_name(self, groupname: str) -> Optional[Dict[str, Any]]:
        """Get group info by name. Returns dict with gid, name, members, or None.
        
        Only works on Unix systems where grp module is available.
        """
        trace_in()
        if not require("grp"):
            trace_out()
            return None
        try:
            info = grp.getgrnam(groupname)
            result = {
                "gid": info.gr_gid,
                "name": info.gr_name,
                "members": list(info.gr_mem),
            }
            log(f"Got group info for {groupname}: gid={info.gr_gid}")
            trace_out()
            return result
        except KeyError:
            warn(f"Group not found: {groupname}")
            trace_out()
            return None
        except Exception as e:
            warn(f"Error getting group info for {groupname}: {e}")
            trace_out()
            return None

    def group_exists(self, groupname: str) -> bool:
        """Check if a group exists. Returns False on Windows or if group doesn't exist."""
        trace_in()
        available, _ = check_dependency("grp")
        if not available:
            # On Windows, just return False - no grp module (no error)
            trace_out()
            return False
        try:
            grp.getgrnam(groupname)
            log(f"Group exists: {groupname}")
            trace_out()
            return True
        except KeyError:
            log(f"Group does not exist: {groupname}")
            trace_out()
            return False

    def get_group_by_gid(self, gid: int) -> Optional[Dict[str, Any]]:
        """Get group info by GID. Returns dict with gid, name, members, or None.
        
        Only works on Unix systems where grp module is available.
        """
        trace_in()
        if not require("grp"):
            trace_out()
            return None
        try:
            info = grp.getgrgid(gid)
            result = {
                "gid": info.gr_gid,
                "name": info.gr_name,
                "members": list(info.gr_mem),
            }
            log(f"Got group info for gid {gid}: name={info.gr_name}")
            trace_out()
            return result
        except KeyError:
            warn(f"GID not found: {gid}")
            trace_out()
            return None
        except Exception as e:
            warn(f"Error getting group info for gid {gid}: {e}")
            trace_out()
            return None
        except Exception as e:
            warn(f"Error checking group existence for {groupname}: {e}")
            trace_out()
            return False

    def user_exists(self, username: str) -> bool:
        """Check if a user exists. Returns False on Windows or if user doesn't exist."""
        trace_in()
        available, _ = check_dependency("pwd")
        if not available:
            # On Windows, just return False - no pwd module (no error)
            trace_out()
            return False
        try:
            pwd.getpwnam(username)
            log(f"User exists: {username}")
            trace_out()
            return True
        except KeyError:
            log(f"User does not exist: {username}")
            trace_out()
            return False
        except Exception as e:
            warn(f"Error checking user existence for {username}: {e}")
            trace_out()
            return False


