"""
hh_nginx module uninstall hooks.

Handles htpasswd file cleanup for tier users and human user.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import is_error
from hh.render.render import TableData, FieldConfig
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.user_accounts import detect_project_owner

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


@register_module_hook('uninstall_40_htpasswd', 'Remove users from htpasswd files')
def remove_htpasswd_entries() -> Dict[str, Any]:
    """Remove tier users and human user from .htpasswd files."""
    trace_in()
    from hh.deploy.uninstall_hooks import UNINSTALL_CONFIG

    project_name = UNINSTALL_CONFIG["project_name"]
    project_path = UNINSTALL_CONFIG["project_path"]

    if is_error():
        return trace_out({"status": "skipped"})

    try:
        # Load htpasswd_dir from install config
        htpasswd_dir = "/var/www"  # Default fallback
        try:
            from hh.deploy.install_helpers_config import load_install_config
            install_config = load_install_config(project_name)
            if install_config:
                htpasswd_dir = install_config.get("htpasswd_dir", "/var/www").strip()
        except Exception:
            pass  # Use default if config can't be loaded

        # Get guest, admin and root tier indices
        guest_idx = HENHOUSE_TIERS.index('guest') if 'guest' in HENHOUSE_TIERS else None
        admin_idx = HENHOUSE_TIERS.index('admin') if 'admin' in HENHOUSE_TIERS else None
        root_idx = HENHOUSE_TIERS.index('root') if 'root' in HENHOUSE_TIERS else None

        htpasswd_removed = []

        # Remove guest tier user (if it exists)
        if guest_idx is not None:
            guest_tier = HENHOUSE_TIERS[guest_idx]
            guest_user = f"{project_name}_{guest_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_{guest_tier}"

            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, guest_user],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {guest_user} from {htpasswd_file}")
                    htpasswd_removed.append(htpasswd_file)
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {guest_user} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {guest_user} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")

        # Remove admin tier user
        if admin_idx is not None:
            admin_tier = HENHOUSE_TIERS[admin_idx]
            admin_user = f"{project_name}_{admin_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_{admin_tier}"

            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, admin_user],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {admin_user} from {htpasswd_file}")
                    htpasswd_removed.append(htpasswd_file)
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {admin_user} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {admin_user} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")

        # Remove root tier user (panel)
        if root_idx is not None:
            root_tier = HENHOUSE_TIERS[root_idx]
            root_user = f"{project_name}_{root_tier}"
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_panel"

            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, root_user],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {root_user} from {htpasswd_file}")
                    htpasswd_removed.append(htpasswd_file)
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {root_user} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {root_user} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")

        # Remove human user from htpasswd_human
        project_owner = detect_project_owner(project_path)
        if project_owner:
            htpasswd_file = f"{htpasswd_dir}/.htpasswd_human"

            if Path(htpasswd_file).exists():
                result = subprocess.run(['htpasswd', '-D', htpasswd_file, project_owner],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"Removed user {project_owner} from {htpasswd_file}")
                    htpasswd_removed.append(htpasswd_file)
                else:
                    if "not found" in result.stderr.lower():
                        log(f"User {project_owner} not found in {htpasswd_file} (may have been already removed)")
                    else:
                        warn(f"Failed to remove user {project_owner} from {htpasswd_file}: {result.stderr}")
            else:
                log(f"{htpasswd_file} does not exist - skipping")

        log(f"hh_nginx: Removed users from {len(htpasswd_removed)} htpasswd file(s)")
        return trace_out({"status": "success", "htpasswd_removed": htpasswd_removed})

    except Exception as e:
        warn(f"Failed to remove users from .htpasswd files: {str(e)}")
        return trace_out({"status": "error", "error": str(e)})


@register_module_hook('uninstall_95_render', 'Render NGINX uninstall summary')
def render_nginx_uninstall_summary() -> Dict[str, Any]:
    """Render NGINX uninstall summary."""
    trace_in()

    # Return empty for now - can add nginx-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
