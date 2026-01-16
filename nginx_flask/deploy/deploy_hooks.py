"""
NGINX/Flask deployment hooks
"""
import os
import subprocess
from typing import Dict, Any, Union, List
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.flask.flask_start import run_flask_start
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from nginx_flask.deploy.deploy_helpers_nginx import get_server_ip, create_nginx_ssl_config_local, create_nginx_config_local, install_nginx_ssl_config, install_nginx_config, create_local_decoy, check_nginx_status
from nginx_flask.deploy.deploy_helpers_flask import stop_flask_daemons_helper, restart_flask_daemons_helper, deploy_flask_apps_helper
from nginx_flask.deploy.deploy_helpers_permissions import set_flask_logs_permissions_helper, set_site_permissions_helper
from nginx_flask.deploy.deploy_helpers_site import prepare_site_directory_helper, deploy_site_css_helper, deploy_site_js_helper, deploy_site_misc_helper
from nginx_flask.deploy.deploy_helpers_directory import sterilize_deployment_directory_helper
from nginx_flask.deploy.deploy_helpers_modules import deploy_modules_helper, clean_module_deploy_directories_helper
from nginx_flask.deploy.deploy_helpers_clients import deploy_client_files_helper
from nginx_flask.deploy.deploy_helpers_context import deploy_context_helper


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

# Pre-validated configuration storage for nginx_flask module
pre_validated_whitelists: Dict[str, List[str]] = {}

@register_module_hook('deploy_pre_validate')
def validate_nginx_flask_config():
    """Pre-validate NGINX/Flask specific configuration including whitelists."""
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


@register_module_hook('deploy_render')
def render_nginx_flask_summary():
    """Render NGINX/Flask summary pieces for main deployment table."""
    from hh.render.render import TableData, FieldConfig
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}

    table_data = TableData()

    # Get site deployment counts from hook results
    hook_results = source_data.get('hook_results', [])
    js_count = 0
    css_count = 0
    misc_count = 0

    for result in hook_results:
        if result.get('component') == 'site_js' and result.get('js_count'):
            js_count = result['js_count']
        elif result.get('component') == 'site_css' and result.get('count'):
            css_count = result['count']
        elif result.get('component') == 'site_misc' and result.get('count'):
            misc_count = result['count']

    # Flask deployment
    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'deploy_apps' and
            result.get('flask_deployed')):
            flask_apps = result['flask_deployed']
            for app in flask_apps:
                table_data.add_row('flask_deployed', value=app)

    # Flask restart status
    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'restart' and
            result.get('flask_restart')):
            flask_data = result['flask_restart']
            daemons = flask_data.get('daemons', [])
            for daemon in daemons:
                tier = daemon.get('tier', 'unknown')
                status = daemon.get('status', 'unknown')
                port = daemon.get('port', 'unknown')
                user = daemon.get('user', 'unknown')
                display = f"{tier}: {status}"
                table_data.add_row('flask_restart', value=display)

    # Site file counts
    if js_count > 0:
        table_data.add_row('js_count', value=f"{js_count} files")
    if css_count > 0:
        table_data.add_row('css_count', value=f"{css_count} files")
    if misc_count > 0:
        table_data.add_row('misc_count', value=f"{misc_count} files")

    field_config = FieldConfig()
    field_config.add_simple(['flask_deployed', 'flask_restart', 'js_count', 'css_count', 'misc_count'])

    return {
        "table_data": table_data,
        "field_config": field_config
    }


@register_module_hook('deploy_render')
def render_nginx_domain_table():
    """Render the NGINX domain information as a separate full table."""
    from hh.render.render import TableData, FieldConfig, render_block
    from hh.gateway.gateway import get_gateway
    from hh.gateway.response.json_standard import get_data

    # Access final deployment results directly
    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}

    domain = source_data.get('domain', '')
    ssl_enabled = source_data.get('ssl_enabled', False)
    is_local = source_data.get('is_local', False)

    if not domain:
        return {"render_block": "<div>No domain configured</div>"}

    # Build domain table
    table_data = TableData()
    table_data.add_row('domain_header', value=domain)

    # Port (443 for SSL, 80 for HTTP-only)
    port = '443' if ssl_enabled else '80'
    table_data.add_row('port', value=port)

    # Certificate path and creation status
    certificate_path = source_data.get('certificate_path')
    certificate_created = source_data.get('certificate_created', False)
    if certificate_path:
        cert_status = str(certificate_path)
        if certificate_created:
            cert_status += " (created)"
        table_data.add_row('certificate_path', value=cert_status)

    # Server IP binding
    server_ip = source_data.get('server_ip')
    if server_ip and isinstance(server_ip, str):
        table_data.add_row('bind_ips', value=server_ip)

    # Client IP access control (local deployments only)
    local_allow_block = source_data.get('local_allow_block')
    if is_local and local_allow_block:
        table_data.add_row('client_ip_access', value=local_allow_block)

    # NGINX deployment status from hook results
    hook_results = source_data.get('hook_results', [])
    nginx_deployed = False
    nginx_active = False
    nginx_enabled_sites = []

    for result in hook_results:
        if (result.get('module') == 'nginx_flask' and
            result.get('action') == 'deploy_nginx_ssl'):
            nginx_deployed = result.get('nginx_deployed', False)
            nginx_active = result.get('nginx_active', False)
            nginx_enabled_sites = result.get('nginx_enabled_sites', [])
            break

    # NGINX status
    table_data.add_row('nginx_deployed', value='Yes' if nginx_deployed else 'No')
    nginx_status = 'Yes (nginx service running)' if nginx_active else 'No'
    table_data.add_row('nginx_active', value=nginx_status)

    field_config = FieldConfig()
    field_config.add_header('domain_header')
    field_config.add_simple(['port', 'certificate_path', 'bind_ips', 'client_ip_access', 'nginx_deployed', 'nginx_active'])

    # Return as full render_block instead of table pieces
    domain_table_html = render_block(table_data, field_config, block_type='domain')
    return {
        "render_block": domain_table_html
    }

@register_module_hook('deploy_stop_daemons')
def stop_flask_daemons() -> Union[Dict[str, Any], bool]:
    """Stop Flask tier daemons before deployment."""
    try:
        return stop_flask_daemons_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to stop Flask daemons: {e}")
        return False


@register_module_hook('deploy_restart_daemons')
def restart_flask_daemons() -> Union[Dict[str, Any], bool]:
    """Restart Flask tier daemons after deployment."""
    try:
        return restart_flask_daemons_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to restart Flask daemons: {e}")
        return False


@register_module_hook('deploy_flask_apps')
def deploy_flask_apps() -> Union[Dict[str, Any], bool]:
    """Deploy Flask tier applications and media server."""
    try:
        return deploy_flask_apps_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy Flask apps: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy Flask apps: {e}")
        return False


@register_module_hook('deploy_permissions_special')
def set_flask_logs_permissions() -> Dict[str, Any]:
    """Set special permissions for Flask daemon logs directory."""
    try:
        return set_flask_logs_permissions_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to set Flask logs permissions: {e}")
        report_error("backend", f"nginx_flask hook: Failed to set Flask logs permissions: {e}")
        return {"status": "error", "component": "flask_logs", "error": str(e)}


@register_module_hook('deploy_permissions_special')
def set_site_permissions() -> Dict[str, Any]:
    """Set special permissions for site files (HTML, JS, CSS, etc.)."""
    try:
        return set_site_permissions_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to set site permissions: {e}")
        report_error("backend", f"nginx_flask hook: Failed to set site permissions: {e}")
        return {"status": "error", "component": "site", "error": str(e)}


@register_module_hook('deploy_site_prepare')
def prepare_site_directory() -> Dict[str, Any]:
    """Prepare the site directory by clearing and recreating it."""
    try:
        return prepare_site_directory_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to prepare site directory: {e}")
        report_error("backend", f"nginx_flask hook: Failed to prepare site directory: {e}")
        return {"status": "error", "component": "site_prepare", "error": str(e)}


@register_module_hook('deploy_site')
def deploy_site_css() -> Dict[str, Any]:
    """Deploy CSS files to the site directory."""
    try:
        return deploy_site_css_helper(pre_validated_whitelists)
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy CSS files: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy CSS files: {e}")
        return {"status": "error", "component": "site_css", "error": str(e)}


@register_module_hook('deploy_site')
def deploy_site_js() -> Dict[str, Any]:
    """Deploy JavaScript files and generate registry."""
    try:
        return deploy_site_js_helper(pre_validated_whitelists)
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy JS files: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy JS files: {e}")
        return {"status": "error", "component": "site_js", "error": str(e)}


@register_module_hook('deploy_site')
def deploy_site_misc() -> Dict[str, Any]:
    """Deploy miscellaneous files to the site directory."""
    try:
        return deploy_site_misc_helper(pre_validated_whitelists)
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy misc files: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy misc files: {e}")
        return {"status": "error", "component": "site_misc", "error": str(e)}


@register_module_hook('deploy_sterilize_directory')
def sterilize_deployment_directory() -> Dict[str, Any]:
    """Sterilize deployment directory by removing all contents except preserved items."""
    try:
        return sterilize_deployment_directory_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to sterilize deployment directory: {e}")
        report_error("backend", f"nginx_flask hook: Failed to sterilize deployment directory: {e}")
        return {"status": "error", "component": "directory_sterilization", "error": str(e)}


@register_module_hook('deploy_modules')
def deploy_modules() -> Dict[str, Any]:
    """Deploy module files from DEPLOY_WHITELIST to deployment directory."""
    try:
        return deploy_modules_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy modules: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy modules: {e}")
        return {"status": "error", "component": "module_deployment", "error": str(e)}


@register_module_hook('deploy_framework_cleanup')
def clean_module_deploy_directories() -> Dict[str, Any]:
    """Clean up module deploy directories after deployment."""
    try:
        return clean_module_deploy_directories_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to clean module deploy directories: {e}")
        report_error("backend", f"nginx_flask hook: Failed to clean module deploy directories: {e}")
        return {"status": "error", "component": "module_deploy_cleanup", "error": str(e)}


@register_module_hook('deploy_client_files')
def deploy_client_files() -> Dict[str, Any]:
    """Deploy client files from CLIENT_WHITELIST to deployment directory."""
    try:
        return deploy_client_files_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy client files: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy client files: {e}")
        return {"status": "error", "component": "client_files", "error": str(e)}


@register_module_hook('deploy_context')
def deploy_context() -> Dict[str, Any]:
    """Deploy context folders and files to deployment directory."""
    try:
        return deploy_context_helper()
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy context: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy context: {e}")
        return {"status": "error", "component": "context_deployment", "error": str(e)}


@register_module_hook('deploy_nginx_and_ssl')
def deploy_nginx_and_ssl() -> Union[Dict[str, Any], bool]:
    """Deploy NGINX configuration and SSL certificates."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask hook: Could not detect project name")
            return False

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()

        # Get deployment parameters from install config
        from hh.deploy.users.install import _install_config_path
        import configparser
        cfg_path = _install_config_path(project_name)
        if not cfg_path.exists():
            warn(f"nginx_flask hook: Install config not found: {cfg_path}")
            return False

        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        if "install" not in parser:
            warn(f"nginx_flask hook: Missing [install] section in {cfg_path}")
            return False

        sec = parser["install"]
        domain = sec.get("domain", "").strip()
        if not domain:
            warn("nginx_flask hook: No domain configured")
            return False

        ssl_enabled = sec.get("ssl_enabled", "").strip().lower() in ("true", "1", "yes")
        ssl_cert_dir_self_signed = Path("/etc/ssl/self-signed")
        ssl_cert_dir_letsencrypt = Path("/etc/letsencrypt/live")
        nginx_sites_available = Path("/etc/nginx/sites-available")
        nginx_sites_enabled = Path("/etc/nginx/sites-enabled")

        # Detect if local deployment
        is_local = (domain.startswith('192.168.') or
                    domain.startswith('10.') or
                    (domain.startswith('172.') and len(domain.split('.')) >= 2 and
                     domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))

        # Get local_allow_block if local
        local_allow_block = ""
        if is_local:
            local_allow_block = f"{'.'.join(domain.split('.')[:-1])}.0/24"
                    
        nginx_deployed = False
        certificate_created = False
        server_ip = get_server_ip()
        log(f"nginx_flask hook: Detected server IP: {server_ip}")
        deployment_mode = "https" if ssl_enabled else "http"

        if ssl_enabled:
            log(f"nginx_flask hook: Starting HTTPS deployment for domain: {domain}")
            deployment_mode = "https" if not is_local else "https_local"

            # Check for certificate creation flags
            create_mode = None
            if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
                create_mode = "self-cert"
            elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
                create_mode = "get-cert"
                if is_local:
                    warn("nginx_flask hook: Cannot obtain Let's Encrypt certificate for local domain")
                    report_error("action", "Cannot obtain Let's Encrypt certificate for local domain")
                    return False

            # Determine certificate path
            if create_mode == "self-cert":
                certificate_path = ssl_cert_dir_self_signed / domain
            elif create_mode == "get-cert":
                certificate_path = ssl_cert_dir_letsencrypt / domain
            else:
                # Try to detect existing certificate
                letsencrypt_path = ssl_cert_dir_letsencrypt / domain / "fullchain.pem"
                self_signed_path = ssl_cert_dir_self_signed / domain / "fullchain.pem"
                if letsencrypt_path.exists():
                    certificate_path = ssl_cert_dir_letsencrypt / domain
                    log(f"nginx_flask hook: Found existing Let's Encrypt certificate at {certificate_path}")
                elif self_signed_path.exists():
                    certificate_path = ssl_cert_dir_self_signed / domain
                    log(f"nginx_flask hook: Found existing self-signed certificate at {certificate_path}")
                else:
                    certificate_path = ssl_cert_dir_letsencrypt / domain
                    warn(f"nginx_flask hook: Certificate not found")
                    report_error("action", f"Certificate not found for domain {domain}")
                    return False

            cert_file_path = certificate_path / "fullchain.pem"

            # Create self-signed certificate if needed
            if create_mode == "self-cert":
                log("nginx_flask hook: Creating self-signed certificate...")
                from nginx_flask.deploy.deploy_helpers_ssl import generate_self_signed_certificate, ensure_certificate_exists
                cert_name = domain.replace('.', '_')

                if generate_self_signed_certificate(certificate_path, cert_name, "root", "root"):
                    certificate_created = True
                    log(f"nginx_flask hook: Self-signed certificate generated at {certificate_path}")

                    if cert_file_path.exists():
                        if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                            warn("nginx_flask hook: Certificate verification failed after creation")
                            report_error("action", "Certificate verification failed after creation")
                else:
                    warn("nginx_flask hook: Failed to generate self-signed certificate")
                    report_error("action", "Failed to generate self-signed certificate")
                    return False

            # Verify certificate exists
            if create_mode is None and not cert_file_path.exists():
                warn(f"nginx_flask hook: Certificate file not found at {cert_file_path}")
                report_error("action", f"Certificate file not found at {cert_file_path}")
                return False

            # Install NGINX SSL configuration
            log("nginx_flask hook: Installing NGINX SSL configuration...")

            if is_local:
                log(f"nginx_flask hook: Local deployment with access control: {local_allow_block}")
                config_content = create_nginx_ssl_config_local(domain, project_name, local_allow_block, server_ip, str(certificate_path))
                if not config_content:
                    warn("nginx_flask hook: Failed to generate local NGINX SSL configuration")
                    report_error("action", "Failed to generate local NGINX SSL configuration")
                else:
                    # Write config
                    config_file = nginx_sites_available / domain
                    config_file.write_text(config_content)
                    log(f"nginx_flask hook: Local NGINX SSL config written to: {config_file}")

                    # Symlink to sites-enabled
                    enabled_file = nginx_sites_enabled / domain
                    if enabled_file.exists():
                        enabled_file.unlink()
                    enabled_file.symlink_to(config_file)
                    log(f"nginx_flask hook: Symlink created: {enabled_file}")

                    # Test and reload NGINX
                    test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                    if test_result.returncode != 0:
                        warn(f"nginx_flask hook: Nginx configuration test failed: {test_result.stderr}")
                        report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                    else:
                        log("nginx_flask hook: Nginx SSL configuration test passed")
                        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                        if reload_result.returncode != 0:
                            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                            if restart_result.returncode != 0:
                                warn(f"nginx_flask hook: Failed to reload/restart Nginx: {restart_result.stderr}")
                                report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                            else:
                                log("nginx_flask hook: Nginx restarted successfully")
                                nginx_deployed = True
                        else:
                            log("nginx_flask hook: Nginx reloaded successfully")
                            nginx_deployed = True

                        # Create decoy server
                        if nginx_deployed:
                            if not create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
                                warn("nginx_flask hook: Failed to create local decoy server")
            else:
                # Public deployment
                if install_nginx_ssl_config(domain, project_name, str(certificate_path), nginx_sites_available, nginx_sites_enabled):
                    nginx_deployed = True
                    log("nginx_flask hook: NGINX SSL configuration installed successfully")
                else:
                    warn("nginx_flask hook: NGINX SSL configuration installation failed")
                    report_error("action", "NGINX SSL configuration installation failed")

            # Get Let's Encrypt certificate if needed
            if not is_error() and create_mode == "get-cert":
                log("nginx_flask hook: Obtaining Let's Encrypt certificate...")
                from nginx_flask.deploy.deploy_helpers_ssl import get_certificate_from_letsencrypt, ensure_certificate_exists
                if get_certificate_from_letsencrypt(domain, certificate_path):
                    certificate_created = True
                    log(f"nginx_flask hook: Let's Encrypt certificate obtained for {domain}")

                    if cert_file_path.exists():
                        if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                            warn("nginx_flask hook: Certificate verification failed after creation")
                            report_error("action", "Certificate verification failed after creation")
                else:
                    warn("nginx_flask hook: Failed to obtain Let's Encrypt certificate")
                    report_error("action", "Failed to obtain Let's Encrypt certificate")

        else:
            # HTTP-only deployment
            log("nginx_flask hook: Installing NGINX HTTP-only configuration...")
            deployment_mode = "http" if not is_local else "http_local"

            if is_local:
                log(f"nginx_flask hook: Local deployment with access control: {local_allow_block}")
                config_content = create_nginx_config_local(domain, project_name, local_allow_block, server_ip)
                if not config_content:
                    warn("nginx_flask hook: Failed to generate local NGINX HTTP configuration")
                    report_error("action", "Failed to generate local NGINX HTTP configuration")
                else:
                    # Write config
                    config_file = nginx_sites_available / domain
                    config_file.write_text(config_content)
                    log(f"nginx_flask hook: Local NGINX HTTP config written to: {config_file}")

                    # Symlink to sites-enabled
                    enabled_file = nginx_sites_enabled / domain
                    if enabled_file.exists():
                        enabled_file.unlink()
                    enabled_file.symlink_to(config_file)
                    log(f"nginx_flask hook: Symlink created: {enabled_file}")

                    # Test and reload NGINX
                    test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                    if test_result.returncode != 0:
                        warn(f"nginx_flask hook: Nginx configuration test failed: {test_result.stderr}")
                        report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                    else:
                        log("nginx_flask hook: Nginx HTTP configuration test passed")
                        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                        if reload_result.returncode != 0:
                            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                            if restart_result.returncode != 0:
                                warn(f"nginx_flask hook: Failed to reload/restart Nginx: {restart_result.stderr}")
                                report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                            else:
                                log("nginx_flask hook: Nginx restarted successfully")
                                nginx_deployed = True
                        else:
                            log("nginx_flask hook: Nginx reloaded successfully")
                            nginx_deployed = True

                        # Create decoy server
                        if nginx_deployed:
                            if not create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
                                warn("nginx_flask hook: Failed to create local decoy server")
            else:
                # Public deployment
                if install_nginx_config(domain, project_name, nginx_sites_available, nginx_sites_enabled):
                    nginx_deployed = True
                    log("nginx_flask hook: NGINX HTTP configuration installed successfully")
                else:
                    warn("nginx_flask hook: NGINX HTTP configuration installation failed")
                    report_error("action", "NGINX HTTP configuration installation failed")

        # Get final NGINX status
        try:
            nginx_status = check_nginx_status()
            log(f"nginx_flask hook: NGINX status: active={nginx_status.get('is_active', False)}")
        except Exception:
            nginx_status = {'is_active': False, 'enabled_sites': []}

        return {
            "module": "nginx_flask",
            "action": "deploy_nginx_ssl",
            "nginx_deployed": nginx_deployed,
            "certificate_created": certificate_created,
            "certificate_path": str(certificate_path) if ssl_enabled and 'certificate_path' in locals() else None,
            "deployment_mode": deployment_mode,
            "nginx_active": nginx_status.get('is_active', False),
            "nginx_enabled_sites": nginx_status.get('enabled_sites', [])
        }
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy NGINX/SSL: {e}")
        report_error("action", f"nginx_flask hook: Failed to deploy NGINX/SSL: {e}")
        return False
