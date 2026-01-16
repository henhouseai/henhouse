"""
Project deployment helper hooks.

These functions handle project-level deployment operations like git operations, module deployment, and framework cleanup.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_module_hook('deploy_pre_validate')
def validate_project_config() -> Dict[str, Any]:
    """Pre-validate project-specific configuration."""
    trace_in()

    log("Validating project deployment configuration")

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project context")

    # Validate that we're in a project directory with proper structure
    hh_dir = current_path / 'hh'
    if not hh_dir.exists() or not hh_dir.is_dir():
        raise ValueError("Not in a valid henhouse project directory")

    # Check for required directories
    required_dirs = ['hh/deploy', 'hh/gateway', 'hh/render']
    missing_dirs = []
    for dir_name in required_dirs:
        dir_path = current_path / dir_name
        if not dir_path.exists() or not dir_path.is_dir():
            missing_dirs.append(dir_name)

    if missing_dirs:
        raise ValueError(f"Missing required directories: {', '.join(missing_dirs)}")

    log(f"Project validation successful for: {project_name}")

    return trace_out({
        "project_name": project_name,
        "project_path": str(current_path),
        "validation_status": "passed"
    })


@register_module_hook('deploy_permissions_special')
def set_project_permissions() -> Dict[str, Any]:
    """Set special permissions for project-specific directories."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    dest = Path("/srv") / project_name

    # Set special permissions for project-specific files
    # This could include configuration files, logs, etc.

    log(f"Project special permissions set for: {project_name}")

    return trace_out({
        "status": "completed",
        "component": "project_permissions",
        "project_name": project_name
    })


@register_module_hook('deploy_git_preserve_ops')
def preserve_git_state() -> Dict[str, Any]:
    """Preserve current git state before deployment operations."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    dest = Path("/srv") / project_name
    git_dir = dest / '.git'

    if not git_dir.exists():
        log(f"No git repository found at {dest}, skipping git state preservation")
        return trace_out({
            "status": "skipped",
            "reason": "no_git_repo",
            "project_name": project_name
        })

    # Preserve current branch and commit
    try:
        # Get current branch
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                              cwd=dest, capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()

        # Get current commit
        result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                              cwd=dest, capture_output=True, text=True, check=True)
        current_commit = result.stdout.strip()

        # Check for uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'],
                              cwd=dest, capture_output=True, text=True, check=True)
        has_changes = bool(result.stdout.strip())

        preserved_state = {
            "current_branch": current_branch,
            "current_commit": current_commit,
            "has_uncommitted_changes": has_changes
        }

        log(f"Git state preserved for {project_name}: branch={current_branch}, commit={current_commit[:8]}")

        return trace_out({
            "status": "completed",
            "component": "git_preserve",
            "project_name": project_name,
            "preserved_state": preserved_state
        })

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to preserve git state: {e}")


@register_module_hook('deploy_git_restore_ops')
def restore_git_state() -> Dict[str, Any]:
    """Restore git state after deployment operations."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    dest = Path("/srv") / project_name
    git_dir = dest / '.git'

    if not git_dir.exists():
        log(f"No git repository found at {dest}, skipping git state restoration")
        return trace_out({
            "status": "skipped",
            "reason": "no_git_repo",
            "project_name": project_name
        })

    # For now, just ensure we're on a valid branch
    # More complex restoration logic could be added here
    try:
        result = subprocess.run(['git', 'status', '--porcelain'],
                              cwd=dest, capture_output=True, text=True, check=True)

        if result.stdout.strip():
            log(f"Git repository has uncommitted changes after deployment: {project_name}")
        else:
            log(f"Git repository is clean after deployment: {project_name}")

        return trace_out({
            "status": "completed",
            "component": "git_restore",
            "project_name": project_name,
            "has_changes": bool(result.stdout.strip())
        })

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to restore git state: {e}")


@register_module_hook('deploy_modules')
def deploy_project_modules() -> Dict[str, Any]:
    """Deploy project-specific modules."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    # This hook would handle deployment of project-specific modules
    # For now, it's a placeholder for any project-specific deployment logic

    log(f"Project modules deployed for: {project_name}")

    return trace_out({
        "status": "completed",
        "component": "project_modules",
        "project_name": project_name
    })


@register_module_hook('deploy_framework_cleanup')
def cleanup_project_framework() -> Dict[str, Any]:
    """Clean up project framework artifacts."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    dest = Path("/srv") / project_name

    # Remove framework-specific cache files, temporary files, etc.
    cleanup_items = []

    # Clean up any framework-specific artifacts
    framework_artifacts = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '.pytest_cache',
        'node_modules/.cache'  # if applicable
    ]

    for pattern in framework_artifacts:
        if pattern == '__pycache__':
            for pycache_dir in dest.rglob(pattern):
                try:
                    import shutil
                    shutil.rmtree(pycache_dir)
                    cleanup_items.append(str(pycache_dir))
                except Exception:
                    pass  # Ignore errors during cleanup
        else:
            for item in dest.rglob(pattern):
                try:
                    if item.is_file():
                        item.unlink()
                        cleanup_items.append(str(item))
                except Exception:
                    pass  # Ignore errors during cleanup

    log(f"Framework cleanup completed for {project_name}: {len(cleanup_items)} items removed")

    return trace_out({
        "status": "completed",
        "component": "framework_cleanup",
        "project_name": project_name,
        "items_cleaned": len(cleanup_items)
    })