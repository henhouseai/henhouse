"""
General removal hooks for nginx_flask module (hh_srv category).

Handles pre-validation, file removal, manifest clearing, and render.
"""
import shutil
import configparser
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.render.render import TableData, FieldConfig

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

# Pre-validated configuration storage
pre_validated_config: Optional[dict] = None

def _install_config_path(project_name: str) -> Path:
    return Path(f"/root/.{project_name}-install.cnf")

def _manifest_get_all_sites(project_name: str) -> List[str]:
    """Get all domains from manifest_sites section."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return []
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_sites"):
        return []
    return list(parser.options("manifest_sites"))

def _manifest_clear_all_sites(project_name: str) -> None:
    """Remove all sites from manifest_sites section."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if parser.has_section("manifest_sites"):
        parser.remove_section("manifest_sites")
        with open(cfg_path, 'w') as f:
            parser.write(f)
        os.chmod(cfg_path, 0o600)


@register_module_hook('remove_00_pre_validate', 'Pre-validate removal configuration')
def validate_removal_config() -> Dict[str, Any]:
    """Pre-validate removal configuration and store results for later hooks."""
    global pre_validated_config
    trace_in()

    log("Validating removal configuration")

    # Detect project context
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            break
        current_path = current_path.parent
    else:
        project_name = Path.cwd().name
        current_path = Path.cwd()

    # Load deployment configuration from install config
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Install config not found: {cfg_path}")
        raise ValueError(f"Install config not found: {cfg_path}")

    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        raise ValueError(f"Missing [install] section in {cfg_path}")

    sec = parser["install"]

    # Get NGINX configuration directories
    nginx_sites_available = Path(sec.get("nginx_sites_available", "/etc/nginx/sites-available").strip())
    nginx_sites_enabled = Path(sec.get("nginx_sites_enabled", "/etc/nginx/sites-enabled").strip())

    # Get all deployed sites from manifest
    deployed_domains = _manifest_get_all_sites(project_name)
    log(f"Found {len(deployed_domains)} deployed sites in manifest")

    dest = Path("/srv") / project_name

    # Store the parsed config for access by other hooks
    pre_validated_config = {
        'project_name': project_name,
        'dest': dest,
        'deployed_domains': deployed_domains,
        'nginx_sites_available': nginx_sites_available,
        'nginx_sites_enabled': nginx_sites_enabled,
    }

    log(f"Pre-validated removal config for project: {project_name}")

    return trace_out({
        "project_name": project_name,
        "deployment_path": str(dest),
        "domains_count": len(deployed_domains),
        "domains": deployed_domains
    })


@register_module_hook('remove_30_remove_files', 'Remove deployment files')
def remove_deployment_files() -> Dict[str, Any]:
    """Remove deployment files from /srv/{project}, preserving git folder."""
    trace_in()

    if pre_validated_config is None:
        warn("Pre-validation not completed")
        return trace_out({"status": "skipped", "reason": "no_config"})

    project_name = pre_validated_config['project_name']
    dest = pre_validated_config['dest']

    removed_items = []
    preserved_items = []

    try:
        if dest.exists():
            log(f"Removing deployment files from: {dest}")
            for item in dest.iterdir():
                try:
                    # Preserve git folder
                    if item.name == 'git':
                        log(f"Preserving git folder: {item}")
                        preserved_items.append(str(item))
                        continue

                    if item.is_dir():
                        shutil.rmtree(item)
                        log(f"Removed directory: {item}")
                    else:
                        item.unlink()
                        log(f"Removed file: {item}")
                    removed_items.append(str(item))
                except Exception as e:
                    warn(f"Failed to remove {item}: {e}")

            log(f"Removed {len(removed_items)} items from deployment directory")
        else:
            log(f"Deployment directory does not exist: {dest}")

        return trace_out({
            "status": "completed",
            "component": "remove_files",
            "removed_count": len(removed_items),
            "preserved_count": len(preserved_items),
            "files_removed": True
        })

    except Exception as e:
        warn(f"Failed to remove deployment files: {e}")
        report_error("backend", f"Failed to remove deployment files: {e}")
        return trace_out({"status": "error", "component": "remove_files", "error": str(e)})


@register_module_hook('remove_35_clear_manifest', 'Clear manifest sites')
def clear_manifest_sites() -> Dict[str, Any]:
    """Clear all sites from manifest_sites section."""
    trace_in()

    if pre_validated_config is None:
        warn("Pre-validation not completed")
        return trace_out({"status": "skipped", "reason": "no_config"})

    project_name = pre_validated_config['project_name']

    try:
        _manifest_clear_all_sites(project_name)
        log("Cleared all sites from manifest")

        return trace_out({
            "status": "completed",
            "component": "clear_manifest",
            "manifest_cleared": True
        })

    except Exception as e:
        warn(f"Failed to clear manifest: {e}")
        report_error("backend", f"Failed to clear manifest: {e}")
        return trace_out({"status": "error", "component": "clear_manifest", "error": str(e)})


@register_module_hook('remove_95_render', 'Render server removal status')
def render_srv_removal() -> Dict[str, Any]:
    """Render srv module's removal status (files, manifest)."""
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    table_data = TableData()

    # Get srv-specific data
    files_removed = False
    manifest_cleared = False
    removed_count = 0

    for result in hook_results:
        if result.get('component') == 'remove_files':
            files_removed = result.get('files_removed', False)
            removed_count = result.get('removed_count', 0)
        elif result.get('component') == 'clear_manifest':
            manifest_cleared = result.get('manifest_cleared', False)

    # Summary row
    summary_parts = []
    if files_removed:
        summary_parts.append(f"{removed_count} files removed")
    if manifest_cleared:
        summary_parts.append("manifest cleared")
    summary = ', '.join(summary_parts) if summary_parts else 'No operations'
    table_data.add_row('srv_removal_summary', value=summary)

    field_config = FieldConfig()
    field_config.add_simple(['srv_removal_summary'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }
