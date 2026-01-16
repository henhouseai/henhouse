"""
SSL certificate management helpers.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

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

try:
    _initialize_debug()
except:
    pass


def ensure_certificate_exists(
    cert_path: str,
    cert_owner_user: str = "mysql",
    cert_owner_group: str = "mysql",
    create_mode: Optional[str] = None,
    domain: Optional[str] = None
) -> bool:
    """
    Ensure certificate exists at the specified path with correct permissions.
    
    Args:
        cert_path: Full path to the certificate file (e.g., /etc/mysql/ssl/ca.pem)
        cert_owner_user: System user that should own the certificate (default: mysql)
        cert_owner_group: System group that should own the certificate (default: mysql)
        create_mode: If certificate is missing, how to create it:
            - "self-cert": Generate self-signed certificate
            - "get-cert": Obtain Let's Encrypt certificate (requires domain)
            - None: Error if missing
        domain: Domain name for Let's Encrypt (required if create_mode="get-cert")
    
    Returns:
        True if certificate exists and is valid, False on error
    """
    trace_in()
    try:
        cert_file = Path(cert_path)
        cert_dir = cert_file.parent
        
        # Check if certificate file exists
        if not cert_file.exists():
            if create_mode is None:
                warn(f"Certificate not found at {cert_path}")
                warn("Use -self-cert flag to generate self-signed certificate, or -get-cert flag to obtain Let's Encrypt certificate")
                report_error("action", f"Certificate not found at {cert_path}")
                trace_out()
                return False
            
            # Create certificate directory if needed
            cert_dir.mkdir(parents=True, exist_ok=True)
            log(f"Creating certificate directory: {cert_dir}")
            
            # Generate certificate based on mode
            if create_mode == "self-cert":
                cert_name = cert_file.stem  # e.g., "ca" from "ca.pem"
                if not generate_self_signed_certificate(cert_dir, cert_name, cert_owner_user, cert_owner_group):
                    warn(f"Failed to generate self-signed certificate at {cert_path}")
                    report_error("action", f"Failed to generate self-signed certificate at {cert_path}")
                    trace_out()
                    return False
                log(f"Generated self-signed certificate at {cert_path}")
            elif create_mode == "get-cert":
                if not domain:
                    warn("Domain required for Let's Encrypt certificate")
                    report_error("action", "Domain required for Let's Encrypt certificate")
                    trace_out()
                    return False
                # Let's Encrypt uses a fixed path structure, so we pass cert_dir for API consistency
                # but certbot will create certificates in /etc/letsencrypt/live/{domain}/
                if not get_certificate_from_letsencrypt(domain, cert_dir):
                    warn(f"Failed to obtain Let's Encrypt certificate for {domain}")
                    report_error("action", f"Failed to obtain Let's Encrypt certificate for {domain}")
                    trace_out()
                    return False
                # Note: Let's Encrypt certificates are stored in /etc/letsencrypt/live/{domain}/
                # The cert_path should point to a file in that directory (e.g., chain.pem, fullchain.pem, cert.pem)
                # Verify the certificate file exists at the expected path
                letsencrypt_dir = Path(f"/etc/letsencrypt/live/{domain}")
                cert_file_name = cert_file.name
                letsencrypt_cert_path = letsencrypt_dir / cert_file_name
                if not letsencrypt_cert_path.exists():
                    # Try common Let's Encrypt certificate file names
                    for alt_name in ["chain.pem", "fullchain.pem", "cert.pem"]:
                        alt_path = letsencrypt_dir / alt_name
                        if alt_path.exists():
                            log(f"Let's Encrypt certificate found at {alt_path} (requested {cert_path})")
                            # Note: The user's config points to a specific file, but Let's Encrypt may use a different name
                            # This is informational - the actual file exists
                            break
                    else:
                        warn(f"Let's Encrypt certificate file not found at {letsencrypt_cert_path}")
                        warn(f"Note: Let's Encrypt stores certificates in {letsencrypt_dir}/")
                        warn(f"Update ssl_ca_path in config to point to the correct file (e.g., {letsencrypt_dir}/chain.pem)")
                        report_error("action", f"Let's Encrypt certificate file not found at expected path")
                        trace_out()
                        return False
                log(f"Obtained Let's Encrypt certificate for {domain}")
            else:
                warn(f"Unknown create_mode: {create_mode}")
                report_error("action", f"Unknown create_mode: {create_mode}")
                trace_out()
                return False
        
        # Verify certificate file exists now
        if not cert_file.exists():
            warn(f"Certificate file still missing after creation attempt: {cert_path}")
            report_error("action", f"Certificate file still missing after creation attempt: {cert_path}")
            trace_out()
            return False
        
        # Check and fix permissions
        fixed_permissions = False
        current_stat = cert_file.stat()
        expected_mode = 0o644  # Readable by all, writable by owner
        
        if current_stat.st_mode & 0o777 != expected_mode:
            try:
                cert_file.chmod(expected_mode)
                warn(f"Fixed certificate permissions on {cert_path} (was {oct(current_stat.st_mode & 0o777)}, now {oct(expected_mode)})")
                fixed_permissions = True
            except Exception as e:
                warn(f"Failed to fix certificate permissions on {cert_path}: {e}")
                report_error("action", f"Failed to fix certificate permissions on {cert_path}: {e}")
                trace_out()
                return False
        
        # Check and fix ownership
        try:
            import pwd  # type: ignore[import-untyped]
            import grp  # type: ignore[import-untyped]
            try:
                owner_uid = pwd.getpwnam(cert_owner_user).pw_uid  # type: ignore[attr-defined]
                owner_gid = grp.getgrnam(cert_owner_group).gr_gid  # type: ignore[attr-defined]
                
                if current_stat.st_uid != owner_uid or current_stat.st_gid != owner_gid:
                    os.chown(cert_file, owner_uid, owner_gid)  # type: ignore[attr-defined]
                    if not fixed_permissions:
                        warn(f"Fixed certificate ownership on {cert_path} (now {cert_owner_user}:{cert_owner_group})")
                    else:
                        log(f"Fixed certificate ownership on {cert_path} (now {cert_owner_user}:{cert_owner_group})")
            except KeyError:
                warn(f"User {cert_owner_user} or group {cert_owner_group} does not exist - skipping ownership fix")
        except ImportError:
            # Windows or pwd/grp not available
            pass
        except Exception as e:
            warn(f"Failed to check/fix certificate ownership: {e}")
        
        log(f"Certificate validated at {cert_path}")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Error ensuring certificate exists: {e}")
        report_error("action", f"Error ensuring certificate exists: {e}")
        trace_out()
        return False


def generate_self_signed_certificate(
    cert_dir: Path,
    cert_name: str,
    cert_owner_user: str = "mysql",
    cert_owner_group: str = "mysql"
) -> bool:
    """
    Generate self-signed SSL certificate (CA + server certificate).
    
    Args:
        cert_dir: Directory where certificates will be stored (e.g., /etc/mysql/ssl)
        cert_name: Base name for certificates (e.g., "ca" will create ca.pem, ca-key.pem, server.pem, server-key.pem)
        cert_owner_user: System user that should own the certificates
        cert_owner_group: System group that should own the certificates
    
    Returns:
        True on success, False on error
    """
    trace_in()
    try:
        # Ensure directory exists
        cert_dir.mkdir(parents=True, exist_ok=True)
        
        ca_key_path = cert_dir / f"{cert_name}-key.pem"
        ca_cert_path = cert_dir / f"{cert_name}.pem"
        server_key_path = cert_dir / "server-key.pem"
        server_cert_path = cert_dir / "server.pem"
        
        # Generate CA private key
        log("Generating CA private key...")
        result = subprocess.run(
            ["openssl", "genrsa", "-out", str(ca_key_path), "2048"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            warn(f"Failed to generate CA key: {result.stderr}")
            trace_out()
            return False
        
        # Generate CA certificate
        log("Generating CA certificate...")
        result = subprocess.run(
            [
                "openssl", "req", "-new", "-x509", "-nodes",
                "-days", "3650",
                "-key", str(ca_key_path),
                "-out", str(ca_cert_path),
                "-subj", "/C=US/ST=State/L=City/O=Organization/CN=MySQL-CA"
            ],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            warn(f"Failed to generate CA certificate: {result.stderr}")
            trace_out()
            return False
        
        # Generate server private key
        log("Generating server private key...")
        result = subprocess.run(
            ["openssl", "genrsa", "-out", str(server_key_path), "2048"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            warn(f"Failed to generate server key: {result.stderr}")
            trace_out()
            return False
        
        # Generate server certificate signing request
        log("Generating server certificate signing request...")
        csr_path = cert_dir / "server.csr"
        result = subprocess.run(
            [
                "openssl", "req", "-new",
                "-key", str(server_key_path),
                "-out", str(csr_path),
                "-subj", "/C=US/ST=State/L=City/O=Organization/CN=MySQL-Server"
            ],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            warn(f"Failed to generate server CSR: {result.stderr}")
            trace_out()
            return False
        
        # Sign server certificate with CA
        log("Signing server certificate with CA...")
        result = subprocess.run(
            [
                "openssl", "x509", "-req",
                "-in", str(csr_path),
                "-CA", str(ca_cert_path),
                "-CAkey", str(ca_key_path),
                "-CAcreateserial",
                "-out", str(server_cert_path),
                "-days", "3650"
            ],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            warn(f"Failed to sign server certificate: {result.stderr}")
            trace_out()
            return False
        
        # Clean up CSR and serial file
        try:
            csr_path.unlink()
            serial_path = cert_dir / f"{ca_cert_path.stem}.srl"
            if serial_path.exists():
                serial_path.unlink()
        except Exception:
            pass
        
        # Create NGINX-compatible certificate files (fullchain.pem and privkey.pem)
        # For self-signed, fullchain.pem is just the server cert (no intermediate chain needed)
        fullchain_path = cert_dir / "fullchain.pem"
        privkey_path = cert_dir / "privkey.pem"
        
        # Copy server cert to fullchain.pem
        shutil.copy2(server_cert_path, fullchain_path)
        log("Created fullchain.pem for NGINX compatibility")
        
        # Copy server key to privkey.pem
        shutil.copy2(server_key_path, privkey_path)
        log("Created privkey.pem for NGINX compatibility")
        
        # Set permissions: 644 for certificates, 600 for keys
        for cert_file in [ca_cert_path, server_cert_path, fullchain_path]:
            cert_file.chmod(0o644)
        for key_file in [ca_key_path, server_key_path, privkey_path]:
            key_file.chmod(0o600)
        
        # Set ownership
        try:
            import pwd  # type: ignore[import-untyped]
            import grp  # type: ignore[import-untyped]
            try:
                owner_uid = pwd.getpwnam(cert_owner_user).pw_uid  # type: ignore[attr-defined]
                owner_gid = grp.getgrnam(cert_owner_group).gr_gid  # type: ignore[attr-defined]
                
                for cert_file in [ca_cert_path, server_cert_path, fullchain_path, ca_key_path, server_key_path, privkey_path]:
                    os.chown(cert_file, owner_uid, owner_gid)  # type: ignore[attr-defined]
            except KeyError:
                warn(f"User {cert_owner_user} or group {cert_owner_group} does not exist - certificates created with default ownership")
        except ImportError:
            # Windows or pwd/grp not available
            pass
        except Exception as e:
            warn(f"Failed to set certificate ownership: {e}")
        
        log(f"Self-signed certificates generated in {cert_dir}")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Error generating self-signed certificate: {e}")
        trace_out()
        return False


def get_certificate_from_letsencrypt(domain: str, cert_dir: Path) -> bool:
    """
    Obtain SSL certificate from Let's Encrypt using certbot.
    
    Note: Let's Encrypt always stores certificates in /etc/letsencrypt/live/{domain}/
    regardless of the cert_dir parameter. The cert_dir parameter is accepted for
    API consistency but Let's Encrypt's path structure is fixed.
    
    Args:
        domain: Domain name for the certificate
        cert_dir: Directory parameter (ignored - Let's Encrypt uses fixed path)
    
    Returns:
        True on success, False on error
    """
    trace_in()
    try:
        # Check if certbot is available
        result = subprocess.run(
            ["which", "certbot"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            warn("certbot not found - install certbot to use Let's Encrypt certificates")
            report_error("action", "certbot not found - install certbot to use Let's Encrypt certificates")
            trace_out()
            return False
        
        # Run certbot to obtain certificate
        log(f"Obtaining Let's Encrypt certificate for {domain}...")
        result = subprocess.run(
            [
                "certbot", "certonly",
                "--standalone",
                "--non-interactive",
                "--agree-tos",
                "--email", f"admin@{domain}",  # Default email, could be made configurable
                "-d", domain,
                "-d", f"www.{domain}",
                "-d", f"admin.{domain}",
                "-d", f"panel.{domain}"
            ],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            warn(f"certbot failed: {result.stderr}")
            report_error("action", f"certbot failed: {result.stderr}")
            trace_out()
            return False
        
        # Let's Encrypt always stores certificates in /etc/letsencrypt/live/{domain}/
        # This path is fixed by Let's Encrypt and cannot be configured
        letsencrypt_path = Path(f"/etc/letsencrypt/live/{domain}")
        if not letsencrypt_path.exists():
            warn(f"Let's Encrypt certificate directory not found after certbot: {letsencrypt_path}")
            report_error("action", f"Let's Encrypt certificate directory not found after certbot: {letsencrypt_path}")
            trace_out()
            return False
        
        log(f"Let's Encrypt certificate obtained for {domain} at {letsencrypt_path}")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Error obtaining Let's Encrypt certificate: {e}")
        report_error("action", f"Error obtaining Let's Encrypt certificate: {e}")
        trace_out()
        return False
