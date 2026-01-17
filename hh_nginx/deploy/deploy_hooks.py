"""
NGINX deployment hooks - split from monolithic deploy_85 into three focused hooks.

These hooks handle NGINX configuration deployment and SSL certificates.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.error.error_store import report_error, is_error

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


@register_module_hook('deploy_85_nginx_config', 'Generate and install NGINX configuration')
def deploy_nginx_config() -> Dict[str, Any]:
    """
    Generate and install NGINX configuration files.

    Handles both SSL and HTTP-only configurations for local and public deployments.
    Writes config to sites-available and creates symlink to sites-enabled.
    Does NOT restart nginx - that's done in deploy_87.
    """
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context
    from hh_nginx.deploy.deploy_helpers_nginx import (
        get_server_ip, create_nginx_ssl_config_local, create_nginx_config_local,
        create_nginx_ssl_config, create_nginx_config
    )

    project_name, current_path = detect_project_context()
    if not project_name:
        warn("hh_nginx: Could not detect project name")
        trace_out()
        return {"status": "error", "error": "Could not detect project name"}

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()

    # Get deployment parameters from install config
    from hh.deploy.users.install import _install_config_path
    import configparser
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"hh_nginx: Install config not found: {cfg_path}")
        trace_out()
        return {"status": "error", "error": f"Install config not found: {cfg_path}"}

    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"hh_nginx: Missing [install] section in {cfg_path}")
        trace_out()
        return {"status": "error", "error": "Missing [install] section in config"}

    sec = parser["install"]
    domain = sec.get("domain", "").strip()
    if not domain:
        warn("hh_nginx: No domain configured")
        trace_out()
        return {"status": "error", "error": "No domain configured"}

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

    server_ip = get_server_ip()
    log(f"hh_nginx: Detected server IP: {server_ip}")
    deployment_mode = "https" if ssl_enabled else "http"

    config_written = False
    certificate_path = None

    if ssl_enabled:
        log(f"hh_nginx: Preparing HTTPS deployment for domain: {domain}")
        deployment_mode = "https" if not is_local else "https_local"

        # Check for certificate creation flags
        create_mode = None
        if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
            create_mode = "self-cert"
        elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
            create_mode = "get-cert"
            if is_local:
                warn("hh_nginx: Cannot obtain Let's Encrypt certificate for local domain")
                report_error("action", "Cannot obtain Let's Encrypt certificate for local domain")
                trace_out()
                return {"status": "error", "error": "Cannot obtain Let's Encrypt certificate for local domain"}

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
                log(f"hh_nginx: Found existing Let's Encrypt certificate at {certificate_path}")
            elif self_signed_path.exists():
                certificate_path = ssl_cert_dir_self_signed / domain
                log(f"hh_nginx: Found existing self-signed certificate at {certificate_path}")
            else:
                certificate_path = ssl_cert_dir_letsencrypt / domain
                warn(f"hh_nginx: Certificate not found (will be created in deploy_86)")

        # Generate and write NGINX SSL configuration
        log("hh_nginx: Generating NGINX SSL configuration...")

        if is_local:
            log(f"hh_nginx: Local deployment with access control: {local_allow_block}")
            config_content = create_nginx_ssl_config_local(domain, project_name, local_allow_block, server_ip, str(certificate_path))
        else:
            config_content = create_nginx_ssl_config(domain, project_name, str(certificate_path))

        if not config_content:
            warn("hh_nginx: Failed to generate NGINX SSL configuration")
            report_error("action", "Failed to generate NGINX SSL configuration")
        else:
            # Write config
            config_file = nginx_sites_available / domain
            config_file.write_text(config_content)
            log(f"hh_nginx: NGINX SSL config written to: {config_file}")

            # Symlink to sites-enabled
            enabled_file = nginx_sites_enabled / domain
            if enabled_file.exists():
                enabled_file.unlink()
            enabled_file.symlink_to(config_file)
            log(f"hh_nginx: Symlink created: {enabled_file}")
            config_written = True

    else:
        # HTTP-only deployment
        log("hh_nginx: Preparing NGINX HTTP-only configuration...")
        deployment_mode = "http" if not is_local else "http_local"

        if is_local:
            log(f"hh_nginx: Local deployment with access control: {local_allow_block}")
            config_content = create_nginx_config_local(domain, project_name, local_allow_block, server_ip)
        else:
            config_content = create_nginx_config(domain, project_name)

        if not config_content:
            warn("hh_nginx: Failed to generate NGINX HTTP configuration")
            report_error("action", "Failed to generate NGINX HTTP configuration")
        else:
            # Write config
            config_file = nginx_sites_available / domain
            config_file.write_text(config_content)
            log(f"hh_nginx: NGINX HTTP config written to: {config_file}")

            # Symlink to sites-enabled
            enabled_file = nginx_sites_enabled / domain
            if enabled_file.exists():
                enabled_file.unlink()
            enabled_file.symlink_to(config_file)
            log(f"hh_nginx: Symlink created: {enabled_file}")
            config_written = True

    result = {
        "module": "hh_nginx",
        "action": "deploy_nginx_config",
        "config_written": config_written,
        "deployment_mode": deployment_mode,
        "certificate_path": str(certificate_path) if certificate_path else None,
        "server_ip": server_ip,
        "local_allow_block": local_allow_block if is_local else None,
        "ssl_enabled": ssl_enabled,
        "is_local": is_local,
        "domain": domain
    }

    trace_out()
    return result


@register_module_hook('deploy_86_ssl_certificates', 'Create and verify SSL certificates')
def deploy_ssl_certificates() -> Dict[str, Any]:
    """
    Handle SSL certificate creation and verification.

    Creates self-signed certificates or obtains Let's Encrypt certificates as needed.
    Verifies certificates exist and are valid.
    """
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context

    project_name, current_path = detect_project_context()
    if not project_name:
        warn("hh_nginx: Could not detect project name")
        trace_out()
        return {"status": "error", "error": "Could not detect project name"}

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()

    # Get deployment parameters from install config
    from hh.deploy.users.install import _install_config_path
    import configparser
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        # Config not found, but this is OK - might be HTTP-only deployment
        trace_out()
        return {"status": "skipped", "reason": "No install config found"}

    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        trace_out()
        return {"status": "skipped", "reason": "No install section in config"}

    sec = parser["install"]
    domain = sec.get("domain", "").strip()
    ssl_enabled = sec.get("ssl_enabled", "").strip().lower() in ("true", "1", "yes")

    if not ssl_enabled:
        log("hh_nginx: SSL not enabled, skipping certificate handling")
        trace_out()
        return {"status": "skipped", "reason": "SSL not enabled"}

    ssl_cert_dir_self_signed = Path("/etc/ssl/self-signed")
    ssl_cert_dir_letsencrypt = Path("/etc/letsencrypt/live")

    # Detect if local deployment
    is_local = (domain.startswith('192.168.') or
                domain.startswith('10.') or
                (domain.startswith('172.') and len(domain.split('.')) >= 2 and
                 domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))

    # Check for certificate creation flags
    create_mode = None
    if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
        create_mode = "self-cert"
    elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
        create_mode = "get-cert"

    certificate_created = False
    certificate_path = None

    # Determine certificate path
    if create_mode == "self-cert":
        certificate_path = ssl_cert_dir_self_signed / domain
    elif create_mode == "get-cert":
        certificate_path = ssl_cert_dir_letsencrypt / domain
    else:
        # Detect existing certificate
        letsencrypt_path = ssl_cert_dir_letsencrypt / domain / "fullchain.pem"
        self_signed_path = ssl_cert_dir_self_signed / domain / "fullchain.pem"
        if letsencrypt_path.exists():
            certificate_path = ssl_cert_dir_letsencrypt / domain
        elif self_signed_path.exists():
            certificate_path = ssl_cert_dir_self_signed / domain
        else:
            certificate_path = ssl_cert_dir_letsencrypt / domain

    cert_file_path = certificate_path / "fullchain.pem"

    # Create self-signed certificate if needed
    if create_mode == "self-cert":
        log("hh_nginx: Creating self-signed certificate...")
        from hh_nginx.deploy.deploy_helpers_ssl import generate_self_signed_certificate, ensure_certificate_exists
        cert_name = domain.replace('.', '_')

        if generate_self_signed_certificate(certificate_path, cert_name, "root", "root"):
            certificate_created = True
            log(f"hh_nginx: Self-signed certificate generated at {certificate_path}")

            if cert_file_path.exists():
                if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                    warn("hh_nginx: Certificate verification failed after creation")
                    report_error("action", "Certificate verification failed after creation")
        else:
            warn("hh_nginx: Failed to generate self-signed certificate")
            report_error("action", "Failed to generate self-signed certificate")
            trace_out()
            return {"status": "error", "error": "Failed to generate self-signed certificate"}

    # Get Let's Encrypt certificate if needed
    elif create_mode == "get-cert" and not is_error():
        log("hh_nginx: Obtaining Let's Encrypt certificate...")
        from hh_nginx.deploy.deploy_helpers_ssl import get_certificate_from_letsencrypt, ensure_certificate_exists
        if get_certificate_from_letsencrypt(domain, certificate_path):
            certificate_created = True
            log(f"hh_nginx: Let's Encrypt certificate obtained for {domain}")

            if cert_file_path.exists():
                if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                    warn("hh_nginx: Certificate verification failed after creation")
                    report_error("action", "Certificate verification failed after creation")
        else:
            warn("hh_nginx: Failed to obtain Let's Encrypt certificate")
            report_error("action", "Failed to obtain Let's Encrypt certificate")

    # Verify certificate exists
    if not cert_file_path.exists():
        if create_mode:
            warn(f"hh_nginx: Certificate file not found at {cert_file_path}")
            report_error("action", f"Certificate file not found at {cert_file_path}")
            trace_out()
            return {"status": "error", "error": f"Certificate file not found at {cert_file_path}"}
        else:
            log(f"hh_nginx: Certificate file not found, assuming it will be created later or exists elsewhere")

    result = {
        "module": "hh_nginx",
        "action": "deploy_ssl_certificates",
        "certificate_created": certificate_created,
        "certificate_path": str(certificate_path) if certificate_path else None,
        "create_mode": create_mode
    }

    trace_out()
    return result


@register_module_hook('deploy_87_nginx_restart', 'Test config, restart NGINX, and verify')
def restart_nginx() -> Dict[str, Any]:
    """
    Test NGINX configuration, restart/reload NGINX, and verify it's running.

    Creates local decoy server if needed for local deployments.
    Returns comprehensive deployment status.
    """
    trace_in()
    from hh.deploy.deploy_utils import detect_project_context
    from hh_nginx.deploy.deploy_helpers_nginx import check_nginx_status, create_local_decoy, get_server_ip

    project_name, current_path = detect_project_context()
    if not project_name:
        warn("hh_nginx: Could not detect project name")
        trace_out()
        return {"status": "error", "error": "Could not detect project name"}

    # Get deployment parameters from install config
    from hh.deploy.users.install import _install_config_path
    import configparser
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        trace_out()
        return {"status": "error", "error": "Install config not found"}

    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        trace_out()
        return {"status": "error", "error": "Missing install section"}

    sec = parser["install"]
    domain = sec.get("domain", "").strip()

    # Detect if local deployment
    is_local = (domain.startswith('192.168.') or
                domain.startswith('10.') or
                (domain.startswith('172.') and len(domain.split('.')) >= 2 and
                 domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))

    nginx_sites_available = Path("/etc/nginx/sites-available")
    nginx_sites_enabled = Path("/etc/nginx/sites-enabled")
    server_ip = get_server_ip()

    nginx_restarted = False
    decoy_created = False

    # Test NGINX configuration
    log("hh_nginx: Testing NGINX configuration...")
    test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    if test_result.returncode != 0:
        warn(f"hh_nginx: Nginx configuration test failed: {test_result.stderr}")
        report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
        trace_out()
        return {
            "status": "error",
            "error": "Nginx configuration test failed",
            "test_output": test_result.stderr
        }

    log("hh_nginx: Nginx configuration test passed")

    # Reload/restart NGINX
    log("hh_nginx: Reloading NGINX...")
    reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
    if reload_result.returncode != 0:
        # Try restart instead
        log("hh_nginx: Reload failed, attempting restart...")
        restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
        if restart_result.returncode != 0:
            warn(f"hh_nginx: Failed to reload/restart Nginx: {restart_result.stderr}")
            report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
            trace_out()
            return {
                "status": "error",
                "error": "Failed to reload/restart Nginx",
                "restart_output": restart_result.stderr
            }
        else:
            log("hh_nginx: Nginx restarted successfully")
            nginx_restarted = True
    else:
        log("hh_nginx: Nginx reloaded successfully")
        nginx_restarted = True

    # Create decoy server for local deployments
    if is_local and nginx_restarted:
        log("hh_nginx: Creating local decoy server...")
        if create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
            decoy_created = True
            log("hh_nginx: Local decoy server created successfully")
        else:
            warn("hh_nginx: Failed to create local decoy server (non-fatal)")

    # Get final NGINX status
    try:
        nginx_status = check_nginx_status()
        log(f"hh_nginx: NGINX status: active={nginx_status.get('is_active', False)}")
    except Exception as e:
        warn(f"hh_nginx: Failed to check nginx status: {e}")
        nginx_status = {'is_active': False, 'enabled_sites': []}

    result = {
        "module": "hh_nginx",
        "action": "restart_nginx",
        "nginx_restarted": nginx_restarted,
        "nginx_active": nginx_status.get('is_active', False),
        "nginx_enabled_sites": nginx_status.get('enabled_sites', []),
        "decoy_created": decoy_created if is_local else None,
        "server_ip": server_ip
    }

    trace_out()
    return result
