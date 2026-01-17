"""
General deployment helper functions for hh_srv module.

Manifest management and deployment utilities.
"""

import os
import json
import shutil
import subprocess
import configparser
import datetime
from pathlib import Path
from typing import List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.deploy.deploy_utils import load_whitelist_with_extensions
from hh.deploy.conf.context_blacklist import CONTEXT_BLACKLIST
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

try:
    _initialize_debug()
except:
    pass


def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _install_config_path(project_name: str) -> Path:
    return Path(f"/root/.{project_name}-install.cnf")


def _manifest_add_site(project_name: str, domain: str, mode: str) -> None:
    """Add deployed site to manifest with SSL mode."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_sites"):
        parser.add_section("manifest_sites")
    entry = {"domain": domain, "mode": mode, "timestamp": _iso_now()}
    parser.set("manifest_sites", domain, json.dumps(entry, separators=(',', ':')))
    with open(cfg_path, 'w') as f:
        parser.write(f)
    os.chmod(cfg_path, 0o600)


def cleanup_old_deployment() -> None:
    """Remove old deployment files and gateway scripts."""
    # Get project name dynamically
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            break
        current_path = current_path.parent
    else:
        project_name = Path.cwd().name

    users = [f"{project_name}_{tier}" for tier in HENHOUSE_TIERS]

    dest = Path(f'/srv/{project_name}')
    if dest.exists():
        log(f"Removing old deployment: {dest}")
        shutil.rmtree(dest)
    for user in users:
        user_home = Path(f'/home/{user}')
        gateway_script = user_home / 'gateway.py'
        if gateway_script.exists():
            log(f"Removing gateway.py for {user}")
            gateway_script.unlink()
        hh_script = user_home / 'hh'
        if hh_script.exists():
            log(f"Removing hh script for {user}")
            hh_script.unlink()


def deploy_context_folders(source: Path, dest: Path) -> None:
    """Deploy context folders and files for agent visibility."""
    trace_in()
    try:
        log("Deploying context folders and files")

        # Load context whitelist with extension support
        CONTEXT_WHITELIST = load_whitelist_with_extensions('context_whitelist', 'CONTEXT_WHITELIST')

        # Deploy whitelisted context items (folders and files) with blacklist filtering
        for item in CONTEXT_WHITELIST:
            source_item = source / item
            if source_item.exists():
                dest_item = dest / 'context' / item
                if source_item.is_dir():
                    # Handle directories
                    log(f"Deploying context folder: {item} -> context/{item}")
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(source_item, dest_item, ignore=should_ignore_context_path)
                elif source_item.is_file():
                    # Handle files
                    log(f"Deploying context file: {item} -> context/{item}")
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_item, dest_item)
                else:
                    log(f"Context item is neither file nor directory: {item}")
            else:
                log(f"Context item not found: {item}")

        log("Context deployment complete")
    except Exception as e:
        warn(f"Context deployment failed: {str(e)}")
        raise
    finally:
        trace_out()


def should_ignore_context_path(directory: str, files: List[str]) -> List[str]:
    """Determine which files/folders to ignore for context deployment."""
    ignored = []

    for item in files:
        item_path = Path(directory) / item

        # Check if any part of the path matches blacklist
        for blacklist_pattern in CONTEXT_BLACKLIST:
            if matches_blacklist_pattern(item_path, blacklist_pattern):
                ignored.append(item)
                break

    return ignored


def matches_blacklist_pattern(path: Path, pattern: str) -> bool:
    """Check if a path matches a blacklist pattern."""
    # Convert pattern to Path for comparison
    pattern_path = Path(pattern)

    # Check if any part of the path matches
    for part in path.parts:
        if part == pattern_path.name or part == pattern_path.stem:
            return True

    # Check if the full path contains the pattern
    if pattern in str(path):
        return True

    # Check for wildcard patterns
    if '*' in pattern:
        import fnmatch
        if fnmatch.fnmatch(str(path), pattern):
            return True

    return False


def setup_deployment_ownership_and_permissions(project_name: str) -> None:
    """Set ownership and permissions for deployed code."""
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway or not gateway.os:
            warn("Gateway or ProcessManager not available")
            trace_out()
            return

        # Set ownership of deployment directory to project highest level user with deploy group AFTER deployment
        srv_project = Path("/srv") / project_name
        if srv_project.exists():
            try:
                project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
                user_info = gateway.os.get_user_by_name(project_highest_user)
                if not user_info:
                    warn(f"User not found: {project_highest_user}")
                    trace_out()
                    return
                project_highest_uid = user_info["uid"]
                deploy_group_name = f"{project_name}_deploy"
                subprocess.run(['chown', '-R', f'{project_highest_uid}:{deploy_group_name}', str(srv_project)], check=True)

                # Set secure permissions: directories 750, files 640
                subprocess.run(['find', str(srv_project), '-type', 'd', '-exec', 'chmod', '750', '{}', ';'], check=True)
                subprocess.run(['find', str(srv_project), '-type', 'f', '-exec', 'chmod', '640', '{}', ';'], check=True)

                # Fix git directory permissions: owner can write, group can read and write
                git_dir = srv_project / 'git'
                if git_dir.exists():
                    subprocess.run(['chown', '-R', f'{project_highest_uid}:{project_name}', str(git_dir)], check=True)
                    subprocess.run(['find', str(git_dir), '-type', 'd', '-exec', 'chmod', '770', '{}', ';'], check=True)
                    subprocess.run(['find', str(git_dir), '-type', 'f', '-exec', 'chmod', '660', '{}', ';'], check=True)
                    log(f"Set git directory permissions: {project_highest_user}:{project_name} (owner:rw, group:rw)")

                log(f"Set ownership and permissions: {project_highest_user}:{deploy_group_name} (owner:rw, group:r)")
            except Exception as e:
                warn(f"Failed to set ownership and permissions: {str(e)}")
    except Exception as e:
        warn(f"Failed to setup deployment ownership and permissions: {str(e)}")
    finally:
        trace_out()
