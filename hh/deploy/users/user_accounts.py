import os
import subprocess
import pwd
from pathlib import Path
from typing import List, Dict, Any, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

from hh.deploy.users.user_account_suffixes import HENHOUSE_TIERS

def create_user_config_file(user: str, project_name: str, password: str) -> None:
    """Create project-specific config file for user."""
    trace_in()
    try:
        user_home = Path(f'/home/{user}')
        config_file = user_home / f'.{project_name}.cnf'
        
        config_content = f"[client]\nuser={user}\npassword={password}\nhost=localhost\ndatabase={project_name}\n"
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Set ownership and permissions
        os.chown(config_file, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
        os.chmod(config_file, 0o600)
        
        log(f"Created config file for {user}: {config_file}")
    except Exception as e:
        warn(f"Failed to create config file for {user}: {str(e)}")
    finally:
        trace_out()

def update_user_paths(project_name: str) -> None:
    """Update user shell paths to include their home directory."""
    trace_in()
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
                os.chown(profile_path, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
                log(f"Updated PATH for {user}")
        
        log("User paths updated successfully")
    except Exception as e:
        warn(f"Failed to update user paths: {str(e)}")
    finally:
        trace_out()

def create_user_gateway_scripts(project_name: str, hen_script_name: str = 'hen') -> None:
    """Create gateway scripts for all user tiers."""
    trace_in()
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
            os.chown(gateway_script, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
            os.chmod(gateway_script, 0o755)
            log(f"Created gateway script for {user}")
        
        log("Gateway scripts created successfully")
    except Exception as e:
        warn(f"Failed to create gateway scripts: {str(e)}")
    finally:
        trace_out()

def create_user_hen_scripts(project_name: str, hen_script_name: str = 'hen') -> None:
    """Create hen wrapper scripts for all user tiers."""
    trace_in()
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
            os.chown(hen_script, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
            os.chmod(hen_script, 0o755)
            log(f"Created hen script for {user}")
        
        log("hen scripts created successfully")
    except Exception as e:
        warn(f"Failed to create hen scripts: {str(e)}")
    finally:
        trace_out()

def create_root_gateway_script(project_name: str, project_path: Path, hen_script_name: str = 'hen') -> None:
    """Create gateway script for root user pointing to project codebase."""
    trace_in()
    try:
        log("Creating root gateway script")
        
        # Verify hen.py exists in project
        hen_script_path = project_path / 'hen.py'
        if not hen_script_path.exists():
            warn(f"hen.py not found at {hen_script_path} - skipping root gateway script setup")
            trace_out()
            return
        
        # Read hen.py content
        with open(hen_script_path, 'r') as f:
            hen_content = f.read()
        
        # Insert Python path setup after future imports (use project_path instead of /srv)
        lines = hen_content.split('\n')
        insert_idx = 0
        
        # Find the last future import
        for i, line in enumerate(lines):
            if line.strip().startswith('from __future__'):
                insert_idx = i + 1
        
        # Insert the Python path setup after future imports
        path_setup = f"import sys\nimport os\nsys.path.insert(0, '{str(project_path)}')\n"
        lines.insert(insert_idx, path_setup)
        
        # Create gateway-{hen_script_name} in /root (or gateway.py if default)
        root_home = Path('/root')
        if hen_script_name == 'hen':
            gateway_script = root_home / 'gateway.py'
        else:
            gateway_script = root_home / f'gateway-{hen_script_name}'
        
        with open(gateway_script, 'w') as f:
            f.write('\n'.join(lines))
        os.chown(gateway_script, 0, 0)  # root:root
        os.chmod(gateway_script, 0o755)
        log(f"Created root gateway script at {gateway_script}")
        
    except Exception as e:
        warn(f"Failed to create root gateway script: {str(e)}")
    finally:
        trace_out()

def detect_project_owner(project_path: Path) -> Optional[str]:
    """Detect the owner of the project folder."""
    trace_in()
    try:
        stat_info = project_path.stat()
        owner_uid = stat_info.st_uid
        owner_info = pwd.getpwuid(owner_uid)
        log(f"Detected project owner: {owner_info.pw_name}")
        trace_out()
        return owner_info.pw_name
    except Exception as e:
        warn(f"Failed to detect project owner: {str(e)}")
        trace_out()
        return None

def setup_user_convenience_scripts(project_name: str, project_path: Path, username: str, hen_script_name: str = 'hen', is_root: bool = False) -> None:
    """Set up convenience scripts (hen) for a user pointing to project codebase."""
    trace_in()
    try:
        log(f"Setting up convenience scripts for {'root' if is_root else username}")
        
        # Verify hen.py exists in project
        hen_script_path = project_path / 'hen.py'
        if not hen_script_path.exists():
            warn(f"hen.py not found at {hen_script_path} - skipping script setup")
            trace_out()
            return
        
        # Determine home directory and user info
        if is_root:
            user_home = Path('/root')
            user_uid = 0
            user_gid = 0
            user_display = "root"
            # Determine gateway script name
            if hen_script_name == 'hen':
                gateway_script_name = 'gateway.py'
            else:
                gateway_script_name = f'gateway-{hen_script_name}'
        else:
            user_home = Path(f'/home/{username}')
            try:
                user_info = pwd.getpwnam(username)
                user_uid = user_info.pw_uid
                user_gid = user_info.pw_gid
                user_display = username
                # Determine gateway script name
                if hen_script_name == 'hen':
                    gateway_script_name = 'gateway.py'
                else:
                    gateway_script_name = f'gateway-{hen_script_name}'
            except KeyError:
                warn(f"User {username} not found - skipping script setup")
                trace_out()
                return
        
        # Create hen script with custom name
        hen_script = user_home / hen_script_name
        local_project_path = Path.cwd()  # Current working directory where init was run
        hen_script_content = f'''#!/bin/bash
cd {local_project_path}
python3 {gateway_script_name} "$@"
'''
        
        with open(hen_script, 'w') as f:
            f.write(hen_script_content)
        os.chown(hen_script, user_uid, user_gid)
        os.chmod(hen_script, 0o755)
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
            os.chown(profile_path, user_uid, user_gid)
            log(f"Updated PATH for {user_display}")
        
        log(f"Convenience script setup complete for {user_display}")
        
    except Exception as e:
        warn(f"Failed to setup convenience scripts for {'root' if is_root else username}: {str(e)}")
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
        setup_user_convenience_scripts(project_name, project_path, project_owner, hen_script_name, is_root=False)
        
        # Also create gateway script for human user
        create_human_user_gateway_script(project_name, project_path, project_owner, hen_script_name)
        
    except Exception as e:
        warn(f"Failed to setup human user home directory: {str(e)}")
    finally:
        trace_out()

def create_human_user_gateway_script(project_name: str, project_path: Path, project_owner: str, hen_script_name: str = 'hen') -> None:
    """Create gateway script for human user (project owner) pointing to project codebase."""
    trace_in()
    try:
        log("Creating human user gateway script")
        
        # Verify hen.py exists in project
        hen_script_path = project_path / 'hen.py'
        if not hen_script_path.exists():
            warn(f"hen.py not found at {hen_script_path} - skipping human user gateway script setup")
            trace_out()
            return
        
        # Read hen.py content
        with open(hen_script_path, 'r') as f:
            hen_content = f.read()
        
        # Insert Python path setup after future imports (use project_path instead of /srv)
        lines = hen_content.split('\n')
        insert_idx = 0
        
        # Find the last future import
        for i, line in enumerate(lines):
            if line.strip().startswith('from __future__'):
                insert_idx = i + 1
        
        # Insert the Python path setup after future imports
        path_setup = f"import sys\nimport os\nsys.path.insert(0, '{str(project_path)}')\n"
        lines.insert(insert_idx, path_setup)
        
        # Create gateway-{hen_script_name} in human user home (or gateway.py if default)
        human_home = Path(f'/home/{project_owner}')
        if hen_script_name == 'hen':
            gateway_script = human_home / 'gateway.py'
        else:
            gateway_script = human_home / f'gateway-{hen_script_name}'
        
        user_info = pwd.getpwnam(project_owner)
        with open(gateway_script, 'w') as f:
            f.write('\n'.join(lines))
        os.chown(gateway_script, user_info.pw_uid, user_info.pw_gid)
        os.chmod(gateway_script, 0o755)
        log(f"Created human user gateway script at {gateway_script}")
        
    except Exception as e:
        warn(f"Failed to create human user gateway script: {str(e)}")
    finally:
        trace_out()

def setup_root_user_script(project_name: str, project_path: Path, hen_script_name: str = 'hen') -> None:
    """Set up root user convenience script for sudo operations with cache cleanup."""
    trace_in()
    try:
        log("Setting up root user convenience script")
        
        # Verify hen.py exists in project
        hen_script_path = project_path / 'hen.py'
        if not hen_script_path.exists():
            warn(f"hen.py not found at {hen_script_path} - skipping root script setup")
            trace_out()
            return
        
        # Determine gateway script name
        if hen_script_name == 'hen':
            gateway_script_name = 'gateway.py'
        else:
            gateway_script_name = f'gateway-{hen_script_name}'
        
        # Create root hen script with cache cleanup
        root_home = Path('/root')
        hen_script = root_home / hen_script_name
        local_project_path = Path.cwd()  # Current working directory where init was run
        hen_script_content = f'''#!/bin/bash
cd {local_project_path}
python3 {gateway_script_name} "$@"
find . -type d -name "__pycache__" -exec rm -rf {{}} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
'''
        
        with open(hen_script, 'w') as f:
            f.write(hen_script_content)
        os.chown(hen_script, 0, 0)  # root:root
        os.chmod(hen_script, 0o755)
        log(f"Created root hen script with cache cleanup at {hen_script}")
        
        # Update root's PATH to include /root
        profile_path = root_home / '.profile'
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profile_content = f.read()
        else:
            profile_content = ''
        
        path_update = f'export PATH="/root:$PATH"'
        if path_update not in profile_content:
            with open(profile_path, 'a') as f:
                f.write(f'\n{path_update}\n')
            os.chown(profile_path, 0, 0)
            log("Updated PATH for root")
        
        log("Root convenience script setup complete")
        
    except Exception as e:
        warn(f"Failed to setup root user convenience script: {str(e)}")
    finally:
        trace_out()