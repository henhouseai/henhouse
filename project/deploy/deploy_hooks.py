"""
Project Module - Git-based Project Management

Provides git operations for push-project/pull-project functionality
including git directory preservation, restoration, and permissions.
"""

import subprocess
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

# Debug initialization
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


pre_validated_git_config: dict = {}

@register_module_hook('deploy_pre_validate')
def validate_project_config():
    """Pre-validate project-specific configuration."""
    global pre_validated_git_config

    log("Validating project deployment configuration")

    # For now, just store basic project context - git operations validate their own paths
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            raise ValueError("Could not detect project context")

        pre_validated_git_config = {
            'project_name': project_name,
            'current_path': current_path
        }

        log(f"Pre-validated project config for: {project_name}")
    except Exception as e:
        warn(f"Failed to validate project config: {e}")
        raise ValueError(f"Failed to validate project config: {e}")


@register_module_hook('deploy_git_preserve_ops')
def preserve_git_directory() -> dict:
    """Preserve git directory by moving it to a temporary location."""
    import shutil

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project git hook: Could not detect project name")
            return {"status": "error", "component": "git_preserve", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        git_dir = dest / 'git'
        temp_git_path = dest.parent / f'{project_name}_git'

        if not git_dir.exists():
            log("project git hook: Git directory does not exist, nothing to preserve")
            return {"status": "skipped", "component": "git_preserve", "reason": "no_git_dir"}

        # Clean up any existing temp git directory
        if temp_git_path.exists():
            shutil.rmtree(temp_git_path)
            log(f"project git hook: Removed existing temporary git directory: {temp_git_path}")

        # Move git directory to temp location
        shutil.move(str(git_dir), str(temp_git_path))
        log(f"project git hook: Preserved git directory to: {temp_git_path}")

        return {
            "status": "completed",
            "component": "git_preserve",
            "git_dir": str(git_dir),
            "temp_path": str(temp_git_path),
            "preserved": True
        }

    except Exception as e:
        warn(f"project git hook: Failed to preserve git directory: {e}")
        report_error("backend", f"project git hook: Failed to preserve git directory: {e}")
        return {"status": "error", "component": "git_preserve", "error": str(e)}


@register_module_hook('deploy_git_restore_ops')
def restore_git_directory() -> dict:
    """Restore git directory from temporary location."""
    import shutil

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project git hook: Could not detect project name")
            return {"status": "error", "component": "git_restore", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        git_dir = dest / 'git'
        temp_git_path = dest.parent / f'{project_name}_git'

        if not temp_git_path.exists():
            warn(f"project git hook: Temporary git directory not found: {temp_git_path}")
            return {"status": "error", "component": "git_restore", "error": "temp_git_missing"}

        # Move git directory back to its original location
        shutil.move(str(temp_git_path), str(git_dir))
        log(f"project git hook: Restored git directory to: {git_dir}")

        return {
            "status": "completed",
            "component": "git_restore",
            "git_dir": str(git_dir),
            "temp_path": str(temp_git_path),
            "restored": True
        }

    except Exception as e:
        warn(f"project git hook: Failed to restore git directory: {e}")
        report_error("backend", f"project git hook: Failed to restore git directory: {e}")
        return {"status": "error", "component": "git_restore", "error": str(e)}


@register_module_hook('deploy_permissions_special')
def set_git_permissions() -> dict:
    """Set special permissions for git directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("project permissions hook: Could not detect project name")
            return {"status": "error", "component": "git", "error": "no_project"}

        gateway = get_gateway()
        dest = Path("/srv") / project_name
        git_dir = dest / 'git'

        if not git_dir.exists():
            log("project permissions hook: Git directory does not exist, skipping git permissions")
            return {"status": "skipped", "component": "git", "reason": "no_git_dir"}

        # Get project user info
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"project permissions hook: User not found: {project_highest_user}")
            return {"status": "error", "component": "git", "error": "user_not_found"}

        project_highest_uid = user_info["uid"]

        # Set git directory permissions (770/660 - more permissive than base)
        # Git needs group write for collaboration
        subprocess.run(['chown', '-R', f'{project_highest_uid}:{project_name}', str(git_dir)], check=True)
        subprocess.run(['find', str(git_dir), '-type', 'd', '-exec', 'chmod', '770', '{}', ';'], check=True)
        subprocess.run(['find', str(git_dir), '-type', 'f', '-exec', 'chmod', '660', '{}', ';'], check=True)

        log(f"project permissions hook: Set git directory permissions: {project_highest_user}:{project_name} (770/660)")
        return {"status": "completed", "component": "git", "permissions": "770/660", "ownership": f"{project_highest_user}:{project_name}"}

    except Exception as e:
        warn(f"project permissions hook: Failed to set git permissions: {e}")
        report_error("backend", f"project permissions hook: Failed to set git permissions: {e}")
        return {"status": "error", "component": "git", "error": str(e)}
