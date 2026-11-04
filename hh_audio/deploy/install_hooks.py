"""
Audio module installation hooks.

Handles audio directory setup.
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


@register_module_hook('install_55_media_dirs', 'Create /srv/audio directory structure')
def create_audio_directory() -> Dict[str, Any]:
    """Set up audio directory with proper permissions during installation."""
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, _ = detect_project_context()
    if not project_name:
        return trace_out({"status": "error", "error": "Could not detect project name"})

    gateway = get_gateway()
    if not gateway or not gateway.files:
        error_msg = "No gateway or files interface available"
        warn(f"audio: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})

    try:
        log(f"audio: Setting up audio directory for project {project_name}")

        # Create /srv/audio/{project_name} directory
        audio_dir = Path(f'/srv/audio/{project_name}')
        audio_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(audio_dir), 0o2775)
        log(f"audio: Created audio directory with group write: {audio_dir}")

        # Create deleted subdirectory
        deleted_dir = audio_dir / 'deleted'
        deleted_dir.mkdir(parents=True, exist_ok=True)
        gateway.files.chmod(str(deleted_dir), 0o2775)
        log(f"audio: Created deleted subdirectory: {deleted_dir}")

        # Set ownership for audio directory and subdirectories
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        admin_group_name = f"{project_name}_admin"
        gateway.files.chown(str(audio_dir), project_highest_user, group=admin_group_name, recursive=True)
        log(f"audio: Set audio directory ownership: {project_highest_user}:{admin_group_name}")

        log("audio: Audio directory setup completed successfully")

        return trace_out({
            "status": "success",
            "directory": str(audio_dir),
            "owner": f"{project_highest_user}:{admin_group_name}"
        })

    except Exception as e:
        error_msg = f"Failed to setup audio directory: {str(e)}"
        warn(f"audio: {error_msg}")
        report_error("action", error_msg)
        return trace_out({"status": "error", "error": error_msg})


@register_module_hook('install_95_render', 'Render audio module summary')
def render_audio_summary() -> Dict[str, Any]:
    """Render audio module summary."""
    trace_in()
    from hh.render.render import TableData, FieldConfig

    # Return empty for now - can add audio-specific rendering later
    table_data = TableData()
    field_config = FieldConfig()

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })
