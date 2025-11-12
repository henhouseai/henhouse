import os
import shutil
import subprocess
import pwd
import grp
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error

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

@register_action('uninstall')
@register_command('uninstall')
def uninstall() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Detect project context
    project_name, project_path = detect_project_context()
    log(f"Starting {project_name} system uninstall")
    log(f"Project: {project_name} at {project_path}")
    
    # Discover script names from tier user directory
    hen_script_name, gateway_script_name = discover_script_names(project_name)
    log(f"Discovered script names: hen={hen_script_name}, gateway={gateway_script_name}")

    # Parse additional users to remove
    remove_users = gateway.get_arg('remove_user')
    additional_users = []
    if remove_users:
        additional_users = [user.strip() for user in remove_users.split(',') if user.strip()]
        log(f"Additional users to remove: {additional_users}")
    
    # Get dynamic project users
    project_users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
    
    # Combine project users with additional users
    users_to_remove = project_users.copy()
    users_to_remove.extend(additional_users)
    
    # Remove duplicates
    seen = set()
    users_to_remove = [user for user in users_to_remove if not (user in seen or seen.add(user))]
    
    log(f"Users to remove: {users_to_remove}")

    # Step 1: Remove users with safety checks
    removed_users = []
    removed_project_users = []  # Track which project users were actually removed
    if not is_error():
        for user in users_to_remove:
            try:
                # Check if user exists first
                try:
                    user_info = pwd.getpwnam(user)
                except KeyError:
                    log(f"User {user} does not exist - checking for leftover home directory")
                    # Check for leftover home directory and clean it up
                    user_home = Path(f'/home/{user}')
                    if user_home.exists():
                        log(f"Found leftover home directory for non-existent user: {user}")
                        # Use the directory validation function to check if it's safe to delete
                        debug(f"Validating leftover directory {user_home} for deletion")
                        validation_result = validate_user_directory_for_deletion(user, project_name, user_home)
                        debug(f"Validation result for leftover directory {user_home}: {validation_result}")
                        if validation_result:
                            log(f"Removing leftover home directory for non-existent user: {user}")
                            shutil.rmtree(user_home)
                            removed_users.append(f"{user} (home directory only)")
                            # Track if this was a project user (not an additional user)
                            if user in project_users:
                                removed_project_users.append(user)
                        else:
                            warn(f"Skipping deletion of leftover home directory for {user} - failed safety checks")
                    else:
                        log(f"No leftover home directory found for {user}")
                    continue
                
                debug(f"Validating user {user} for deletion")
                validation_result = validate_user_for_deletion(user, project_name)
                debug(f"Validation result for {user}: {validation_result}")
                if validation_result:
                    # Change ownership back to user before deletion
                    user_home = Path(f'/home/{user}')
                    if user_home.exists():
                        try:
                            os.chown(user_home, user_info.pw_uid, user_info.pw_gid)
                            log(f"Changed ownership of {user_home} back to {user}")
                        except Exception as e:
                            warn(f"Failed to change ownership of {user_home}: {str(e)}")
                    
                    subprocess.run(['userdel', '-r', user], check=True, capture_output=True)
                    log(f"Removed user: {user}")
                    removed_users.append(user)
                    # Track if this was a project user (not an additional user)
                    if user in project_users:
                        removed_project_users.append(user)
                else:
                    warn(f"Skipping deletion of user {user} - failed safety checks")
                    debug(f"User {user} validation failed - see detailed debug info above")
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode()
                warn(f"Failed to remove user {user}: {error_msg}")
                debug(f"userdel error for {user}: {error_msg}")
            except Exception as e:
                warn(f"Error removing user {user}: {str(e)}")
                debug(f"Exception for {user}: {str(e)}")

    # Step 2: Remove project directory (only if project highest level user doesn't exist)
    # Note: /srv/images/{project_name} and /srv/files/{project_name} are in different locations and NOT touched
    if not is_error():
        srv_project = Path(f'/srv/{project_name}')
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        if srv_project.exists():
            # Check if project highest level user doesn't exist (was deleted or never existed)
            try:
                # Try to get user info - if this fails, user doesn't exist
                pwd.getpwnam(project_highest_user)
                # If we get here, user still exists - don't delete directory
                warn(f"Project highest level user {project_highest_user} still exists - skipping directory deletion")
            except KeyError:
                # User doesn't exist (was successfully deleted or never existed) - safe to delete
                log(f"Removing project directory: {srv_project}")
                shutil.rmtree(srv_project)
                log(f"Note: /srv/images/{project_name} and /srv/files/{project_name} are preserved and left untouched")

    # Step 3: Remove project owner from group BEFORE deleting the group
    if not is_error():
        project_owner = detect_project_owner(project_path)
        if project_owner:
            try:
                subprocess.run(['gpasswd', '-d', project_owner, project_name], check=True, capture_output=True)
                log(f"Removed project owner {project_owner} from group {project_name}")
            except subprocess.CalledProcessError as e:
                if "not a member" not in e.stderr.decode() and "does not exist" not in e.stderr.decode():
                    warn(f"Failed to remove project owner {project_owner} from group {project_name}: {e.stderr.decode()}")

    # Step 4: Clean up human user (project owner) home directory
    # Only do this if we actually removed at least one project user (safety check)
    # This prevents accidentally deleting scripts from other projects on a second uninstall run
    if not is_error() and removed_project_users:
        log(f"Removed {len(removed_project_users)} project user(s) - proceeding with human/root script cleanup")
        cleanup_human_user_home(project_name, project_path, hen_script_name, gateway_script_name)
        cleanup_root_user_scripts(project_name, project_path, hen_script_name, gateway_script_name)
    elif not is_error() and not removed_project_users:
        log("No project users were removed - skipping human/root script cleanup for safety")
        warn("Skipping human/root script cleanup - no project users were found/removed. This prevents accidental deletion of scripts from other projects.")

    # Step 5: Remove users from .htpasswd files
    if not is_error():
        remove_htpasswd_users(project_name)
    
    # Step 6: Reset project group ownership (this deletes the group)
    if not is_error():
        reset_project_group_ownership(project_name, project_path)

    # Final result
    result = not is_error()
    if result:
        log("System uninstall completed successfully")
        
        # Consolidate all detailed information for the parser
        skipped_users = [user for user in users_to_remove if user not in removed_users]
        srv_project = Path(f'/srv/{project_name}')
        project_directory_removed = not srv_project.exists()
        groups_deleted = []
        human_scripts_removed = []
        root_scripts_removed = []
        project_owner = detect_project_owner(project_path)
        
        # Check what groups were actually deleted
        groups_to_check = [project_name, f"{project_name}_deploy"]
        for group in groups_to_check:
            try:
                grp.getgrnam(group)
                # Group still exists
            except KeyError:
                # Group was deleted
                groups_deleted.append(group)
        
        # Check what human scripts were removed
        if project_owner and hen_script_name:
            human_home = Path(f'/home/{project_owner}')
            hen_script = human_home / hen_script_name
            if not hen_script.exists():
                human_scripts_removed.append(f"/home/{project_owner}/{hen_script_name}")
            if gateway_script_name:
                gateway_script = human_home / gateway_script_name
                if not gateway_script.exists():
                    human_scripts_removed.append(f"/home/{project_owner}/{gateway_script_name}")
        
        # Check what root scripts were removed
        if hen_script_name:
            root_home = Path('/root')
            root_hen_script = root_home / hen_script_name
            if not root_hen_script.exists():
                root_scripts_removed.append(f"/root/{hen_script_name}")
            if gateway_script_name:
                root_gateway_script = root_home / gateway_script_name
                if not root_gateway_script.exists():
                    root_scripts_removed.append(f"/root/{gateway_script_name}")
        
        result_data = {
            "project_name": project_name,
            "project_path": str(project_path),
            "project_owner": project_owner,
            "users_removed": removed_users,
            "users_skipped": skipped_users,
            "users_total_attempted": len(users_to_remove),
            "project_directory_removed": project_directory_removed,
            "project_directory_path": str(srv_project),
            "groups_deleted": groups_deleted,
            "groups_total_attempted": len(groups_to_check),
            "human_scripts_removed": human_scripts_removed,
            "root_scripts_removed": root_scripts_removed,
            "safety_checks_passed": len(removed_users),
            "safety_checks_failed": len(skipped_users),
            "status": "uninstalled"
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("System uninstall encountered problems")

    # Clear registry cache to prevent permission issues
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    trace_out()
    return result

def validate_user_directory_for_deletion(user: str, project_name: str, user_home: Path) -> bool:
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
        try:
            # Check if the expected user exists and get their UID
            user_info = pwd.getpwnam(user)
            expected_uid = user_info.pw_uid
        except KeyError:
            # User doesn't exist, so we can't validate ownership
            warn(f"User {user} does not exist - cannot validate directory ownership")
            trace_out()
            return False
        
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
            'hen',                 # User's hen wrapper script
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

def validate_user_for_deletion(user: str, project_name: str) -> bool:
    """Validate that a user is safe to delete (appears to be a project agent user)."""
    trace_in()
    try:
        # Check if user exists
        user_info = pwd.getpwnam(user)
        
        # Safety check 1: User must be a system user (UID < 1000)
        if user_info.pw_uid >= 1000:
            warn(f"User {user} has UID {user_info.pw_uid} (>= 1000) - SKIPPING")
            debug(f"User UID: {user_info.pw_uid}")
            debug(f"Expected UID < 1000: {user_info.pw_uid < 1000}")
            debug(f"User info: {user_info}")
            trace_out()
            return False
        
        # Safety check 2: User must have /bin/bash as shell
        if user_info.pw_shell != '/bin/bash':
            warn(f"User {user} has shell {user_info.pw_shell} (not /bin/bash) - SKIPPING")
            debug(f"User shell: {user_info.pw_shell}")
            debug(f"Expected shell: /bin/bash")
            debug(f"User info: {user_info}")
            trace_out()
            return False
        
        # Safety check 3: User must have expected home directory path
        expected_home = f'/home/{user}'
        if user_info.pw_dir != expected_home:
            warn(f"User {user} has unexpected home directory {user_info.pw_dir} - SKIPPING")
            debug(f"Expected home: {expected_home}")
            debug(f"Actual home: {user_info.pw_dir}")
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
        
    except KeyError:
        log(f"User {user} does not exist - safe to proceed")
        trace_out()
        return True
    except Exception as e:
        warn(f"Error validating user {user}: {str(e)} - SKIPPING")
        trace_out()
        return False

def cleanup_existing_users(project_name: str, additional_users: List[str] = None) -> None:
    trace_in()
    log("Cleaning up existing users")
    
    # Get dynamic project users
    project_users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
    
    # Combine project users with additional users to remove
    users_to_remove = project_users.copy()
    if additional_users:
        users_to_remove.extend(additional_users)
    
    # Remove duplicates while preserving order
    seen = set()
    users_to_remove = [user for user in users_to_remove if not (user in seen or seen.add(user))]
    
    log(f"Users to remove: {users_to_remove}")
    
    for user in users_to_remove:
        try:
            # Safety validation before deletion
            if not validate_user_for_deletion(user, project_name):
                warn(f"Skipping deletion of user {user} - failed safety checks")
                continue
            
            # Proceed with deletion
            subprocess.run(['userdel', '-r', user], check=True, capture_output=True)
            log(f"Removed user: {user}")
        except subprocess.CalledProcessError as e:
            warn(f"Failed to remove user {user}: {e.stderr.decode()}")
        except Exception as e:
            warn(f"Error removing user {user}: {str(e)}")
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

# Import detect_project_context from utils
from hh.deploy.utils import detect_project_context

def discover_script_names(project_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Discover hen script name and gateway script name from tier user directory."""
    trace_in()
    hen_script_name = None
    gateway_script_name = None
    
    try:
        # Get first tier user
        if not HENHOUSE_TIERS:
            warn("No tiers defined - cannot discover script names")
            trace_out()
            return None, None
        
        first_tier = HENHOUSE_TIERS[0]
        tier_user = f"{project_name}_{first_tier}"
        tier_user_home = Path(f'/home/{tier_user}')
        
        if not tier_user_home.exists():
            log(f"Tier user home {tier_user_home} does not exist - cannot discover script names")
            trace_out()
            return None, None
        
        # Look for hen script (could be 'hen' or custom name)
        # Look for gateway script (could be 'gateway.py' or 'gateway-{name}')
        for item in tier_user_home.iterdir():
            if item.is_file() and os.access(item, os.X_OK):
                name = item.name
                # Check if it's a hen script (contains 'python3 gateway')
                if name != 'gateway.py' and not name.startswith('gateway-'):
                    try:
                        with open(item, 'r') as f:
                            content = f.read()
                        if 'python3 gateway' in content:
                            hen_script_name = name
                            log(f"Discovered hen script name: {hen_script_name}")
                    except Exception:
                        pass
                
                # Check if it's a gateway script (starts with gateway)
                if name == 'gateway.py' or name.startswith('gateway-'):
                    gateway_script_name = name
                    log(f"Discovered gateway script name: {gateway_script_name}")
        
        if not hen_script_name:
            # Default to 'hen' if not found
            hen_script_name = 'hen'
            log("No custom hen script found, defaulting to 'hen'")
        
        if not gateway_script_name:
            # Default to 'gateway.py' if not found
            gateway_script_name = 'gateway.py'
            log("No gateway script found, defaulting to 'gateway.py'")
        
        log(f"Discovered script names: hen={hen_script_name}, gateway={gateway_script_name}")
        
    except Exception as e:
        warn(f"Error discovering script names: {str(e)}")
        # Default to standard names on error
        hen_script_name = 'hen'
        gateway_script_name = 'gateway.py'
    finally:
        trace_out()
    
    return hen_script_name, gateway_script_name

def reset_project_group_ownership(project_name: str, project_path: Path) -> None:
    """Reset project folder group ownership and delete project group."""
    trace_in()
    try:
        log(f"Resetting project group ownership: {project_name}")
        
        # Reset group ownership to match the directory owner's group
        try:
            # Get the current owner of the directory
            stat_info = project_path.stat()
            owner_uid = stat_info.st_uid
            owner_info = pwd.getpwuid(owner_uid)
            owner_name = owner_info.pw_name
            
            # Get the owner's primary group
            primary_group = grp.getgrgid(owner_info.pw_gid).gr_name
            subprocess.run(['chgrp', '-R', primary_group, str(project_path)], check=True, capture_output=True)
            log(f"Reset group ownership of {project_path} to {primary_group} (owner: {owner_name})")
        except subprocess.CalledProcessError as e:
            warn(f"Failed to reset group ownership: {e.stderr.decode()}")
        except Exception as e:
            warn(f"Failed to get owner group info: {str(e)}")
        
        # Delete all project groups
        groups_to_delete = [project_name, f"{project_name}_deploy", f"{project_name}_admin"]
        for group in groups_to_delete:
            try:
                subprocess.run(['groupdel', group], check=True, capture_output=True)
                log(f"Deleted group: {group}")
            except subprocess.CalledProcessError as e:
                if "does not exist" in e.stderr.decode():
                    log(f"Group {group} does not exist")
                else:
                    warn(f"Failed to delete group {group}: {e.stderr.decode()}")
        
    except Exception as e:
        warn(f"Failed to reset project group: {str(e)}")
    finally:
        trace_out()

def cleanup_user_convenience_scripts(project_name: str, project_path: Path, username: str, hen_script_name: Optional[str] = None, gateway_script_name: Optional[str] = None, is_root: bool = False) -> None:
    """Clean up convenience scripts (hen) for a user."""
    trace_in()
    try:
        log(f"Cleaning up convenience scripts for {'root' if is_root else username}")
        
        # Default to standard names if not provided
        if not hen_script_name:
            hen_script_name = 'hen'
        if not gateway_script_name:
            gateway_script_name = 'gateway.py'
        
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
        
        # Remove hen script if it exists and looks like our script
        hen_script = user_home / hen_script_name
        if hen_script.exists():
            try:
                with open(hen_script, 'r') as f:
                    content = f.read()
                
                # Check if it references the gateway script (either gateway.py or gateway-{name})
                if f'python3 {gateway_script_name}' in content or 'python3 gateway' in content:
                    hen_script.unlink()
                    log(f"Removed hen script ({hen_script_name}) from {user_display}'s home directory")
                else:
                    log(f"hen script ({hen_script_name}) in {user_display}'s home directory doesn't match our pattern - skipping")
            except Exception as e:
                warn(f"Failed to remove hen script from {user_display}'s home: {str(e)}")
        
        # Remove gateway script if it exists and looks like our script
        gateway_script = user_home / gateway_script_name
        if gateway_script.exists():
            try:
                with open(gateway_script, 'r') as f:
                    content = f.read()
                
                # Check if it's our gateway script (has sys.path.insert)
                if 'sys.path.insert' in content:
                    gateway_script.unlink()
                    log(f"Removed gateway script ({gateway_script_name}) from {user_display}'s home directory")
                else:
                    log(f"gateway script ({gateway_script_name}) in {user_display}'s home directory doesn't match our pattern - skipping")
            except Exception as e:
                warn(f"Failed to remove gateway script from {user_display}'s home: {str(e)}")
        
        
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
        
        log(f"Convenience scripts cleanup complete for {user_display}")
        
    except Exception as e:
        warn(f"Failed to cleanup convenience scripts for {'root' if is_root else username}: {str(e)}")
    finally:
        trace_out()

def cleanup_human_user_home(project_name: str, project_path: Path, hen_script_name: Optional[str] = None, gateway_script_name: Optional[str] = None) -> None:
    """Clean up human user (project owner) home directory setup."""
    trace_in()
    try:
        # Detect project owner (human user)
        project_owner = detect_project_owner(project_path)
        if not project_owner:
            log("No project owner detected - skipping human user home cleanup")
            trace_out()
            return
        
        log(f"Cleaning up human user home directory for {project_owner}")
        cleanup_user_convenience_scripts(project_name, project_path, project_owner, hen_script_name, gateway_script_name, is_root=False)
        
    except Exception as e:
        warn(f"Failed to cleanup human user home directory: {str(e)}")
    finally:
        trace_out()

def cleanup_root_user_scripts(project_name: str, project_path: Path, hen_script_name: Optional[str] = None, gateway_script_name: Optional[str] = None) -> None:
    """Clean up root user convenience scripts."""
    trace_in()
    try:
        log("Cleaning up root user convenience scripts")
        cleanup_user_convenience_scripts(project_name, project_path, "root", hen_script_name, gateway_script_name, is_root=True)
        
    except Exception as e:
        warn(f"Failed to cleanup root user convenience scripts: {str(e)}")
    finally:
        trace_out()

def remove_htpasswd_users(project_name: str) -> None:
    """Remove users from .htpasswd files for admin and root tiers."""
    trace_in()
    try:
        # Get admin and root tier indices
        admin_idx = HENHOUSE_TIERS.index('admin') if 'admin' in HENHOUSE_TIERS else None
        root_idx = HENHOUSE_TIERS.index('root') if 'root' in HENHOUSE_TIERS else None
        
        if admin_idx is not None:
            admin_tier = HENHOUSE_TIERS[admin_idx]
            admin_user = f"{project_name}_{admin_tier}"
            htpasswd_file = f"/var/www/.htpasswd_{admin_tier}"
            
            # Use htpasswd -D to delete the user from the file
            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, admin_user], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {admin_user} from {htpasswd_file}")
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {admin_user} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {admin_user} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")
        
        if root_idx is not None:
            root_tier = HENHOUSE_TIERS[root_idx]
            root_user = f"{project_name}_{root_tier}"
            # Use 'panel' as the suffix for root tier .htpasswd file
            htpasswd_file = "/var/www/.htpasswd_panel"
            
            # Use htpasswd -D to delete the user from the file
            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, root_user], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {root_user} from {htpasswd_file}")
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {root_user} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {root_user} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")
        
    except Exception as e:
        warn(f"Failed to remove users from .htpasswd files: {str(e)}")
    finally:
        trace_out()
