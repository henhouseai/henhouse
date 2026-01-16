import os
import shutil
import subprocess
import json
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

from hh.deploy.cache.cache_cleanup_registry import get_cache_directories
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from nginx_flask.deploy.ssl_helpers import ensure_certificate_exists
from nginx_flask.deploy.nginx_helpers import (
    get_server_ip,
    create_nginx_ssl_config_local,
    create_nginx_config_local,
    install_nginx_ssl_config,
    install_nginx_config,
    create_local_decoy,
    check_nginx_status
)
from hh.deploy.http.deploy_helpers import _manifest_add_site, should_ignore_context_path

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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.conf.context_blacklist import CONTEXT_BLACKLIST
from hh.deploy.deploy_utils import (
    load_whitelist_with_extensions,
)
from hh.gateway.registry.module_hooks import run_hooks

from hh.deploy.conf.deploy_whitelist import (
    FLASK_APP_SOURCE,
    MEDIA_SERVER_SOURCE,
    MAINTENANCE_APP_SOURCE,
)

@register_action('deploy')
@register_command('deploy')
def deploy() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Check if running in deployed Unix environment with privileges
    if not gateway.os or not gateway.os.require_privileged():
        trace_out()
        return False

    # Initialize hook results collection
    hook_results: List[Dict[str, Any]] = []

    # Initialize legacy permission variables for backward compatibility
    ownership_set = False
    cache_permissions_set = False
    logs_permissions_set = False

    # Pre-deployment validation hooks - each module validates its own config
    if not is_error():
        try:
            log("Running pre-deployment validation hooks")
            results = run_hooks('deploy_pre_validate')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Pre-deployment validation hooks failed: {e}")
            report_error("backend", f"Pre-deployment validation hooks failed: {e}")

    # Access pre-validated configuration from hooks
    from .deploy_hooks import pre_validated_config
    if pre_validated_config is None:
        warn("Pre-validation not completed - configuration not available")
        report_error("backend", "Pre-validation not completed - configuration not available")
        trace_out()
        return False

    # Extract validated config values
    project_name = pre_validated_config['project_name']
    current_path = pre_validated_config['current_path']
    source = pre_validated_config['source']
    start_port = pre_validated_config['start_port']
    domain = pre_validated_config['domain']
    ssl_enabled = pre_validated_config['ssl_enabled']
    ssl_cert_dir_letsencrypt = pre_validated_config['ssl_cert_dir_letsencrypt']
    ssl_cert_dir_self_signed = pre_validated_config['ssl_cert_dir_self_signed']
    local_allow_block = pre_validated_config['local_allow_block']
    nginx_sites_available = pre_validated_config['nginx_sites_available']
    nginx_sites_enabled = pre_validated_config['nginx_sites_enabled']
    certificate_path = pre_validated_config['certificate_path']
    is_local = pre_validated_config['is_local']

    # Load whitelists with extension support (moved from pre-validation for backward compatibility)
    CONTEXT_WHITELIST = load_whitelist_with_extensions('context_whitelist', 'CONTEXT_WHITELIST')
    HH_DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'HH_DEPLOY_WHITELIST')
    EXT_DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'EXT_DEPLOY_WHITELIST')
    HH_EXTRA_DEPLOY_FILES = load_whitelist_with_extensions('deploy_whitelist', 'HH_EXTRA_DEPLOY_FILES')
    EXT_EXTRA_DEPLOY_FILES = load_whitelist_with_extensions('deploy_whitelist', 'EXT_EXTRA_DEPLOY_FILES')
    dest = Path("/srv") / project_name
    log(f"Deploying from {source} to {dest} (starting port: {start_port}, domain: {domain}, local: {is_local})")

    # Git preservation hooks
    if not is_error():
        try:
            log("Running git preservation hooks")
            results = run_hooks('deploy_git_preserve')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Git preservation hooks failed: {e}")
            report_error("backend", f"Git preservation hooks failed: {e}")

    # Stop running daemons prior to deployment
    if not is_error():
        try:
            log("Running daemon stop hooks")
            results = run_hooks('deploy_stop_daemons')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Daemon stop hooks failed: {e}")
            report_error("backend", f"Daemon stop hooks failed: {e}")

    # Git preservation operations
    if not is_error():
        try:
            log("Running git preservation operations hooks")
            results = run_hooks('deploy_git_preserve_ops')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Git preservation operations hooks failed: {e}")
            report_error("backend", f"Git preservation operations hooks failed: {e}")

    # Directory sterilization hooks
    if not is_error():
        try:
            log("Running directory sterilization hooks")
            results = run_hooks('deploy_sterilize_directory')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Directory sterilization hooks failed: {e}")
            report_error("backend", f"Directory sterilization hooks failed: {e}")

    # Sterilize deployment directory (remove everything except preserved git)
    if not is_error():
        try:
            if dest.exists():
                # Remove all contents
                for item in dest.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        log(f"Removed: {item}")
                    except Exception as e:
                        warn(f"Failed to remove {item}: {e}")
                log(f"Sterilized deployment directory: {dest}")
            else:
                dest.mkdir(parents=True, exist_ok=True)
                log(f"Created deployment directory: {dest}")
        except Exception as e:
            warn(f"Failed to sterilize deployment directory: {e}")
            report_error("backend", f"Failed to sterilize deployment directory: {e}")

    # Git restoration operations
    if not is_error():
        try:
            log("Running git restoration operations hooks")
            results = run_hooks('deploy_git_restore_ops')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Git restoration operations hooks failed: {e}")
            report_error("backend", f"Git restoration operations hooks failed: {e}")

    # Clean up git_preserved flag

    # Code deployment hooks
    if not is_error():
        try:
            log("Running code deployment hooks")
            results = run_hooks('deploy_code')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Code deployment hooks failed: {e}")
            report_error("backend", f"Code deployment hooks failed: {e}")

    # Deploy main code
    if not is_error():
        hh_source = source / 'hh'
        hh_dest = dest / 'hh'
        code_deployed = False
        try:
            shutil.copytree(hh_source, hh_dest)
            code_deployed = True
            log(f"Deployed code: {hh_source} -> {hh_dest}")
        except Exception as e:
            warn(f"Failed to deploy code: {e}")
            report_error("backend", f"Failed to deploy code: {e}")

    # Deploy ext folder (if it exists)
    if not is_error():
        ext_source = source / 'ext'
        ext_dest = dest / 'ext'
        ext_code_deployed = False
        try:
            if ext_source.exists() and ext_source.is_dir():
                shutil.copytree(ext_source, ext_dest)
                ext_code_deployed = True
                log(f"Deployed ext code: {ext_source} -> {ext_dest}")
            else:
                log("Ext folder not found, skipping ext deployment")
        except Exception as e:
            warn(f"Failed to deploy ext code: {e}")
            report_error("backend", f"Failed to deploy ext code: {e}")

    # Ext cleanup hooks
    if not is_error():
        try:
            log("Running ext cleanup hooks")
            results = run_hooks('deploy_ext_cleanup')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Ext cleanup hooks failed: {e}")
            report_error("backend", f"Ext cleanup hooks failed: {e}")

    # Clean ext/deploy directory but preserve whitelisted items (if ext/ was deployed)
    if not is_error() and ext_code_deployed:
        ext_deploy_dir = dest / 'ext' / 'deploy'
        ext_preserved_items = {}  # Map of item_name -> (source_path, temp_path)
        ext_deployment_cleaned = False
        try:
            if ext_deploy_dir.exists():
                # Temporarily move whitelisted items out
                for item_name in EXT_DEPLOY_WHITELIST:
                    item_path = ext_deploy_dir / item_name
                    if item_path.exists():
                        temp_path = dest / f".{project_name}_ext_{item_name.replace('/', '_').replace('.', '_')}_tmp"
                        
                        # Clean up existing temp if it exists
                        if temp_path.exists():
                            if temp_path.is_dir():
                                shutil.rmtree(temp_path)
                            else:
                                temp_path.unlink()
                        
                        # Move item to temp location
                        shutil.move(str(item_path), str(temp_path))
                        ext_preserved_items[item_name] = (item_path, temp_path)
                        log(f"Temporarily moved ext/{item_name}: {item_path} -> {temp_path}")

                # Remove entire ext/deploy directory contents
                shutil.rmtree(ext_deploy_dir)
                log(f"Removed ext/deploy directory: {ext_deploy_dir}")

                # Recreate ext/deploy directory and restore preserved items
                ext_deploy_dir.mkdir(parents=True, exist_ok=True)
                for item_name, (original_path, temp_path) in ext_preserved_items.items():
                    if temp_path.exists():
                        restored_path = ext_deploy_dir / item_name
                        shutil.move(str(temp_path), str(restored_path))
                        log(f"Restored ext/{item_name}: {restored_path}")

                ext_deployment_cleaned = True
            else:
                log("ext/deploy directory not found, skipping ext/deploy cleanup")
        except Exception as e:
            warn(f"Failed to clean ext/deploy directory while preserving whitelisted items: {e}")
            report_error("backend", f"Failed to clean ext/deploy directory while preserving whitelisted items: {e}")

    # Module deployment hooks
    if not is_error():
        try:
            log("Running module deployment hooks")
            results = run_hooks('deploy_modules')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Module deployment hooks failed: {e}")
            report_error("backend", f"Module deployment hooks failed: {e}")

    # Deploy discovered peer modules
    if not is_error():
        try:
            from hh.deploy.deploy_utils import get_active_modules
            modules = get_active_modules()
            deployed_modules = []
            for module in modules:
                module_source = source / module.path
                module_dest = dest / module.path
                try:
                    if module_source.exists() and module_source.is_dir():
                        shutil.copytree(module_source, module_dest)
                        deployed_modules.append(module)
                        log(f"Deployed module {module.name}: {module_source} -> {module_dest}")
                    else:
                        warn(f"Module source not found: {module_source}")
                except Exception as e:
                    warn(f"Failed to deploy module {module.name}: {e}")
                    report_error("backend", f"Failed to deploy module {module.name}: {e}")

            # Clean each deployed module's deploy directory but preserve whitelisted items
            for module in deployed_modules:
                module_deploy_dir = dest / module.path / 'deploy'
                if module_deploy_dir.exists():
                    # Load module's deploy whitelist
                    module_whitelist = []
                    try:
                        module_whitelist_path = module_deploy_dir / 'conf' / 'deploy_whitelist.py'
                        if module_whitelist_path.exists():
                            # Execute the module's whitelist file in a controlled namespace
                            namespace: dict = {}
                            exec(module_whitelist_path.read_text(), namespace)
                            module_whitelist = namespace.get('MODULE_DEPLOY_WHITELIST', [])
                            log(f"Loaded whitelist for module {module.name}: {module_whitelist}")
                        else:
                            log(f"No whitelist file found for module {module.name}: {module_whitelist_path}")
                    except Exception as e:
                        warn(f"Failed to load whitelist for module {module.name}: {e}")

                    # Preserve whitelisted items
                    preserved_items = {}
                    try:
                        for item_name in module_whitelist:
                            item_path = module_deploy_dir / item_name
                            if item_path.exists():
                                temp_path = dest / f".{project_name}_{module.name}_{item_name.replace('/', '_').replace('.', '_')}_tmp"

                                # Clean up existing temp if it exists
                                if temp_path.exists():
                                    if temp_path.is_dir():
                                        shutil.rmtree(temp_path)
                                    else:
                                        temp_path.unlink()

                                # Move item to temp location
                                shutil.move(str(item_path), str(temp_path))
                                preserved_items[item_name] = (item_path, temp_path)
                                log(f"Temporarily moved {module.name}/{item_name}: {item_path} -> {temp_path}")

                        # Remove entire module/deploy directory contents
                        shutil.rmtree(module_deploy_dir)
                        log(f"Removed {module.name}/deploy directory: {module_deploy_dir}")

                        # Recreate module/deploy directory and restore preserved items
                        module_deploy_dir.mkdir(parents=True, exist_ok=True)
                        for item_name, (original_path, temp_path) in preserved_items.items():
                            if temp_path.exists():
                                restored_path = module_deploy_dir / item_name
                                shutil.move(str(temp_path), str(restored_path))
                                log(f"Restored {module.name}/{item_name}: {restored_path}")

                        log(f"Cleaned {module.name}/deploy directory while preserving whitelisted items")
                    except Exception as e:
                        warn(f"Failed to clean {module.name}/deploy directory: {e}")
                        report_error("backend", f"Failed to clean {module.name}/deploy directory: {e}")
        except Exception as e:
            warn(f"Error deploying modules: {e}")
            report_error("backend", f"Error deploying modules: {e}")

    # Framework cleanup hooks
    if not is_error():
        try:
            log("Running framework cleanup hooks")
            results = run_hooks('deploy_framework_cleanup')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Framework cleanup hooks failed: {e}")
            report_error("backend", f"Framework cleanup hooks failed: {e}")

    # Clean deployment directory but preserve whitelisted items
    if not is_error():
        deploy_dir = dest / 'hh' / 'deploy'
        preserved_items = {}  # Map of item_name -> (source_path, temp_path)
        deployment_cleaned = False
        try:
            # Temporarily move whitelisted items out
            for item_name in HH_DEPLOY_WHITELIST:
                item_path = deploy_dir / item_name
                if item_path.exists():
                    temp_path = dest / f".{project_name}_{item_name.replace('/', '_').replace('.', '_')}_tmp"
                    
                    # Clean up existing temp if it exists
                    if temp_path.exists():
                        if temp_path.is_dir():
                            shutil.rmtree(temp_path)
                        else:
                            temp_path.unlink()
                    
                    # Move item to temp location
                    shutil.move(str(item_path), str(temp_path))
                    preserved_items[item_name] = (item_path, temp_path)
                    log(f"Temporarily moved {item_name}: {item_path} -> {temp_path}")

            # Remove entire deploy directory contents
            if deploy_dir.exists():
                shutil.rmtree(deploy_dir)
                log(f"Removed deploy directory: {deploy_dir}")

            # Recreate deploy directory and restore preserved items
            deploy_dir.mkdir(parents=True, exist_ok=True)
            for item_name, (original_path, temp_path) in preserved_items.items():
                if temp_path.exists():
                    restored_path = deploy_dir / item_name
                    shutil.move(str(temp_path), str(restored_path))
                    log(f"Restored {item_name}: {restored_path}")

            deployment_cleaned = True
        except Exception as e:
            warn(f"Failed to clean deploy directory while preserving whitelisted items: {e}")
            report_error("backend", f"Failed to clean deploy directory while preserving whitelisted items: {e}")

    # Cache cleanup hooks
    if not is_error():
        try:
            log("Running cache cleanup hooks")
            results = run_hooks('deploy_cache_cleanup')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Cache cleanup hooks failed: {e}")
            report_error("backend", f"Cache cleanup hooks failed: {e}")

    # Clean cache files
    if not is_error():
        cache_cleaned = {
            'pycache_dirs': 0,
            'pyc_files': 0,
            'cache_files': 0,
            'cache_dirs': 0
        }
        try:
            # Remove __pycache__ directories
            for pycache_dir in dest.rglob('__pycache__'):
                shutil.rmtree(pycache_dir)
                cache_cleaned['pycache_dirs'] += 1
                log(f"Removed __pycache__ directory: {pycache_dir}")

            # Remove .pyc files
            for pyc_file in dest.rglob('*.pyc'):
                pyc_file.unlink()
                cache_cleaned['pyc_files'] += 1
                log(f"Removed .pyc file: {pyc_file}")

            # Remove cache files
            cache_patterns = ['*-reg.json', '*.cycle.json', 'cache.json', '*.cache']
            for pattern in cache_patterns:
                for cache_file in dest.rglob(pattern):
                    cache_file.unlink()
                    cache_cleaned['cache_files'] += 1
                    log(f"Removed cache file: {cache_file}")

            # Remove .cache directories
            for cache_dir in dest.rglob('.cache'):
                shutil.rmtree(cache_dir)
                cache_cleaned['cache_dirs'] += 1
                log(f"Removed .cache directory: {cache_dir}")

            log(f"Cache cleanup complete: {cache_cleaned['pycache_dirs']} __pycache__ dirs, {cache_cleaned['pyc_files']} .pyc files, {cache_cleaned['cache_files']} cache files, {cache_cleaned['cache_dirs']} .cache dirs")
        except Exception as e:
            warn(f"Failed to clean cache files: {e}")
            report_error("backend", f"Failed to clean cache files: {e}")

    # Deploy Flask apps via module hooks
    if not is_error():
        try:
            log("Running Flask app deployment hooks")
            results = run_hooks('deploy_flask_apps')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Flask app deployment hooks failed: {e}")
            report_error("backend", f"Flask app deployment hooks failed: {e}")

    # Deploy maintenance worker script
    if not is_error():
        try:
            maint_source = source / MAINTENANCE_APP_SOURCE
            if maint_source.exists():
                maint_dest = dest / f'{project_name}_maintenance.py'
                content = maint_source.read_text()
                content = content.replace('__PROJECT_NAME__', project_name)
                with open(maint_dest, 'w') as f:
                    f.write(content)
                log(f"Deployed maintenance worker: {maint_dest}")
            else:
                log("Maintenance worker template not found, skipping deployment")
        except Exception as e:
            warn(f"Failed to deploy maintenance worker: {e}")
            report_error("backend", f"Failed to deploy maintenance worker: {e}")
    
    # Deploy EXT maintenance workers (e.g., migration_worker.py)
    if not is_error():
        try:
            ext_maint_dir = source / "ext" / "deploy" / "maintenance"
            if ext_maint_dir.exists():
                for worker_file in ext_maint_dir.glob("*_worker.py"):
                    daemon_name = worker_file.stem.replace("_worker", "")
                    maint_dest = dest / f'{project_name}_maintenance_{daemon_name}.py'
                    content = worker_file.read_text()
                    # No replacement needed for EXT workers (they find project root themselves)
                    with open(maint_dest, 'w') as f:
                        f.write(content)
                    log(f"Deployed EXT maintenance worker: {maint_dest} (from {worker_file.name})")
        except Exception as e:
            warn(f"Failed to deploy EXT maintenance workers: {e}")
            report_error("backend", f"Failed to deploy EXT maintenance workers: {e}")

    flask_restart_info: Dict[str, Any] = {}
    maintenance_restart_info: Dict[str, Any] = {}

    # Deploy extra top-level files (config-driven)
    if not is_error():
        try:
            for rel_path in HH_EXTRA_DEPLOY_FILES:
                src = source / rel_path
                if src.exists():
                    dst = dest / src.name
                    shutil.copy2(src, dst)
                    log(f"Deployed HH extra file: {rel_path}")
                else:
                    log(f"HH extra deploy file not found: {rel_path}")
            for rel_path in EXT_EXTRA_DEPLOY_FILES:
                src = source / rel_path
                if src.exists():
                    dst = dest / src.name
                    shutil.copy2(src, dst)
                    log(f"Deployed EXT extra file: {rel_path}")
                else:
                    log(f"EXT extra deploy file not found: {rel_path}")
        except Exception as e:
            warn(f"Failed to deploy extra files: {e}")
            report_error("backend", f"Failed to deploy extra files: {e}")

    # Deploy context folders and files
    if not is_error():
        context_deployed = []
        try:
            for item_str in CONTEXT_WHITELIST:
                source_item = source / item_str
                if source_item.exists():
                    dest_item = dest / 'context' / item_str
                    if source_item.is_dir():
                        # Handle directories
                        if dest_item.exists():
                            shutil.rmtree(dest_item)
                        shutil.copytree(source_item, dest_item, ignore=should_ignore_context_path)
                        context_deployed.append(item_str)
                        log(f"Deployed context folder: {item_str} -> context/{item_str}")
                    elif source_item.is_file():
                        # Handle files
                        dest_item.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_item, dest_item)
                        context_deployed.append(item_str)
                        log(f"Deployed context file: {item_str} -> context/{item_str}")
                    else:
                        log(f"Context item is neither file nor directory: {item_str}")
                else:
                    log(f"Context item not found: {item_str}")
            log(f"Context deployment complete: {len(context_deployed)} items")
        except Exception as e:
            warn(f"Failed to deploy context folders: {e}")
            report_error("backend", f"Failed to deploy context folders: {e}")

    # Site preparation hooks
    if not is_error():
        try:
            log("Running site preparation hooks")
            results = run_hooks('deploy_site_prepare')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Site preparation hooks failed: {e}")
            report_error("backend", f"Site preparation hooks failed: {e}")

    # Site deployment hooks (JS, CSS, misc - run in alphabetical order)
    site_deployed: List[str] = []
    js_count = 0
    css_count = 0
    misc_count = 0
    flask_restart_info = {}
    maintenance_restart_info = {}
    if not is_error():
        try:
            log("Running site deployment hooks")
            results = run_hooks('deploy_site')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Site deployment hooks failed: {e}")
            report_error("backend", f"Site deployment hooks failed: {e}")


    # Phase 1: Pre-permissions setup
    if not is_error():
        try:
            log("Running pre-permissions setup hooks")
            results = run_hooks('deploy_permissions_pre')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Pre-permissions setup hooks failed: {e}")
            report_error("backend", f"Pre-permissions setup hooks failed: {e}")

    # Phase 2: Base permissions setup
    if not is_error():
        try:
            log("Running base permissions setup hooks")
            results = run_hooks('deploy_permissions_base')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Base permissions setup hooks failed: {e}")
            report_error("backend", f"Base permissions setup hooks failed: {e}")

    # Phase 3: Special permissions setup
    if not is_error():
        try:
            log("Running special permissions setup hooks")
            results = run_hooks('deploy_permissions_special')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Special permissions setup hooks failed: {e}")
            report_error("backend", f"Special permissions setup hooks failed: {e}")

    # Phase 4: Permissions verification
    if not is_error():
        try:
            log("Running permissions verification hooks")
            results = run_hooks('deploy_permissions_verify')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Permissions verification hooks failed: {e}")
            report_error("backend", f"Permissions verification hooks failed: {e}")

    # Restart daemons after permissions/logs are in place
    if not is_error():
        try:
            log("Running daemon restart hooks")
            results = run_hooks('deploy_restart_daemons')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Daemon restart hooks failed: {e}")
            report_error("backend", f"Daemon restart hooks failed: {e}")

    # Deploy NGINX and SSL via module hooks
    deployment_mode = "https"
    flask_deployed: List[str] = []
    nginx_deployed = False
    certificate_created = False
    nginx_status_data: Dict[str, Any] = {}
    server_ip = ""
    if not is_error():
        try:
            log("Running NGINX and SSL deployment hooks")
            results = run_hooks('deploy_nginx_and_ssl')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"NGINX and SSL deployment hooks failed: {e}")
            report_error("backend", f"NGINX and SSL deployment hooks failed: {e}")

    # Final result
    deployment_result: bool = not is_error()
    if deployment_result:
        log("Deployment completed successfully")

        # Manifest update hooks
        try:
            log("Running manifest update hooks")
            results = run_hooks('deploy_manifest_update')
            if results:
                hook_results.extend(results)
        except Exception as e:  # noqa: BLE001
            warn(f"Manifest update hooks failed: {e}")
            report_error("backend", f"Manifest update hooks failed: {e}")

        # Add to manifest
        try:
            _manifest_add_site(project_name, domain, deployment_mode)
        except Exception as e:
            warn(f"Failed to record site in manifest: {e}")
        
        result_data = {
            "project_name": project_name,
            "source": str(source),
            "destination": str(dest),
            "domain": domain,
            "is_local": is_local,
            "ssl_enabled": ssl_enabled,
            "deployment_mode": deployment_mode,
            "code_deployed": code_deployed,
            "deployment_cleaned": deployment_cleaned,
            "cache_cleaned": cache_cleaned,
            "flask_deployed": flask_deployed,
            "context_deployed": context_deployed,
            "site_deployed": site_deployed,
            "js_count": js_count,
            "css_count": css_count,
            "misc_count": misc_count,
            "ownership_set": ownership_set,
            "cache_permissions_set": cache_permissions_set,
            "logs_permissions_set": logs_permissions_set,
            "flask_restart": flask_restart_info,
            "maintenance_restart": maintenance_restart_info,
            "hook_results": hook_results,
            "nginx_deployed": nginx_deployed,
            "certificate_created": certificate_created,
            "certificate_path": certificate_path,
            "nginx_active": nginx_status_data.get('is_active', False),
            "nginx_enabled_sites": nginx_status_data.get('enabled_sites', []),
            "local_allow_block": local_allow_block if is_local else None,
            "server_ip": server_ip,
            "status": "deployed"
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Deployment encountered problems")

    # Clear registry cache to prevent permission issues
    from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
    clean_all_caches()
    
    trace_out()
    return deployment_result
