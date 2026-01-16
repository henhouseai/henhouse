import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.http.deploy_helpers import _manifest_add_site, should_ignore_context_path
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section

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

from hh.deploy.deploy_utils import load_whitelist_with_extensions
from hh.gateway.registry.module_hooks import run_hooks

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
    cache_cleaned: Dict[str, int] = {}  # Will be populated from hook results

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

    # Load whitelists with extension support
    from hh.deploy.deploy_utils import load_tuple_whitelist_with_extensions
    CONTEXT_WHITELIST = load_whitelist_with_extensions('context_whitelist', 'CONTEXT_WHITELIST')
    DEPLOY_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'DEPLOY_WHITELIST')
    CLIENT_WHITELIST = load_whitelist_with_extensions('deploy_whitelist', 'CLIENT_WHITELIST')
    APP_WHITELIST = load_tuple_whitelist_with_extensions('deploy_whitelist', 'APP_WHITELIST')

    HH_EXTRA_DEPLOY_FILES = CLIENT_WHITELIST  # All client files now in one list
    EXT_EXTRA_DEPLOY_FILES: List[str] = []  # No longer separate EXT list
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

    # Cache cleanup hooks
    if not is_error():
        try:
            log("Running cache cleanup hooks")
            results = run_hooks('deploy_cache_cleanup')
            if results:
                hook_results.extend(results)
                # Extract cache_cleaned from hook results for use in final result
                cache_cleaned = {}
                for result in results:
                    if result.get('component') == 'cache_cleanup' and result.get('cache_cleaned'):
                        cache_cleaned = result['cache_cleaned']
                        break
        except Exception as e:  # noqa: BLE001
            warn(f"Cache cleanup hooks failed: {e}")
            report_error("backend", f"Cache cleanup hooks failed: {e}")

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

    # Deploy maintenance workers via module hooks
    if not is_error():
        try:
            log("Running maintenance worker deployment hooks")
            results = run_hooks('deploy_flask_apps')
            if results:
                # Filter for maintenance module results
                maintenance_results = [r for r in results if r.get('module') == 'maintenance']
                hook_results.extend(maintenance_results)
        except Exception as e:  # noqa: BLE001
            warn(f"Maintenance worker deployment hooks failed: {e}")
            report_error("backend", f"Maintenance worker deployment hooks failed: {e}")

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
            "code_deployed": True,
            "deployment_cleaned": True,  # Module deploy directories cleaned
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


@register_parser('deploy')
def render_deploy_hookified() -> bool:
    """
    Hookified deployment renderer - processes deploy_render hooks from modules.

    This is the new rendering architecture where each module provides its own
    rendering instructions via deploy_render hooks. The results can be either:
    - {"table_data": TableData, "field_config": FieldConfig} for aggregation into main summary
    - {"render_block": "pre-rendered HTML"} for direct inclusion as separate tables

    Pieces are aggregated into ONE summary table, full tables are inserted between pieces.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_deploy_hookified")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False

    lines = []
    lines.append(render_header_block('l_deploy_header'))
    log(f"Processing hookified deploy data")

    # Call deploy_render hooks from all modules
    from hh.gateway.registry.module_hooks import run_hooks
    render_instructions = run_hooks('deploy_render')

    # Separate pieces for summary table vs full tables
    summary_table_data = TableData()
    summary_field_config = FieldConfig()
    full_tables = []  # List of (instruction_index, render_block) tuples

    # Process each render instruction and collect pieces
    for i, instruction in enumerate(render_instructions):
        if 'render_block' in instruction:
            # Full table - collect for insertion at this position
            full_tables.append((i, instruction['render_block']))
        elif 'table_data' in instruction and 'field_config' in instruction:
            # Piece for summary table - aggregate it
            piece_table_data = instruction['table_data']
            piece_field_config = instruction['field_config']

            # Merge table data (add all rows)
            for row in piece_table_data.rows:
                summary_table_data.rows.append(row)

            # Merge field configs (add all simple fields - hooks should NOT define headers)
            summary_field_config.configs.extend(piece_field_config.configs)

    # Build output: summary table first, then full tables in order
    if summary_table_data.num_rows() > 0 and summary_field_config.configs:
        # Add summary header since we have content (hooks only provide simple fields)
        summary_field_config.add_header('deploy_summary')
        summary_block = render_block(summary_table_data, summary_field_config, block_type='deploy_summary')
        lines.append(summary_block)
        break_section(lines)

    # Add full tables in the order they appeared
    for _, full_table_html in full_tables:
        lines.append(full_table_html)
        break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
