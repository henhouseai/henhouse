import os
import shutil
import subprocess
import configparser
import json
import datetime
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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _install_config_path(project_name: str) -> Path:
    return Path(f"/root/.{project_name}-install.cnf")

def _update_manifest_user_removal(cfg_path: Path, users: List[str]) -> None:
    if not cfg_path.exists() or not users:
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_users"):
        return
    changed = False
    for user in users:
        if parser.has_option("manifest_users", user):
            try:
                obj = json.loads(parser.get("manifest_users", user))
                if isinstance(obj, dict):
                    obj["removed_at"] = _iso_now()
                    parser.set("manifest_users", user, json.dumps(obj, separators=(',', ':')))
                    changed = True
            except Exception:
                continue
    if changed:
        with open(cfg_path, 'w') as f:
            parser.write(f)
        os.chmod(cfg_path, 0o600)

@register_action('uninstall')
@register_command('uninstall')
def uninstall() -> bool:
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

    # Detect project context
    project_name, project_path = detect_project_context()
    log(f"Starting {project_name} system uninstall")
    log(f"Project: {project_name} at {project_path}")
    cfg_path = _install_config_path(project_name)

    # Block uninstall if manifest lists deployed sites
    if cfg_path.exists():
        try:
            parser = configparser.ConfigParser()
            parser.read(cfg_path)
            if parser.has_section("manifest_sites"):
                sites = [item[0] for item in parser.items("manifest_sites")]
                if sites:
                    warn(f"Manifest shows deployed sites: {', '.join(sites)}")
                    warn("Remove them with: http_remove -domain <domain> (or use force there), then rerun uninstall.")
                    trace_out()
                    return False
        except Exception as e:
            warn(f"Could not read manifest_sites: {e}")
            trace_out()
            return False
    
    # Get entry point script name from install config - REQUIRED, no fallback
    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        report_error("action", f"Install config not found: {cfg_path}. Cannot determine script name.")
        trace_out()
        return False
    
    try:
        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        if not parser.has_section("install"):
            warn(f"Missing [install] section in {cfg_path}")
            report_error("action", f"Missing [install] section in {cfg_path}. Cannot determine script name.")
            trace_out()
            return False
        
        entry_point_script_name = parser.get("install", "entry_point_script_name", fallback=None)
        if not entry_point_script_name:
            warn(f"entry_point_script_name not found in install config: {cfg_path}")
            report_error("action", f"entry_point_script_name not found in install config: {cfg_path}. Cannot determine script name.")
            trace_out()
            return False
        
        entry_point_script_name = entry_point_script_name.strip()
        if not entry_point_script_name:
            warn(f"entry_point_script_name is empty in install config: {cfg_path}")
            report_error("action", f"entry_point_script_name is empty in install config: {cfg_path}. Cannot determine script name.")
            trace_out()
            return False
        
        log(f"Using entry point script name from install config: {entry_point_script_name}")
    except Exception as e:
        warn(f"Could not read entry_point_script_name from install config: {e}")
        report_error("action", f"Could not read entry_point_script_name from install config: {e}")
        trace_out()
        return False

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
    seen: set[str] = set()
    deduplicated: list[str] = []
    for user in users_to_remove:
        if user not in seen:
            seen.add(user)
            deduplicated.append(user)
    users_to_remove = deduplicated
    
    log(f"Users to remove: {users_to_remove}")

    # Step 1: Remove users with safety checks
    removed_users = []
    removed_project_users = []  # Track which project users were actually removed
    if not is_error():
        for user in users_to_remove:
            try:
                # Check if user exists first
                user_info = gateway.os.get_user_by_name(user)
                if not user_info:
                    log(f"User {user} does not exist - checking for leftover home directory")
                    # Check for leftover home directory and clean it up
                    user_home = Path(f'/home/{user}')
                    if user_home.exists():
                        log(f"Found leftover home directory for non-existent user: {user}")
                        # Use the directory validation function to check if it's safe to delete
                        debug(f"Validating leftover directory {user_home} for deletion")
                        validation_result = validate_user_directory_for_deletion(user, project_name, user_home, gateway)
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
                validation_result = validate_user_for_deletion(user, project_name, gateway)
                debug(f"Validation result for {user}: {validation_result}")
                if validation_result:
                    # Change ownership back to user before deletion
                    user_home = Path(f'/home/{user}')
                    if user_home.exists():
                        try:
                            gateway.files.chown(str(user_home), user)
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

    # Update manifest with removal timestamps
    if not is_error():
        try:
            _update_manifest_user_removal(cfg_path, removed_project_users)
        except Exception as e:
            warn(f"Failed to update manifest removal timestamps: {e}")

    # Step 2: Remove project directory (only if project highest level user doesn't exist)
    # Note: /srv/images/{project_name}, /srv/files/{project_name}, /srv/audio/{project_name}, and /srv/video/{project_name} are in different locations and NOT touched
    if not is_error():
        srv_project = Path(f'/srv/{project_name}')
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        if srv_project.exists():
            # Check if project highest level user doesn't exist (was deleted or never existed)
            if gateway.os.user_exists(project_highest_user):
                # User still exists - don't delete directory
                warn(f"Project highest level user {project_highest_user} still exists - skipping directory deletion")
            else:
                # User doesn't exist (was successfully deleted or never existed) - safe to delete
                log(f"Removing project directory: {srv_project}")
                shutil.rmtree(srv_project)
                log(f"Note: /srv/images/{project_name}, /srv/files/{project_name}, /srv/audio/{project_name}, and /srv/video/{project_name} are preserved and left untouched")

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
    if not is_error() and removed_project_users and entry_point_script_name:
        log(f"Removed {len(removed_project_users)} project user(s) - proceeding with human/root script cleanup")
        cleanup_human_user_home(project_name, project_path, entry_point_script_name)
        cleanup_root_user_scripts(project_name, project_path, entry_point_script_name)
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
            if not gateway.os.group_exists(group):
                # Group was deleted
                groups_deleted.append(group)
        
        # Check what human scripts were removed
        if project_owner and entry_point_script_name:
            human_home = Path(f'/home/{project_owner}')
            entry_point_script = human_home / entry_point_script_name
            if not entry_point_script.exists():
                human_scripts_removed.append(f"/home/{project_owner}/{entry_point_script_name}")
        
        # Check what root scripts were removed
        if entry_point_script_name:
            root_home = Path('/root')
            root_entry_point_script = root_home / entry_point_script_name
            if not root_entry_point_script.exists():
                root_scripts_removed.append(f"/root/{entry_point_script_name}")
        
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

def cleanup_existing_users(project_name: str, additional_users: Optional[List[str]] = None) -> None:
    trace_in()
    gateway = get_gateway()
    log("Cleaning up existing users")
    
    # Load manifest to constrain deletions
    manifest_users = {}
    cfg_path = Path(f"/root/.{project_name}-install.cnf")
    if cfg_path.exists():
        try:
            parser = configparser.ConfigParser()
            parser.read(cfg_path)
            if parser.has_section("manifest_users"):
                manifest_users = {k: v for k, v in parser["manifest_users"].items()}
        except Exception as e:
            warn(f"Could not read manifest_users: {e}")
    
    # Get dynamic project users
    project_users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
    
    # Combine project users with additional users to remove
    users_to_remove = project_users.copy()
    if additional_users:
        users_to_remove.extend(additional_users)
    
    # Remove duplicates while preserving order
    seen: set[str] = set()
    deduplicated: list[str] = []
    for user in users_to_remove:
        if user not in seen:
            seen.add(user)
            deduplicated.append(user)
    users_to_remove = deduplicated

    # If manifest exists, only remove those in manifest
    if manifest_users:
        users_to_remove = [u for u in users_to_remove if u in manifest_users]
    
    log(f"Users to remove: {users_to_remove}")
    
    for user in users_to_remove:
        try:
            # Safety validation before deletion
            if not validate_user_for_deletion(user, project_name, gateway):
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

# Import detect_project_context from utils
from hh.deploy.deploy_utils import detect_project_context

def reset_project_group_ownership(project_name: str, project_path: Path) -> None:
    """Reset project folder group ownership and delete project group."""
    trace_in()
    gateway = get_gateway()
    try:
        log(f"Resetting project group ownership: {project_name}")
        
        # Reset group ownership to match the directory owner's group
        try:
            # Get the current owner of the directory
            stat_info = project_path.stat()
            owner_uid = stat_info.st_uid
            owner_info = gateway.os.get_user_by_uid(owner_uid) if gateway and gateway.os else None
            if not owner_info:
                warn(f"Could not resolve owner for uid {owner_uid}")
            else:
                owner_name = owner_info["name"]
                
                # Get the owner's primary group
                group_info = gateway.os.get_group_by_gid(owner_info["gid"]) if gateway and gateway.os else None
                if group_info:
                    primary_group = group_info["name"]
                    subprocess.run(['chgrp', '-R', primary_group, str(project_path)], check=True, capture_output=True)
                    log(f"Reset group ownership of {project_path} to {primary_group} (owner: {owner_name})")
                else:
                    warn(f"Could not resolve group for gid {owner_info['gid']}")
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

def cleanup_human_user_home(project_name: str, project_path: Path, entry_point_script_name: Optional[str] = None) -> None:
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
        cleanup_user_entry_points(project_name, project_path, project_owner, entry_point_script_name, is_root=False)
        
        # Remove project-specific config file
        config_file = Path(f"/home/{project_owner}/.{project_name}.cnf")
        if config_file.exists():
            try:
                config_file.unlink()
                log(f"Removed {config_file}")
            except Exception as e:
                warn(f"Failed to remove {config_file}: {e}")
        
    except Exception as e:
        warn(f"Failed to cleanup human user home directory: {str(e)}")
    finally:
        trace_out()

def cleanup_root_user_scripts(project_name: str, project_path: Path, entry_point_script_name: Optional[str] = None) -> None:
    """Clean up root user entry points."""
    trace_in()
    try:
        log("Cleaning up root user entry points")
        cleanup_user_entry_points(project_name, project_path, "root", entry_point_script_name, is_root=True)
        # Remove project-specific config file
        config_file = Path(f"/root/.{project_name}.cnf")
        if config_file.exists():
            try:
                config_file.unlink()
                log(f"Removed {config_file}")
            except Exception as e:
                warn(f"Failed to remove {config_file}: {e}")
        
    except Exception as e:
        warn(f"Failed to cleanup root user entry points: {str(e)}")
    finally:
        trace_out()

def remove_htpasswd_users(project_name: str) -> None:
    """Remove users from .htpasswd files for guest, admin and root tiers."""
    trace_in()
    try:
        # Load htpasswd_dir from install config
        htpasswd_dir = "/var/www"  # Default fallback
        try:
            from hh.deploy.users.install import _load_install_config
            install_config = _load_install_config(project_name)
            if install_config:
                htpasswd_dir = install_config.get("htpasswd_dir", "/var/www").strip()
        except Exception:
            pass  # Use default if config can't be loaded
        
        # Get guest, admin and root tier indices
        guest_idx = HENHOUSE_TIERS.index('guest') if 'guest' in HENHOUSE_TIERS else None
        admin_idx = HENHOUSE_TIERS.index('admin') if 'admin' in HENHOUSE_TIERS else None
        root_idx = HENHOUSE_TIERS.index('root') if 'root' in HENHOUSE_TIERS else None
        
        # Remove guest tier user (if it exists)
        if guest_idx is not None:
            guest_tier = HENHOUSE_TIERS[guest_idx]
            guest_user = f"{project_name}_{guest_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_{guest_tier}"
            
            # Use htpasswd -D to delete the user from the file
            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, guest_user], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {guest_user} from {htpasswd_file}")
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {guest_user} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {guest_user} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")
        
        if admin_idx is not None:
            admin_tier = HENHOUSE_TIERS[admin_idx]
            admin_user = f"{project_name}_{admin_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_{admin_tier}"
            
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
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_panel"
            
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
