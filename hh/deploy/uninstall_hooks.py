"""
Core uninstall hooks with UNINSTALL_CONFIG global.

This module contains the global UNINSTALL_CONFIG that other modules can import and contribute to.
"""

import configparser
import datetime
from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error
from hh.deploy.user_accounts import detect_project_owner
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path
from hh.deploy.uninstall_helpers_user_env import cleanup_user_entry_points

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

# INTENTIONALLY CROSS-CUTTABLE GLOBAL
# Other modules import and read this during uninstall execution
UNINSTALL_CONFIG: Dict[str, Any] = {
    "project_name": "",
    "project_path": None,
    "config_path": None,
    "entry_point_script_name": "",
    "removed_project_users": [],  # Track which project users were actually removed
}

# Module-scoped config storage for core settings
core_config: Dict[str, Any] = {}


def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@register_module_hook('uninstall_00_pre_validate', 'Detect uninstall context and validate')
def validate_uninstall_context() -> Dict[str, Any]:
    """Detect project context, check for deployed sites, and load config."""
    trace_in()

    project_name, project_path = detect_project_context()
    if not project_name:
        error_msg = "Could not detect project name"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    cfg_path = get_install_config_path(project_name)

    UNINSTALL_CONFIG["project_name"] = project_name
    UNINSTALL_CONFIG["project_path"] = project_path
    UNINSTALL_CONFIG["config_path"] = cfg_path

    # Block uninstall if manifest lists deployed sites
    if cfg_path.exists():
        try:
            parser = configparser.ConfigParser()
            parser.read(cfg_path)
            if parser.has_section("manifest_sites"):
                sites = [item[0] for item in parser.items("manifest_sites")]
                if sites:
                    error_msg = f"Manifest shows deployed sites: {', '.join(sites)}. Remove them with: http_remove -domain <domain>, then rerun uninstall."
                    warn(error_msg)
                    report_error("action", error_msg)
                    return trace_out({"status": "error", "error": error_msg})
        except Exception as e:
            error_msg = f"Could not read manifest_sites: {e}"
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

    # Get entry point script name from install config - REQUIRED, no fallback
    if not cfg_path.exists():
        error_msg = f"Install config not found: {cfg_path}. Cannot determine script name."
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        if not parser.has_section("install"):
            error_msg = f"Missing [install] section in {cfg_path}. Cannot determine script name."
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

        entry_point_script_name = parser.get("install", "entry_point_script_name", fallback=None)
        if not entry_point_script_name:
            error_msg = f"entry_point_script_name not found in install config: {cfg_path}. Cannot determine script name."
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

        entry_point_script_name = entry_point_script_name.strip()
        if not entry_point_script_name:
            error_msg = f"entry_point_script_name is empty in install config: {cfg_path}. Cannot determine script name."
            warn(error_msg)
            report_error("action", error_msg)
            return trace_out({"status": "error", "error": error_msg})

        UNINSTALL_CONFIG["entry_point_script_name"] = entry_point_script_name
        core_config["entry_point_script_name"] = entry_point_script_name
        log(f"Using entry point script name from install config: {entry_point_script_name}")
    except Exception as e:
        error_msg = f"Could not read entry_point_script_name from install config: {e}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    log(f"Uninstall context validated for {project_name}")
    return trace_out({"status": "success", "project_name": project_name})


@register_module_hook('uninstall_50_user_env', 'Clean up human and root user environments')
def cleanup_user_environments() -> Dict[str, Any]:
    """Clean up human user and root user home directories."""
    trace_in()

    project_name = UNINSTALL_CONFIG["project_name"]
    project_path = UNINSTALL_CONFIG["project_path"]
    entry_point_script_name = core_config.get("entry_point_script_name")
    removed_project_users = UNINSTALL_CONFIG.get("removed_project_users", [])

    # Only do this if we actually removed at least one project user (safety check)
    if not removed_project_users:
        log("No project users were removed - skipping human/root script cleanup for safety")
        warn("Skipping human/root script cleanup - no project users were found/removed. This prevents accidental deletion of scripts from other projects.")
        return trace_out({"status": "skipped"})

    log(f"Removed {len(removed_project_users)} project user(s) - proceeding with human/root script cleanup")

    human_scripts_removed = []
    root_scripts_removed = []

    try:
        # Detect project owner (human user)
        project_owner = detect_project_owner(project_path)
        if project_owner:
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

            # Check what human scripts were removed
            if entry_point_script_name:
                human_home = Path(f'/home/{project_owner}')
                entry_point_script = human_home / entry_point_script_name
                if not entry_point_script.exists():
                    human_scripts_removed.append(f"/home/{project_owner}/{entry_point_script_name}")
        else:
            log("No project owner detected - skipping human user home cleanup")

        # Clean up root user entry points
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

        # Check what root scripts were removed
        if entry_point_script_name:
            root_home = Path('/root')
            root_entry_point_script = root_home / entry_point_script_name
            if not root_entry_point_script.exists():
                root_scripts_removed.append(f"/root/{entry_point_script_name}")

        log("hh core: Human and root user environments cleaned")
        return trace_out({
            "status": "success",
            "human_scripts_removed": human_scripts_removed,
            "root_scripts_removed": root_scripts_removed
        })

    except Exception as e:
        error_msg = f"Failed to cleanup user environments: {str(e)}"
        warn(error_msg)
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('uninstall_65_cache_cleanup', 'Clean all caches')
def clean_caches() -> Dict[str, Any]:
    """Clear registry cache to prevent permission issues."""
    trace_in()

    try:
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        clean_all_caches()

        log("hh core: Caches cleaned")
        return trace_out({"status": "success"})

    except Exception as e:
        error_msg = f"Failed to clean caches: {str(e)}"
        warn(error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('uninstall_95_render', 'Render uninstall summary')
def render_uninstall_summary() -> Dict[str, Any]:
    """Render uninstall summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - parser will aggregate from all modules
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
