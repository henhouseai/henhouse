"""
Project deployment hooks for framework project management.
"""

import subprocess
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.project.deploy_helpers_project import validate_project_config, set_project_permissions, preserve_git_state, restore_git_state, deploy_project_modules, cleanup_project_framework

# All hook functions are now imported from deploy_helpers_project.py