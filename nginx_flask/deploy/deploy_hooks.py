"""
NGINX/Flask deployment hooks
"""
import os
import subprocess
from typing import Dict, Any, List
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
# Import hooks directly from helper files (they are now decorated hooks)
from nginx_flask.deploy.deploy_helpers_render import render_nginx_flask_summary, render_nginx_domain_table
from nginx_flask.deploy.deploy_helpers_flask import stop_flask_daemons, restart_flask_daemons, deploy_flask_apps
from nginx_flask.deploy.deploy_helpers_permissions import set_flask_logs_permissions, set_site_permissions
from nginx_flask.deploy.deploy_helpers_site import prepare_site_directory, deploy_site_css, deploy_site_js, deploy_site_misc
from nginx_flask.deploy.deploy_helpers_directory import sterilize_deployment_directory
from nginx_flask.deploy.deploy_helpers_clients import deploy_client_files
from nginx_flask.deploy.deploy_helpers_context import deploy_context
from nginx_flask.deploy.deploy_helpers_nginx import deploy_nginx_and_ssl



# Pre-validated configuration storage for nginx_flask module
pre_validated_whitelists: Dict[str, List[str]] = {}

@register_module_hook('deploy_pre_validate')
def validate_nginx_flask_config():
    """Pre-validate NGINX/Flask specific configuration including whitelists."""
    from hh.gateway.registry.debug import get_log, get_warn

    log = get_log(True)
    warn = get_warn(True)

    global pre_validated_whitelists

    log("Validating NGINX/Flask deployment configuration")

    from hh.deploy.deploy_utils import load_whitelist_with_extensions

    # Load whitelists that will be used by site deployment hooks
    try:
        pre_validated_whitelists['JS_WHITELIST'] = load_whitelist_with_extensions('js_whitelist', 'JS_WHITELIST')
        pre_validated_whitelists['CSS_WHITELIST'] = load_whitelist_with_extensions('css_whitelist', 'CSS_WHITELIST')
        pre_validated_whitelists['JS_PAGE_CLASSES_WHITELIST'] = load_whitelist_with_extensions('js_page_classes_whitelist', 'JS_PAGE_CLASSES_WHITELIST')
        pre_validated_whitelists['MISC_WHITELIST'] = load_whitelist_with_extensions('misc_whitelist', 'MISC_WHITELIST')

        log("Pre-validated NGINX/Flask whitelists")
    except Exception as e:
        warn(f"Failed to load NGINX/Flask whitelists: {e}")
        raise ValueError(f"Failed to load NGINX/Flask whitelists: {e}")


# All hook functions are now directly imported from helper files
