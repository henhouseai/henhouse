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
    cache_ssl_ca: Optional[str] = None
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
        if ssl_ca:
            config_lines.append(f"ssl_ca={ssl_ca}")
        if cache_host:
            config_lines.append(f"cache_host={cache_host}")
        if cache_ssl_ca:
            config_lines.append(f"cache_ssl_ca={cache_ssl_ca}")
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

def create_user_gateway_scripts(project_name: str, hen_script_name: str = 'hen') -> None:
    """Create gateway scripts for all user tiers."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Creating user gateway scripts")
        
        # Get current hen.py content
        current_path = Path.cwd()
        hen_script_path = current_path / 'hen.py'
        with open(hen_script_path, 'r') as f:
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

def create_user_hen_scripts(project_name: str, hen_script_name: str = 'hen') -> None:
    """Create hen wrapper scripts for all user tiers."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Creating user hen scripts")
        
        users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in users:
            user_home = Path(f'/home/{user}')
            hen_script = user_home / hen_script_name
            hen_script_content = f'''#!/bin/bash
cd /home/{user}
python3 gateway.py "$@"
'''
            with open(hen_script, 'w') as f:
                f.write(hen_script_content)
            gateway.files.chown(str(hen_script), user)
            gateway.files.chmod(str(hen_script), 0o755)
            log(f"Created hen script for {user}")
        
        log("hen scripts created successfully")
    except Exception as e:
        warn(f"Failed to create hen scripts: {str(e)}")
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

def setup_user_entry_points(project_name: str, project_path: Path, username: str, hen_script_name: str = 'hen', is_root: bool = False) -> None:
    """Set up entry points (hen) for a user pointing to project codebase."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Setting up entry points for {'root' if is_root else username}")
        
        # Verify hen.py exists in project
        hen_script_path = project_path / 'hen.py'
        if not hen_script_path.exists():
            warn(f"hen.py not found at {hen_script_path} - skipping script setup")
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
        
        # Create hen script with custom name, calling hen.py directly
        hen_script = user_home / hen_script_name
        local_project_path = Path.cwd()  # Current working directory where init was run
        hen_script_content = f'''#!/bin/bash
cd {local_project_path}
python3 hen.py "$@"
'''
        
        with open(hen_script, 'w') as f:
            f.write(hen_script_content)
        gateway.files.chown(str(hen_script), chown_user)
        gateway.files.chmod(str(hen_script), 0o755)
        log(f"Created hen script for {user_display} pointing to {project_path}/hen.py")
        
        
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

def setup_human_user_home(project_name: str, project_path: Path, hen_script_name: str = 'hen') -> None:
    """Set up human user (project owner) home directory with hen script pointing to project codebase."""
    trace_in()
    try:
        # Detect project owner (human user)
        project_owner = detect_project_owner(project_path)
        if not project_owner:
            warn("No project owner detected - skipping human user home setup")
            trace_out()
            return
        
        log(f"Setting up human user home directory for {project_owner}")
        setup_user_entry_points(project_name, project_path, project_owner, hen_script_name, is_root=False)
        
    except Exception as e:
        warn(f"Failed to setup human user home directory: {str(e)}")
    finally:
        trace_out()

def setup_root_user_script(project_name: str, project_path: Path, hen_script_name: str = 'hen') -> None:
    """Set up root user entry point for sudo operations with cache cleanup."""
    trace_in()
    gateway = get_gateway()
    try:
        log("Setting up root user entry point")
        
        # Verify hen.py exists in project
        hen_script_path = project_path / 'hen.py'
        if not hen_script_path.exists():
            warn(f"hen.py not found at {hen_script_path} - skipping root script setup")
            trace_out()
            return
        
        # Create root hen script with cache cleanup, calling hen.py directly
        root_home = Path('/root')
        hen_script = root_home / hen_script_name
        local_project_path = Path.cwd()  # Current working directory where init was run
        hen_script_content = f'''#!/bin/bash
cd {local_project_path}
python3 hen.py "$@"
find . -type d -name "__pycache__" -exec rm -rf {{}} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
'''
        
        with open(hen_script, 'w') as f:
            f.write(hen_script_content)
        gateway.files.chown(str(hen_script), "root")
        gateway.files.chmod(str(hen_script), 0o755)
        log(f"Created root hen script with cache cleanup at {hen_script}")
        
        # Update root's PATH to include /root (both .profile and .bashrc for compatibility)
        path_update = 'export PATH="/root:$PATH"'
        
        for config_file in ['.profile', '.bashrc']:
            config_path = root_home / config_file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_content = f.read()
            else:
                config_content = ''
            
            # Check if /root is already in PATH (more flexible check)
            path_already_set = False
            if '/root' in config_content:
                # Check if it's in a PATH export line
                lines = config_content.split('\n')
                for line in lines:
                    if 'PATH' in line and '/root' in line:
                        path_already_set = True
                        break
            
            if not path_already_set:
                with open(config_path, 'a') as f:
                    f.write(f'\n{path_update}\n')
                gateway.files.chown(str(config_path), "root")
                log(f"Updated PATH in {config_file} for root")
            else:
                log(f"PATH already includes /root in {config_file} for root")
        
        log("Root entry point setup complete")
        
    except Exception as e:
        warn(f"Failed to setup root user entry point: {str(e)}")
    finally:
        trace_out()