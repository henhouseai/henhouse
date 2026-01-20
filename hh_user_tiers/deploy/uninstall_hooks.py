"""
hh_user_tiers module uninstall hooks.

Handles tier user removal with safety validation.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.response.json_standard import success_payload
from hh.render.render import TableData, FieldConfig
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.user_accounts import detect_project_owner
from hh_user_tiers.deploy.uninstall_helpers_safety import validate_user_for_deletion, validate_user_directory_for_deletion
from hh_user_tiers.deploy.uninstall_helpers_manifest import update_manifest_user_removal

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

# Module-scoped config storage
tier_config: Dict[str, Any] = {}


@register_module_hook('uninstall_15_users', 'Remove tier users with safety validation')
def remove_tier_users() -> Dict[str, Any]:
    """Remove tier users with comprehensive safety checks."""
    trace_in()
    from hh.deploy.uninstall_hooks import UNINSTALL_CONFIG

    project_name = UNINSTALL_CONFIG["project_name"]
    gateway = get_gateway()

    # Get dynamic project users
    project_users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]
    users_to_remove = project_users.copy()

    log(f"Users to remove: {users_to_remove}")

    # Remove users with safety checks
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
                        debug(f"Validating leftover directory {user_home} for deletion")
                        validation_result = validate_user_directory_for_deletion(user, project_name, user_home, gateway)
                        debug(f"Validation result for leftover directory {user_home}: {validation_result}")
                        if validation_result:
                            log(f"Removing leftover home directory for non-existent user: {user}")
                            shutil.rmtree(user_home)
                            removed_users.append(f"{user} (home directory only)")
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

    # Store removed users for later hooks
    tier_config["removed_users"] = removed_users
    tier_config["removed_project_users"] = removed_project_users
    tier_config["users_total_attempted"] = len(users_to_remove)
    tier_config["users_skipped"] = [user for user in users_to_remove if user not in removed_users]

    # Update UNINSTALL_CONFIG so other modules know which users were removed
    UNINSTALL_CONFIG["removed_project_users"] = removed_project_users

    log(f"hh_user_tiers: Removed {len(removed_users)} user(s), skipped {len(tier_config['users_skipped'])}")
    return trace_out({
        "status": "success",
        "removed_users": removed_users,
        "removed_count": len(removed_users)
    })


@register_module_hook('uninstall_20_manifest', 'Update manifest with removal timestamps')
def update_user_manifest() -> Dict[str, Any]:
    """Update manifest with removal timestamps for removed users."""
    trace_in()
    from hh.deploy.uninstall_hooks import UNINSTALL_CONFIG

    cfg_path = UNINSTALL_CONFIG["config_path"]
    removed_project_users = tier_config.get("removed_project_users", [])

    if not is_error():
        try:
            update_manifest_user_removal(cfg_path, removed_project_users)
            log("hh_user_tiers: Manifest updated with removal timestamps")
        except Exception as e:
            warn(f"Failed to update manifest removal timestamps: {e}")

    return trace_out({"status": "success"})


@register_module_hook('uninstall_25_project_dir', 'Remove project directory if safe')
def remove_project_directory() -> Dict[str, Any]:
    """Remove /srv/{project} directory only if highest tier user is gone."""
    trace_in()
    from hh.deploy.uninstall_hooks import UNINSTALL_CONFIG

    project_name = UNINSTALL_CONFIG["project_name"]
    gateway = get_gateway()

    project_directory_removed = False
    srv_project = Path(f'/srv/{project_name}')

    if not is_error():
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
                project_directory_removed = True
                log(f"Note: /srv/images/{project_name}, /srv/files/{project_name}, /srv/audio/{project_name}, and /srv/video/{project_name} are preserved and left untouched")

    tier_config["project_directory_removed"] = project_directory_removed
    tier_config["project_directory_path"] = str(srv_project)

    log(f"hh_user_tiers: Project directory {'removed' if project_directory_removed else 'preserved'}")
    return trace_out({"status": "success", "directory_removed": project_directory_removed})


@register_module_hook('uninstall_30_groups', 'Remove owner from groups and delete groups')
def cleanup_groups() -> Dict[str, Any]:
    """Remove project owner from groups, delete groups, reset ownership."""
    trace_in()
    from hh.deploy.uninstall_hooks import UNINSTALL_CONFIG

    project_name = UNINSTALL_CONFIG["project_name"]
    project_path = UNINSTALL_CONFIG["project_path"]
    gateway = get_gateway()

    groups_deleted = []

    if not is_error():
        # Remove project owner from group BEFORE deleting the group
        project_owner = detect_project_owner(project_path)
        if project_owner:
            try:
                subprocess.run(['gpasswd', '-d', project_owner, project_name], check=True, capture_output=True)
                log(f"Removed project owner {project_owner} from group {project_name}")
            except subprocess.CalledProcessError as e:
                if "not a member" not in e.stderr.decode() and "does not exist" not in e.stderr.decode():
                    warn(f"Failed to remove project owner {project_owner} from group {project_name}: {e.stderr.decode()}")

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
                groups_deleted.append(group)
            except subprocess.CalledProcessError as e:
                if "does not exist" in e.stderr.decode():
                    log(f"Group {group} does not exist")
                else:
                    warn(f"Failed to delete group {group}: {e.stderr.decode()}")

    tier_config["groups_deleted"] = groups_deleted
    tier_config["groups_total_attempted"] = 3

    log(f"hh_user_tiers: Deleted {len(groups_deleted)} group(s)")
    return trace_out({"status": "success", "groups_deleted": groups_deleted})


@register_module_hook('uninstall_95_render', 'Render tier user removal summary')
def render_tier_removal_summary() -> Dict[str, Any]:
    """Render tier user removal summary."""
    trace_in()

    # Return empty for now - can add tier-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
