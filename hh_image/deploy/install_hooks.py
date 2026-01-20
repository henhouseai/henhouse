"""
Image module installation hooks.

Handles image directory setup.
"""

from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
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


@register_module_hook('install_55_media_dirs', 'Create /srv/images directory structure')
def create_images_directory() -> Dict[str, Any]:
    """Set up images directory with proper permissions during installation."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, _ = detect_project_context()
    if not project_name:
        return trace_out({"status": "error", "error": "Could not detect project name"})

    gateway = get_gateway()
    if not gateway or not gateway.files:
        error_msg = "No gateway or files interface available"
        warn(f"hh_image: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        log(f"hh_image: Setting up images directory for project {project_name}")

        # Create /srv/images/{project_name} directory
        images_dir = Path(f'/srv/images/{project_name}')
        images_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(images_dir), 0o2775)
        log(f"hh_image: Created images directory with group write: {images_dir}")

        # Create deleted subdirectory
        deleted_dir = images_dir / 'deleted'
        deleted_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(deleted_dir), 0o2775)
        log(f"hh_image: Created deleted subdirectory: {deleted_dir}")

        # Set ownership for images directory and subdirectories
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        admin_group_name = f"{project_name}_admin"
        gateway.files.chown(str(images_dir), project_highest_user, group=admin_group_name, recursive=True)
        log(f"hh_image: Set images directory ownership: {project_highest_user}:{admin_group_name}")

        log("hh_image: Images directory setup completed successfully")

        return trace_out({
            "status": "success",
            "directory": str(images_dir),
            "owner": f"{project_highest_user}:{admin_group_name}"
        })

    except Exception as e:
        error_msg = f"Failed to setup images directory: {str(e)}"
        warn(f"hh_image: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_95_render', 'Render image module summary')
def render_images_summary() -> Dict[str, Any]:
    """Render image module summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - can add image-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
