"""
NGINX and SSL certificate deployment hooks
"""
from typing import Dict, Any, Union
from pathlib import Path
import subprocess
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway

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


@register_module_hook('deploy_nginx_and_ssl')
def deploy_nginx_and_ssl() -> Union[Dict[str, Any], bool]:
    """Deploy NGINX configuration and SSL certificates."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask hook: Could not detect project name")
            return False

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

        from hh.deploy.http.deploy import (
            get_server_ip,
            create_nginx_ssl_config_local,
            create_nginx_config_local,
            install_nginx_ssl_config,
            install_nginx_config,
            create_local_decoy,
            check_nginx_status
        )

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
                from hh.deploy.deploy_utils import generate_self_signed_certificate, ensure_certificate_exists
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
                from hh.deploy.deploy_utils import get_certificate_from_letsencrypt, ensure_certificate_exists
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
