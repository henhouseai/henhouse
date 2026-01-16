"""
Project deployment hooks for framework project management.
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

# Pre-validated configuration storage for project module
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


