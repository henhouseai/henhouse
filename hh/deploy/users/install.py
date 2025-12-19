import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
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
from hh.deploy.users.access import auto_scan_user_keys, generate_ssh_keys, add_user_key
from hh.deploy.users.user_accounts import create_user_config_file, update_user_paths, create_user_gateway_scripts, create_user_hen_scripts, setup_user_convenience_scripts, setup_human_user_home, setup_root_user_script, detect_project_owner
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.error.error_store import report_error


@register_action('install')
@register_command('install')
def install() -> bool:
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
        # Support multiple naming conventions: password1/pwd1/p1, password2/pwd2/p2, etc.
        password1 = gateway.get_arg('password1') or gateway.get_arg('pwd1') or gateway.get_arg('p1')
        password2 = gateway.get_arg('password2') or gateway.get_arg('pwd2') or gateway.get_arg('p2')
        password3 = gateway.get_arg('password3') or gateway.get_arg('pwd3') or gateway.get_arg('p3')
        password4 = gateway.get_arg('password4') or gateway.get_arg('pwd4') or gateway.get_arg('p4')
        user_key = gateway.get_arg('user_key')
        remove_users = gateway.get_arg('remove_user')
        hen_script_name = gateway.get_arg('hen') or 'hen'  # Default to 'hen' if not specified
        clean_install = gateway.get_arg('clean')

        project_name, project_path = detect_project_context()
        log(f"Starting {project_name} system initialization")
        
        if not password1 or not password2 or not password3 or not password4:
            warn("All four passwords are required for install (use password1/pwd1/p1, password2/pwd2/p2, password3/pwd3/p3, password4/pwd4/p4)")
            report_error("action", "All four passwords are required for install (use password1/pwd1/p1, password2/pwd2/p2, password3/pwd3/p3, password4/pwd4/p4)")
            trace_out()
            return False
        
        passwords = [password1, password2, password3, password4]
        
        # Check for existing setup before proceeding
        existing_setup = check_existing_setup(project_name)
        if existing_setup:
            warn(f"Existing setup detected for project {project_name}")
            report_error("action", f"Existing setup detected. Please run uninstall first. Found: {', '.join(existing_setup)}")
            trace_out()
            return False
        
        # Check for script conflicts before proceeding
        project_owner = detect_project_owner(project_path)
        script_conflicts = check_script_conflicts(project_owner, hen_script_name)
        if script_conflicts:
            warn(f"Script conflicts detected: {', '.join(script_conflicts)}")
            report_error("action", f"Script conflicts detected. Please specify -hen flag with a custom script name. Found conflicts: {', '.join(script_conflicts)}")
            trace_out()
            return False
        
        # Parse additional users to remove
        additional_users = []
        if remove_users:
            additional_users = [user.strip() for user in remove_users.split(',') if user.strip()]
            log(f"Additional users to remove: {additional_users}")
        
        log(f"Project: {project_name} at {project_path}")
        log(f"Using script name: {hen_script_name}")

        # Optional clean flag to remove existing git metadata before reinstall
        if clean_install:
            git_dir = project_path / '.git'
            if git_dir.exists():
                shutil.rmtree(git_dir)
                log("Removed existing .git directory for clean install")
        
        # Auto-scan project owner's keys
        if not project_owner:
            project_owner = detect_project_owner(project_path)
        auto_scanned_keys = []
        if project_owner:
            auto_scanned_keys = auto_scan_user_keys(project_owner)
            log(f"Auto-scanned {len(auto_scanned_keys)} keys from {project_owner}")
        
        # Create core groups FIRST (before users so they can be added to them)
        setup_core_groups(project_name)
        
        # Create fresh users (needs deploy group to exist)
        user_data = create_fresh_users(passwords, user_key, project_name, auto_scanned_keys)
        
        # Create/update .htpasswd files for admin and root tiers
        setup_htpasswd_files(project_name, passwords)
        
        # Set up rest of project groups (after users created so their groups exist)
        setup_project_group(project_name, project_path)
        
        # Set up git repository
        setup_git_repository(project_name, project_path)
        
        
        # Create user gateway scripts (with custom naming for root/human user)
        create_user_gateway_scripts(project_name, hen_script_name)
        
        # Create user hen scripts (with custom naming)
        create_user_hen_scripts(project_name, hen_script_name)
        
        # Update user paths
        update_user_paths(project_name)
        
        # Set up human user (project owner) home directory
        setup_human_user_home(project_name, project_path, hen_script_name)
        
        # Set up root user convenience script
        setup_root_user_script(project_name, project_path, hen_script_name)
        
        # Set up images directory with proper permissions
        setup_images_directory(project_name)
        
        # Set up files directory with proper permissions
        setup_files_directory(project_name)
        
        # Set up audio directory with proper permissions
        setup_audio_directory(project_name)
        
        # Set up video directory with proper permissions
        setup_video_directory(project_name)
        
        # Set ownership and permissions for the created directory structure
        from hh.deploy.srv.deploy import setup_deployment_ownership_and_permissions
        setup_deployment_ownership_and_permissions(project_name)
        
        
        # Consolidate all detailed information for the parser
        result_data = {
            "project_name": project_name,
            "project_path": str(project_path),
            "git_repo": f"/srv/{project_name}/git/{project_name}.git",
            "git_branch": project_name,
            "project_owner": project_owner,
            "groups_created": [project_name, f"{project_name}_deploy"],
            "users_created": [user["username"] for user in user_data if user.get("status") == "created"],
            "users_failed": [user["username"] for user in user_data if user.get("status") == "failed"],
            "ssh_keys_generated": len([user for user in user_data if user.get("status") == "created"]),
            "auto_scanned_keys": len(auto_scanned_keys) if auto_scanned_keys else 0,
            "human_scripts_created": [f"/home/{project_owner}/{hen_script_name}"] if project_owner else [],
            "root_scripts_created": [f"/root/{hen_script_name}"],
            "project_ownership": f"{project_owner}:{project_name}" if project_owner else "Unknown",
            "status": "installed"
        }
        gateway.response.set_action_response(success_payload(result_data))
        log("System installation complete!")
        
        # Clear registry cache to prevent permission issues
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        clean_all_caches()
        
        trace_out()
        return True
    except Exception as e:
        warn(f"Installation failed: {str(e)}")
        report_error("backend", f"Installation failed: {str(e)}")
        trace_out()
        return False



def check_existing_setup(project_name: str) -> List[str]:
    """Check for existing project setup and return list of conflicts."""
    trace_in()
    conflicts = []
    gateway = get_gateway()
    
    try:
        # Check for existing project users
        project_users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
        for user in project_users:
            if gateway and gateway.os and gateway.os.user_exists(user):
                conflicts.append(f"user {user}")
                log(f"Found existing user: {user}")
        
        # Check for existing project groups
        project_groups = [project_name, f"{project_name}_deploy", f"{project_name}_admin"]
        for group in project_groups:
            if gateway and gateway.os and gateway.os.group_exists(group):
                conflicts.append(f"group {group}")
                log(f"Found existing group: {group}")
        
        # Check for existing project directory
        srv_project = Path(f'/srv/{project_name}')
        if srv_project.exists():
            conflicts.append(f"directory {srv_project}")
            log(f"Found existing project directory: {srv_project}")
        
        # Check for existing git repository
        git_repo = srv_project / 'git' / f"{project_name}.git"
        if git_repo.exists():
            conflicts.append(f"git repository {git_repo}")
            log(f"Found existing git repository: {git_repo}")
        
        if conflicts:
            log(f"Found {len(conflicts)} existing setup conflicts")
        else:
            log("No existing setup conflicts found")
            
    except Exception as e:
        warn(f"Error checking for existing setup: {str(e)}")
        conflicts.append(f"error checking setup: {str(e)}")
    finally:
        trace_out()
    
    return conflicts

def check_script_conflicts(project_owner: Optional[str], hen_script_name: str) -> List[str]:
    """Check for existing hen scripts in root and human user directories."""
    trace_in()
    conflicts = []
    
    try:
        # Check root directory
        root_home = Path('/root')
        root_hen = root_home / 'hen'
        root_expected_hen = root_home / hen_script_name
        
        # Check if default hen exists when we want to use default name
        if root_hen.exists() and hen_script_name == 'hen':
            conflicts.append(f"/root/hen")
            log(f"Found existing script: /root/hen")
        # Check if our custom hen name already exists
        elif root_expected_hen.exists() and hen_script_name != 'hen':
            conflicts.append(f"/root/{hen_script_name}")
            log(f"Found existing script: /root/{hen_script_name}")
        
        # Check human user directory
        if project_owner:
            human_home = Path(f'/home/{project_owner}')
            human_hen = human_home / 'hen'
            human_expected_hen = human_home / hen_script_name
            
            # Check if default hen exists when we want to use default name
            if human_hen.exists() and hen_script_name == 'hen':
                conflicts.append(f"/home/{project_owner}/hen")
                log(f"Found existing script: /home/{project_owner}/hen")
            # Check if our custom hen name already exists
            elif human_expected_hen.exists() and hen_script_name != 'hen':
                conflicts.append(f"/home/{project_owner}/{hen_script_name}")
                log(f"Found existing script: /home/{project_owner}/{hen_script_name}")
        
        if conflicts:
            log(f"Found {len(conflicts)} script conflicts")
        else:
            log("No script conflicts found")
            
    except Exception as e:
        warn(f"Error checking for script conflicts: {str(e)}")
        conflicts.append(f"error checking scripts: {str(e)}")
    finally:
        trace_out()
    
    return conflicts

def setup_git_repository(project_name: str, project_path: Path) -> None:
    trace_in()
    gateway = get_gateway()
    log("Setting up git repository")
    
    # Create /srv/{project_name} directory structure
    srv_project = Path(f'/srv/{project_name}')
    srv_project.mkdir(parents=True, exist_ok=True)
    
    # Create git directory
    git_dir = srv_project / 'git'
    git_dir.mkdir(parents=True, exist_ok=True)
    
    # Create bare git repository
    bare_repo = git_dir / f"{project_name}.git"
    if bare_repo.exists():
        shutil.rmtree(bare_repo)
    
    subprocess.run(['git', 'init', '--bare', str(bare_repo)], check=True)
    log(f"Created bare git repository: {bare_repo}")
    
    # Set ownership to project owner (detected earlier)
    project_owner = detect_project_owner(project_path)
    if not project_owner:
        raise Exception("Failed to detect project owner - cannot proceed with git repository setup")
    
    gateway.files.chown(str(srv_project), project_owner, group=project_name, recursive=True)
    log(f"Set git repository ownership to {project_owner}:{project_name}")
    
    # Set proper permissions for group access
    gateway.files.chmod_tree(str(bare_repo), dir_mode=0o770, file_mode=0o660)
    
    # Initialize git in project directory if not already a repo
    if not (project_path / '.git').exists():
        log(f"Initializing git repository in {project_path}")
        subprocess.run(['git', 'init'], cwd=str(project_path), check=True)
        
        # Configure git user
        subprocess.run(['git', 'config', 'user.name', f'{project_name} System'], cwd=str(project_path), check=True)
        subprocess.run(['git', 'config', 'user.email', f'system@{project_name}.local'], cwd=str(project_path), check=True)
        
        # Add all files
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True)
        
        # Initial commit
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=str(project_path), check=True)
        
        # Rename branch to project_name (regardless of what git init created)
        subprocess.run(['git', 'branch', '-m', project_name], cwd=str(project_path), check=True)
    
    # Add the bare repo as remote (remove existing if it exists)
    try:
        subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=str(project_path), check=True, capture_output=True)
    except subprocess.CalledProcessError:
        pass  # Remote doesn't exist, that's fine
    subprocess.run(['git', 'remote', 'add', 'origin', str(bare_repo)], cwd=str(project_path), check=True)
    
    # Push to bare repo using project name as branch
    subprocess.run(['git', 'push', 'origin', project_name], cwd=str(project_path), check=True)
    log(f"Pushed project code to {bare_repo} ({project_name} branch)")
    
    # Set HEAD in bare repository to point to the actual branch
    subprocess.run(['git', 'symbolic-ref', 'HEAD', f'refs/heads/{project_name}'], cwd=str(bare_repo), check=True)
    log(f"Set bare repository HEAD to {project_name} branch")
    
    # Fix ownership of entire project folder after all operations
    if project_owner and gateway and gateway.files:
        try:
            # Set ownership of entire project to project_owner:project_name group
            gateway.files.chown(str(project_path), project_owner, group=project_name, recursive=True)
            # Set setgid bit on directories so new files inherit group ownership
            gateway.files.chmod_tree(str(project_path), dir_mode=0o2750)
            log(f"Fixed entire project ownership to {project_owner}:{project_name} with setgid")
        except Exception as e:
            warn(f"Failed to fix project ownership: {str(e)}")
    
    trace_out()

def create_fresh_users(passwords: List[str], user_key: Optional[str], project_name: str, auto_scanned_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    trace_in()
    gateway = get_gateway()
    log("Creating fresh users")
    user_data = []
    admin_tier = 'admin' if 'admin' in HENHOUSE_TIERS else None
    for idx, tier in enumerate(HENHOUSE_TIERS):
        user = f"{project_name}_{tier}"
        password = passwords[idx]
        try:
            useradd_cmd = ['useradd', '-r', '-s', '/bin/bash', '-m', '-d', f'/home/{user}']
            if tier == admin_tier:
                admin_group_name = f"{project_name}_{admin_tier}"
                useradd_cmd.extend(['-g', admin_group_name])
            useradd_cmd.append(user)
            result = subprocess.run(useradd_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, ['useradd'], result.stdout, result.stderr)
            subprocess.run([
                'chpasswd'
            ], input=f'{user}:{password}\n', text=True, check=True, capture_output=True)
            gateway.files.chmod(f'/home/{user}', 0o755)
            
            # All users own their own home directories
            gateway.files.chown(f'/home/{user}', user)
            
            ssh_keys = generate_ssh_keys(user, project_name)
            
            # Add all keys: user-provided, auto-scanned, and any additional
            all_keys = []
            if user_key:
                all_keys.append(user_key)
            if auto_scanned_keys:
                all_keys.extend(auto_scanned_keys)
            
            for key in all_keys:
                add_user_key(user, key)
            
            # Create project-specific config file
            create_user_config_file(user, project_name, password)
            
            # Add users to appropriate groups based on tier
            deploy_group_name = f"{project_name}_deploy"
            if user == f"{project_name}_{HENHOUSE_TIERS[-1]}":
                # Highest tier user gets both groups
                try:
                    subprocess.run(['usermod', '-a', '-G', f'{project_name},{deploy_group_name}', user], check=True, capture_output=True)
                    log(f"Added {user} to groups {project_name} and {deploy_group_name}")
                except subprocess.CalledProcessError as e:
                    warn(f"Failed to add {user} to groups: {e.stderr.decode()}")
            else:
                # Lower tier users get only deploy group
                try:
                    subprocess.run(['usermod', '-a', '-G', deploy_group_name, user], check=True, capture_output=True)
                    log(f"Added {user} to deploy group {deploy_group_name}")
                except subprocess.CalledProcessError as e:
                    warn(f"Failed to add {user} to deploy group: {e.stderr.decode()}")
            
            user_data.append({
                "username": user,
                "status": "created",
                "ssh_keys": ssh_keys,
                "home_directory": f"/home/{user}"
            })
            log(f"Created user: {user}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            warn(f"Failed to create user {user}: {error_msg}")
            user_data.append({
                "username": user,
                "status": "failed",
                "error": error_msg
             })
        except Exception as e:
            warn(f"Failed to create user {user}: {str(e)}")
            user_data.append({
                "username": user,
                "status": "failed",
                "error": str(e)
             })
    trace_out()
    return user_data

def setup_htpasswd_files(project_name: str, passwords: List[str]) -> None:
    """Create/update .htpasswd files for admin and root tiers."""
    trace_in()
    try:
        # Get admin and root tier indices
        admin_idx = HENHOUSE_TIERS.index('admin') if 'admin' in HENHOUSE_TIERS else None
        root_idx = HENHOUSE_TIERS.index('root') if 'root' in HENHOUSE_TIERS else None
        
        if admin_idx is not None:
            admin_tier = HENHOUSE_TIERS[admin_idx]
            admin_user = f"{project_name}_{admin_tier}"
            admin_password = passwords[admin_idx]
            htpasswd_file = f"/var/www/.htpasswd_{admin_tier}"
            
            # Use htpasswd to create/update the file (-b for batch mode, -c to create file)
            # Check if file exists to determine if we should use -c
            file_exists = Path(htpasswd_file).exists()
            cmd = ['htpasswd', '-b']
            if not file_exists:
                cmd.append('-c')  # Create file if it doesn't exist
            cmd.extend([htpasswd_file, admin_user, admin_password])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                log(f"Created/updated {htpasswd_file} with user {admin_user}")
            else:
                warn(f"Failed to create/update {htpasswd_file}: {result.stderr}")
        
        if root_idx is not None:
            root_tier = HENHOUSE_TIERS[root_idx]
            root_user = f"{project_name}_{root_tier}"
            root_password = passwords[root_idx]
            # Use 'panel' as the suffix for root tier .htpasswd file
            htpasswd_file = "/var/www/.htpasswd_panel"
            
            # Use htpasswd to create/update the file (-b for batch mode, -c to create file)
            file_exists = Path(htpasswd_file).exists()
            cmd = ['htpasswd', '-b']
            if not file_exists:
                cmd.append('-c')  # Create file if it doesn't exist
            cmd.extend([htpasswd_file, root_user, root_password])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                log(f"Created/updated {htpasswd_file} with user {root_user}")
            else:
                warn(f"Failed to create/update {htpasswd_file}: {result.stderr}")
        
    except Exception as e:
        warn(f"Failed to setup .htpasswd files: {str(e)}")
        report_error("backend", f"Failed to setup .htpasswd files: {str(e)}")
    finally:
        trace_out()


def setup_core_groups(project_name: str) -> None:
    """Create core groups that users need to be added to."""
    trace_in()
    try:
        log(f"Setting up core groups: {project_name}")
        
        # Create project group
        try:
            subprocess.run(['groupadd', project_name], check=True, capture_output=True)
            log(f"Created group: {project_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr.decode():
                log(f"Group {project_name} already exists")
            else:
                raise
        
        # Create deploy group
        deploy_group_name = f"{project_name}_deploy"
        try:
            subprocess.run(['groupadd', deploy_group_name], check=True, capture_output=True)
            log(f"Created group: {deploy_group_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr.decode():
                log(f"Group {deploy_group_name} already exists")
            else:
                raise

        # Create admin group
        admin_group_name = f"{project_name}_admin"
        try:
            subprocess.run(['groupadd', admin_group_name], check=True, capture_output=True)
            log(f"Created group: {admin_group_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr.decode():
                log(f"Group {admin_group_name} already exists")
            else:
                raise
        
        trace_out()
    except Exception as e:
        warn(f"Failed to setup core groups: {str(e)}")
    finally:
        trace_out()

def setup_project_group(project_name: str, project_path: Path) -> None:
    """Add users to groups and set ownership."""
    trace_in()
    try:
        log(f"Setting up project groups: {project_name}")
        
        deploy_group_name = f"{project_name}_deploy"
        admin_group_name = f"{project_name}_admin"
        
        # Add current user to all groups
        current_user = os.getenv('USER', 'root')
        try:
            subprocess.run(['usermod', '-a', '-G', f'{project_name},{deploy_group_name},{admin_group_name}', current_user], check=True, capture_output=True)
            log(f"Added {current_user} to groups {project_name}, {deploy_group_name}, and {admin_group_name}")
        except subprocess.CalledProcessError as e:
            warn(f"Failed to add {current_user} to groups: {e.stderr.decode()}")
        
        # Auto-detect project owner and add to all groups
        project_owner = detect_project_owner(project_path)
        if project_owner and project_owner != current_user:
            try:
                subprocess.run(['usermod', '-a', '-G', f'{project_name},{deploy_group_name},{admin_group_name}', project_owner], check=True, capture_output=True)
                log(f"Added project owner {project_owner} to groups {project_name}, {deploy_group_name}, and {admin_group_name}")
            except subprocess.CalledProcessError as e:
                warn(f"Failed to add project owner {project_owner} to groups: {e.stderr.decode()}")
        
        # Add www-data to deploy and admin groups so it can read configs and write files
        try:
            subprocess.run(['usermod', '-a', '-G', f'{deploy_group_name},{admin_group_name}', 'www-data'], check=True, capture_output=True)
            log(f"Added www-data to groups {deploy_group_name} and {admin_group_name}")
        except subprocess.CalledProcessError as e:
            log(f"Failed to add www-data to groups (may not exist yet): {e.stderr.decode()}")
        
        # Group ownership will be set at the end of init process
        
    except Exception as e:
        warn(f"Failed to setup project groups: {str(e)}")
    finally:
        trace_out()

def setup_images_directory(project_name: str) -> None:
    """Set up images directory with proper permissions during installation."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Setting up images directory for project {project_name}")
        
        # Create /srv/images/{project_name} directory
        images_dir = Path(f'/srv/images/{project_name}')
        images_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(images_dir), 0o2775)
        log(f"Created images directory with group write: {images_dir}")
        
        # Create deleted subdirectory
        deleted_dir = images_dir / 'deleted'
        deleted_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(deleted_dir), 0o2775)
        log(f"Created deleted subdirectory: {deleted_dir}")
        
        # Set ownership for images directory and subdirectories
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        admin_group_name = f"{project_name}_admin"
        gateway.files.chown(str(images_dir), project_highest_user, group=admin_group_name, recursive=True)
        log(f"Set images directory ownership: {project_highest_user}:{admin_group_name}")
        
        log("Images directory setup completed successfully")
        
    except Exception as e:
        warn(f"Failed to setup images directory: {str(e)}")
        report_error("backend", f"Failed to setup images directory: {str(e)}")
    finally:
        trace_out()

def setup_files_directory(project_name: str) -> None:
    """Set up files directory with proper permissions during installation."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Setting up files directory for project {project_name}")
        
        # Create /srv/files/{project_name} directory
        files_dir = Path(f'/srv/files/{project_name}')
        files_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(files_dir), 0o2775)
        log(f"Created files directory with group write: {files_dir}")
        
        # Create deleted subdirectory
        deleted_dir = files_dir / 'deleted'
        deleted_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(deleted_dir), 0o2775)
        log(f"Created deleted subdirectory: {deleted_dir}")
        
        # Set ownership for files directory
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        admin_group_name = f"{project_name}_admin"
        gateway.files.chown(str(files_dir), project_highest_user, group=admin_group_name, recursive=True)
        log(f"Set files directory ownership: {project_highest_user}:{admin_group_name}")
        
        log("Files directory setup completed successfully")
        
    except Exception as e:
        warn(f"Failed to setup files directory: {str(e)}")
        report_error("backend", f"Failed to setup files directory: {str(e)}")
    finally:
        trace_out()

def setup_audio_directory(project_name: str) -> None:
    """Set up audio directory with proper permissions during installation."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Setting up audio directory for project {project_name}")
        
        # Create /srv/audio/{project_name} directory
        audio_dir = Path(f'/srv/audio/{project_name}')
        audio_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(audio_dir), 0o2775)
        log(f"Created audio directory with group write: {audio_dir}")
        
        # Create deleted subdirectory
        deleted_dir = audio_dir / 'deleted'
        deleted_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(deleted_dir), 0o2775)
        log(f"Created deleted subdirectory: {deleted_dir}")
        
        # Set ownership for audio directory and subdirectories
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        admin_group_name = f"{project_name}_admin"
        gateway.files.chown(str(audio_dir), project_highest_user, group=admin_group_name, recursive=True)
        log(f"Set audio directory ownership: {project_highest_user}:{admin_group_name}")
        
        log("Audio directory setup completed successfully")
        
    except Exception as e:
        warn(f"Failed to setup audio directory: {str(e)}")
        report_error("backend", f"Failed to setup audio directory: {str(e)}")
    finally:
        trace_out()

def setup_video_directory(project_name: str) -> None:
    """Set up video directory with proper permissions during installation."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Setting up video directory for project {project_name}")
        
        # Create /srv/video/{project_name} directory
        video_dir = Path(f'/srv/video/{project_name}')
        video_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(video_dir), 0o2775)
        log(f"Created video directory with group write: {video_dir}")
        
        # Create deleted subdirectory
        deleted_dir = video_dir / 'deleted'
        deleted_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(deleted_dir), 0o2775)
        log(f"Created deleted subdirectory: {deleted_dir}")
        
        # Set ownership for video directory and subdirectories
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        admin_group_name = f"{project_name}_admin"
        gateway.files.chown(str(video_dir), project_highest_user, group=admin_group_name, recursive=True)
        log(f"Set video directory ownership: {project_highest_user}:{admin_group_name}")
        
        log("Video directory setup completed successfully")
        
    except Exception as e:
        warn(f"Failed to setup video directory: {str(e)}")
        report_error("backend", f"Failed to setup video directory: {str(e)}")
    finally:
        trace_out()


