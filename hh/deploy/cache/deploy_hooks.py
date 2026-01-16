"""
Cache deployment hooks for framework cache management.
"""

import subprocess
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.cache.deploy_helpers_cache import render_cache_operations, set_cache_permissions, set_cache_base_permissions, cleanup_cache_files

log = lambda message: None
warn = lambda message: None

def _init_debug():
    global log, warn
    log = get_log(True)
    warn = get_warn(True)

try:
    _init_debug()
except:
    pass

# Pre-validated configuration storage for cache module
pre_validated_cache_config: dict = {}

@register_module_hook('deploy_pre_validate')
def validate_cache_config():
    """Pre-validate cache-specific configuration."""
    global pre_validated_cache_config

    log("Validating cache deployment configuration")

    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            raise ValueError("Could not detect project context")

        # Validate cache directories exist or can be created
        from hh.deploy.cache.cache_cleanup_registry import get_cache_directories
        cache_dirs = get_cache_directories()

        pre_validated_cache_config = {
            'project_name': project_name,
            'current_path': current_path,
            'cache_directories': cache_dirs
        }

        log(f"Pre-validated cache config for: {project_name}")
    except Exception as e:
        warn(f"Failed to validate cache config: {e}")
        raise ValueError(f"Failed to validate cache config: {e}")


# Hook functions are now imported from deploy_helpers_cache.py





# All hook functions are now imported from deploy_helpers_cache.py