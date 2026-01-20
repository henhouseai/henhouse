"""
Git module installation hooks.

Handles git repository initialization and configuration.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
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


@register_module_hook('install_10_conflict_check', 'Check for existing git repository')
def check_git_conflicts() -> Dict[str, Any]:
    """Check for existing git repository."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, _ = detect_project_context()
    if not project_name:
        return trace_out({"status": "error", "error": "Could not detect project name"})

    git_repo = Path(f'/srv/{project_name}/git/{project_name}.git')
    if git_repo.exists():
        error_msg = f"Git repository already exists: {git_repo}"
        warn(f"hh_git: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    log(f"hh_git: No git repository conflicts found")
    return trace_out({"status": "success"})


@register_module_hook('install_40_git', 'Initialize git repository')
def initialize_git_repository() -> Dict[str, Any]:
    """Initialize bare git repository and set up project git."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context
    from hh.deploy.users.user_accounts import detect_project_owner

    project_name, project_path = detect_project_context()
    if not project_name or not project_path:
        error_msg = "Could not detect project name or path"
        warn(f"hh_git: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    gateway = get_gateway()
    if not gateway or not gateway.files:
        error_msg = "No gateway or files interface available"
        warn(f"hh_git: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        log("hh_git: Setting up git repository")

        # Create /srv/{project_name}/git directory
        srv_project = Path(f'/srv/{project_name}')
        srv_project.mkdir(parents=True, exist_ok=True)

        git_dir = srv_project / 'git'
        git_dir.mkdir(parents=True, exist_ok=True)

        # Create bare git repository
        bare_repo = git_dir / f"{project_name}.git"
        if bare_repo.exists():
            shutil.rmtree(bare_repo)

        subprocess.run(['git', 'init', '--bare', str(bare_repo)], check=True)
        log(f"hh_git: Created bare git repository: {bare_repo}")

        # Configure Git safe.directory
        try:
            subprocess.run(['git', 'config', '--system', '--add', 'safe.directory', str(bare_repo)], check=True)
            log(f"hh_git: Configured Git safe.directory for {bare_repo}")
        except subprocess.CalledProcessError as e:
            warn(f"hh_git: Failed to set Git safe.directory (non-fatal): {e}")

        # Set ownership to project owner
        project_owner = detect_project_owner(project_path)
        if not project_owner:
            raise Exception("Failed to detect project owner")

        gateway.files.chown(str(srv_project), project_owner, group=project_name, recursive=True)
        log(f"hh_git: Set git repository ownership to {project_owner}:{project_name}")

        # Set proper permissions
        gateway.files.chmod_tree(str(bare_repo), dir_mode=0o770, file_mode=0o660)

        # Initialize git in project directory if not already a repo
        if not (project_path / '.git').exists():
            log(f"hh_git: Initializing git repository in {project_path}")
            subprocess.run(['git', 'init'], cwd=str(project_path), check=True)

            # Configure git user
            subprocess.run(['git', 'config', 'user.name', f'{project_name} System'], cwd=str(project_path), check=True)
            subprocess.run(['git', 'config', 'user.email', f'system@{project_name}.local'], cwd=str(project_path), check=True)

            # Add all files
            subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True)

            # Initial commit
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=str(project_path), check=True)

            # Rename branch to project_name
            subprocess.run(['git', 'branch', '-m', project_name], cwd=str(project_path), check=True)

        # Check if there are any commits
        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], cwd=str(project_path), capture_output=True, text=True)
        commit_count = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else 0

        if commit_count == 0:
            log(f"hh_git: No commits found in {project_path}, creating initial commit")
            try:
                subprocess.run(['git', 'config', 'user.name', f'{project_name} System'], cwd=str(project_path), check=True)
                subprocess.run(['git', 'config', 'user.email', f'system@{project_name}.local'], cwd=str(project_path), check=True)
            except subprocess.CalledProcessError:
                pass

            subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=str(project_path), check=True)

            try:
                subprocess.run(['git', 'branch', '-m', project_name], cwd=str(project_path), check=True)
            except subprocess.CalledProcessError:
                pass

        # Add the bare repo as remote
        try:
            subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=str(project_path), check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass
        subprocess.run(['git', 'remote', 'add', 'origin', str(bare_repo)], cwd=str(project_path), check=True)

        # Push to bare repo
        subprocess.run(['git', 'push', 'origin', project_name], cwd=str(project_path), check=True)
        log(f"hh_git: Pushed project code to {bare_repo} ({project_name} branch)")

        # Set HEAD in bare repository
        subprocess.run(['git', 'symbolic-ref', 'HEAD', f'refs/heads/{project_name}'], cwd=str(bare_repo), check=True)
        log(f"hh_git: Set bare repository HEAD to {project_name} branch")

        # Fix ownership of entire project folder
        if project_owner and gateway.files:
            try:
                gateway.files.chown(str(project_path), project_owner, group=project_name, recursive=True)
                gateway.files.chmod_tree(str(project_path), dir_mode=0o2750)
                log(f"hh_git: Fixed entire project ownership to {project_owner}:{project_name} with setgid")
            except Exception as e:
                warn(f"hh_git: Failed to fix project ownership: {str(e)}")

        return trace_out({
            "status": "success",
            "bare_repo": str(bare_repo),
            "project_path": str(project_path),
            "owner": project_owner
        })

    except Exception as e:
        error_msg = f"Failed to initialize git repository: {str(e)}"
        warn(f"hh_git: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_95_render', 'Render git summary')
def render_git_summary() -> Dict[str, Any]:
    """Render git repository summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - can add git-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
