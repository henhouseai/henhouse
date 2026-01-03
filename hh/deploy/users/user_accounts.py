import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway

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

def create_user_config_file(
    user: str,
    project_name: str,
    password: str,
    db_user: Optional[str] = None,
    host: Optional[str] = None,
    ssl_ca: Optional[str] = None,
    cache_host: Optional[str] = None,
    cache_ssl_ca: Optional[str] = None,
    ssl_verify_mode: Optional[int] = None,
    mysql_tls_enabled: bool = False
) -> None:
    """Create project-specific config file for user."""
    trace_in()
    gateway = get_gateway()
    try:
        user_home = Path('/root') if user == "root" else Path(f'/home/{user}')
        config_file = user_home / f'.{project_name}.cnf'
        
        host_value = host or 'localhost'
        db_user_value = db_user or user
        config_lines = [
            "[client]",
            f"user={db_user_value}",
            f"password={password}",
            f"host={host_value}",
            f"database={project_name}",
        ]
        # Only write SSL/TLS config if TLS is enabled
        if mysql_tls_enabled:
            if ssl_ca:
                config_lines.append(f"ssl_ca={ssl_ca}")
            if cache_host:
                config_lines.append(f"cache_host={cache_host}")
            if cache_ssl_ca:
                config_lines.append(f"cache_ssl_ca={cache_ssl_ca}")
            if ssl_verify_mode is not None:
                config_lines.append(f"ssl_verify_mode={ssl_verify_mode}")
        else:
            # Still write cache_host even if TLS is disabled (for connection routing)
            if cache_host:
                config_lines.append(f"cache_host={cache_host}")
        config_content = "\n".join(config_lines) + "\n"
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Set ownership and permissions
        gateway.files.chown(str(config_file), user)
        gateway.files.chmod(str(config_file), 0o600)
        
        log(f"Created config file for {user}: {config_file}")
    except Exception as e:
        warn(f"Failed to create config file for {user}: {str(e)}")
    finally:
        trace_out()

def update_user_paths(project_name: str) -> None:
    """Update user shell paths to include their home directory."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Updating user paths")
        
        users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in users:
            user_home = Path(f'/home/{user}')
            profile_path = user_home / '.profile'
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    profile_content = f.read()
            else:
                profile_content = ''
            path_update = f'export PATH="/home/{user}:$PATH"'
            if path_update not in profile_content:
                with open(profile_path, 'a') as f:
                    f.write(f'\n{path_update}\n')
                gateway.files.chown(str(profile_path), user)
                log(f"Updated PATH for {user}")
        
        log("User paths updated successfully")
    except Exception as e:
        warn(f"Failed to update user paths: {str(e)}")
    finally:
        trace_out()

def create_user_gateway_scripts(project_name: str, entry_point_script_name: str = 'hen') -> None:
    """Create gateway scripts for all user tiers."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Creating user gateway scripts")
        
        # Get current hen.py content
        current_path = Path.cwd()
        hen_py_path = current_path / 'hen.py'
        with open(hen_py_path, 'r') as f:
            hen_content = f.read()
        
        users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in users:
            user_home = Path(f'/home/{user}')
            # Tier users always use gateway.py (not custom named)
            gateway_script = user_home / 'gateway.py'
            
            # Insert Python path setup after future imports
            lines = hen_content.split('\n')
            insert_idx = 0
            
            # Find the last future import
            for i, line in enumerate(lines):
                if line.strip().startswith('from __future__'):
                    insert_idx = i + 1
            
            # Insert the Python path setup after future imports
            path_setup = f"import sys\nimport os\nsys.path.insert(0, '/srv/{project_name}')\n"
            lines.insert(insert_idx, path_setup)
            
            with open(gateway_script, 'w') as f:
                f.write('\n'.join(lines))
            gateway.files.chown(str(gateway_script), user)
            gateway.files.chmod(str(gateway_script), 0o755)
            log(f"Created gateway script for {user}")
        
        log("Gateway scripts created successfully")
    except Exception as e:
        warn(f"Failed to create gateway scripts: {str(e)}")
    finally:
        trace_out()

def create_user_entry_point_scripts(project_name: str, entry_point_script_name: str = 'hen') -> None:
    """Create entry point wrapper scripts for all user tiers."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Creating user entry point scripts")
        
        users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in users:
            user_home = Path(f'/home/{user}')
            entry_point_script = user_home / entry_point_script_name
            entry_point_script_content = f'''#!/bin/bash
cd /home/{user}
python3 gateway.py "$@"
'''
            with open(entry_point_script, 'w') as f:
                f.write(entry_point_script_content)
            gateway.files.chown(str(entry_point_script), user)
            gateway.files.chmod(str(entry_point_script), 0o755)
            log(f"Created entry point script for {user}")
        
        log("Entry point scripts created successfully")
    except Exception as e:
        warn(f"Failed to create entry point scripts: {str(e)}")
    finally:
        trace_out()


def detect_project_owner(project_path: Path) -> Optional[str]:
    """Detect the owner of the project folder."""
    trace_in()
    gateway = get_gateway()
    try:
        stat_info = project_path.stat()
        owner_uid = stat_info.st_uid
        owner_info = gateway.os.get_user_by_uid(owner_uid) if gateway and gateway.os else None
        if owner_info:
            log(f"Detected project owner: {owner_info['name']}")
            trace_out()
            return owner_info['name']
        else:
            warn(f"Could not resolve owner for uid {owner_uid}")
            trace_out()
            return None
    except Exception as e:
        warn(f"Failed to detect project owner: {str(e)}")
        trace_out()
        return None

def setup_user_entry_points(project_name: str, project_path: Path, username: str, entry_point_script_name: str = 'hen', is_root: bool = False) -> None:
    """Set up entry point scripts for a user pointing to project codebase."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Setting up entry points for {'root' if is_root else username}")
        
        # Verify hen.py exists in project
        hen_py_path = project_path / 'hen.py'
        if not hen_py_path.exists():
            warn(f"hen.py not found at {hen_py_path} - skipping script setup")
            trace_out()
            return
        
        # Determine home directory and user info
        if is_root:
            user_home = Path('/root')
            user_display = "root"
            chown_user = "root"
        else:
            user_home = Path(f'/home/{username}')
            user_info = gateway.os.get_user_by_name(username) if gateway and gateway.os else None
            if not user_info:
                warn(f"User {username} not found - skipping script setup")
                trace_out()
                return
            user_display = username
            chown_user = username
        
        # Create entry point script with custom name, calling hen.py directly
        entry_point_script = user_home / entry_point_script_name
        local_project_path = Path.cwd()  # Current working directory where init was run
        entry_point_script_content = f'''#!/bin/bash
cd {local_project_path}
python3 hen.py "$@"
'''
        
        with open(entry_point_script, 'w') as f:
            f.write(entry_point_script_content)
        gateway.files.chown(str(entry_point_script), chown_user)
        gateway.files.chmod(str(entry_point_script), 0o755)
        log(f"Created entry point script for {user_display} pointing to {project_path}/hen.py")
        
        
        # Update user's PATH to include their home directory and /root
        profile_path = user_home / '.profile'
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profile_content = f.read()
        else:
            profile_content = ''
        
        path_update = f'export PATH="{user_home}:/root:$PATH"'
        if path_update not in profile_content:
            with open(profile_path, 'a') as f:
                f.write(f'\n{path_update}\n')
            gateway.files.chown(str(profile_path), chown_user)
            log(f"Updated PATH for {user_display}")
        
        log(f"Entry point setup complete for {user_display}")
        
    except Exception as e:
        warn(f"Failed to setup entry points for {'root' if is_root else username}: {str(e)}")
    finally:
        trace_out()

def setup_human_user_home(project_name: str, project_path: Path, entry_point_script_name: str = 'hen') -> None:
    """Set up human user (project owner) home directory with entry point script pointing to project codebase."""
    trace_in()
    try:
        # Detect project owner (human user)
        project_owner = detect_project_owner(project_path)
        if not project_owner:
            warn("No project owner detected - skipping human user home setup")
            trace_out()
            return
        
        log(f"Setting up human user home directory for {project_owner}")
        setup_user_entry_points(project_name, project_path, project_owner, entry_point_script_name, is_root=False)
        
    except Exception as e:
        warn(f"Failed to setup human user home directory: {str(e)}")
    finally:
        trace_out()

def setup_root_user_script(project_name: str, project_path: Path, entry_point_script_name: str = 'hen') -> None:
    """Set up root user entry point for sudo operations with cache cleanup."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Setting up root user entry point")
        
        # Verify hen.py exists in project
        hen_py_path = project_path / 'hen.py'
        if not hen_py_path.exists():
            warn(f"hen.py not found at {hen_py_path} - skipping root script setup")
            trace_out()
            return
        
        # Create root entry point script with cache cleanup, calling hen.py directly
        root_home = Path('/root')
        entry_point_script = root_home / entry_point_script_name
        local_project_path = Path.cwd()  # Current working directory where init was run
        entry_point_script_content = f'''#!/bin/bash
cd {local_project_path}
python3 hen.py "$@"
find . -type d -name "__pycache__" -exec rm -rf {{}} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
'''
        
        with open(entry_point_script, 'w') as f:
            f.write(entry_point_script_content)
        gateway.files.chown(str(entry_point_script), "root")
        gateway.files.chmod(str(entry_point_script), 0o755)
        log(f"Created root entry point script with cache cleanup at {entry_point_script}")
        
        # Update root's PATH to include /root (same as working install - only .profile)
        profile_path = root_home / '.profile'
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profile_content = f.read()
        else:
            profile_content = ''
        
        # Check if /root is already in PATH (check for the exact line that works)
        path_update = 'export PATH="/root:$PATH"'
        if path_update not in profile_content:
            # Also check if there's any PATH line with /root (more flexible)
            path_already_set = False
            if '/root' in profile_content:
                lines = profile_content.split('\n')
                for line in lines:
                    if 'PATH' in line and '/root' in line:
                        path_already_set = True
                        break
            
            if not path_already_set:
                with open(profile_path, 'a') as f:
                    f.write(f'\n{path_update}\n')
                gateway.files.chown(str(profile_path), "root")
                log("Updated PATH in .profile for root")
            else:
                log("PATH already includes /root in .profile for root")
        else:
            log("PATH already set correctly in .profile for root")
        
        # Update sudo's secure_path to include /root (so sudo books works)
        setup_sudo_secure_path()
        
        # Update sudo's secure_path to include /root (so sudo books works)
        setup_sudo_secure_path()
        
        log("Root entry point setup complete")
        
    except Exception as e:
        warn(f"Failed to setup root user entry point: {str(e)}")
    finally:
        trace_out()

def setup_sudo_secure_path() -> None:
    """Add /root to sudo's secure_path so sudo books works."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Setting up sudo secure_path to include /root")
        
        # Read current secure_path from /etc/sudoers
        sudoers_path = Path('/etc/sudoers')
        if not sudoers_path.exists():
            warn("sudoers file not found - skipping secure_path update")
            trace_out()
            return
        
        # Read current sudoers to get existing secure_path
        with open(sudoers_path, 'r') as f:
            sudoers_content = f.read()
        
        # Extract current secure_path
        current_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
        for line in sudoers_content.split('\n'):
            if 'secure_path=' in line:
                start = line.find('secure_path="') + len('secure_path="')
                end = line.find('"', start)
                if end > start:
                    current_path = line[start:end]
                    break
        
        # Check if /root is already in the path
        if '/root' in current_path:
            log("secure_path already includes /root")
            trace_out()
            return
        
        # Add /root to the path
        new_path = f'{current_path}:/root'
        
        # Create a file in /etc/sudoers.d/ (safer than modifying /etc/sudoers directly)
        sudoers_d_dir = Path('/etc/sudoers.d')
        sudoers_d_dir.mkdir(exist_ok=True)
        
        henhouse_sudoers = sudoers_d_dir / 'henhouse-secure-path'
        with open(henhouse_sudoers, 'w') as f:
            f.write(f'Defaults        secure_path="{new_path}"\n')
        
        gateway.files.chmod(str(henhouse_sudoers), 0o440)
        log(f"Created {henhouse_sudoers} to add /root to secure_path")
        
        # Validate with visudo
        result = subprocess.run(['visudo', '-c', '-f', str(henhouse_sudoers)], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            warn(f"visudo validation failed: {result.stderr}")
            henhouse_sudoers.unlink()  # Remove invalid file
            raise Exception("visudo validation failed")
        
        log("sudo secure_path updated successfully")
            
    except Exception as e:
        warn(f"Failed to update sudo secure_path: {str(e)}")
    finally:
        trace_out()