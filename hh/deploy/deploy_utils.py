import os
import shutil
import subprocess
import importlib.util
from pathlib import Path
from typing import Tuple, List, Dict, Any, TypeVar, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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

def detect_project_context() -> Tuple[str, Path]:
    trace_in()
    log("Detecting project context")
    current_path = Path.cwd()
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            project_name = current_path.name
            log(f"Found project: {project_name} at {current_path}")
            trace_out()
            return project_name, current_path
        current_path = current_path.parent
    project_name = Path.cwd().name
    log(f"Using current directory as project: {project_name}")
    trace_out()
    return project_name, Path.cwd()


# ============ Whitelist loading functions ============

T = TypeVar('T')

def _load_list_from_file(file_path: Path, var_name: str) -> T | None:
    """
    Load a Python list variable from a file using importlib.
    
    Args:
        file_path: Path to the Python file
        var_name: Name of the variable to extract
        
    Returns:
        The variable value if found, None otherwise
    """
    if not file_path.exists():
        return None
    
    try:
        # Create a module spec from the file
        spec = importlib.util.spec_from_file_location("whitelist_module", file_path)
        if spec is None or spec.loader is None:
            warn(f"Failed to create module spec for {file_path}")
            return None
        
        # Load the module
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract the variable
        if hasattr(module, var_name):
            return getattr(module, var_name)
        else:
            warn(f"Variable {var_name} not found in {file_path}")
            return None
            
    except Exception as e:
        warn(f"Error loading {file_path}: {e}")
        return None


def load_whitelist_with_extensions(
    base_name: str,
    var_name: str
) -> List[str]:
    """
    Load a whitelist from hh/deploy/conf/ with support for ext/deploy/conf/ blacklists and extensions.
    
    Processing order:
    1. Load base whitelist from hh/deploy/conf/{base_name}.py
    2. Load blacklist from ext/deploy/conf/{base_name}_blacklist.py (if exists)
    3. Subtract blacklist items from base
    4. Load extension whitelist from ext/deploy/conf/{base_name}.py (if exists)
    5. For each item in extension:
       - If item already exists in result AND was not blacklisted: WARN
       - Add item to result
    
    Args:
        base_name: Base filename without .py extension (e.g., 'css_whitelist')
        var_name: Variable name to load (e.g., 'CSS_WHITELIST')
        
    Returns:
        Final combined list of strings
    """
    trace_in()
    log(f"Loading whitelist: {base_name}.{var_name}")
    
    # Detect project context
    project_name, project_root = detect_project_context()
    
    # Determine paths
    hh_conf = project_root / "hh" / "deploy" / "conf"
    ext_conf = project_root / "ext" / "deploy" / "conf"
    
    # Step 1: Load base whitelist
    base_file = hh_conf / f"{base_name}.py"
    loaded_result = _load_list_from_file(base_file, var_name)
    
    if loaded_result is None:
        warn(f"Base whitelist {base_name}.{var_name} not found in {base_file}")
        result: List[str] = []
    else:
        # Make a copy to avoid modifying the original
        result = list(loaded_result)
        log(f"Loaded base whitelist: {len(result)} items")
    
    # Track blacklisted items (for warning purposes)
    blacklisted_items: set[str] = set()
    
    # Step 2: Load and apply blacklist
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    # Use same variable name - the file name already indicates it's a blacklist
    blacklist_var_name = var_name
    
    blacklist = _load_list_from_file(blacklist_file, blacklist_var_name)
    if blacklist is not None:
        blacklisted_items = set(blacklist)
        # Remove blacklisted items from result
        result = [item for item in result if item not in blacklisted_items]
        log(f"Applied blacklist: removed {len(blacklisted_items)} items, {len(result)} remaining")
    
    # Step 3: Load and apply extension
    ext_file = ext_conf / f"{base_name}.py"
    ext_list = _load_list_from_file(ext_file, var_name)
    
    if ext_list is not None:
        for item in ext_list:
            if item in result and item not in blacklisted_items:
                warn(f"Duplicate item in extension (not blacklisted): {item} in {ext_file}")
            if item not in result:
                result.append(item)
        log(f"Applied extension: added {len(ext_list)} items, final count: {len(result)}")
    
    trace_out()
    return result


def load_dict_whitelist_with_extensions(
    base_name: str,
    var_name: str
) -> List[Dict[str, Any]]:
    """
    Load a whitelist of dictionaries from hh/deploy/conf/ with support for ext/deploy/conf/ blacklists and extensions.
    
    Same processing order as load_whitelist_with_extensions, but for lists of dictionaries.
    Blacklist matching is done by comparing the entire dictionary structure.
    
    Args:
        base_name: Base filename without .py extension (e.g., 'application_actions')
        var_name: Variable name to load (e.g., 'APPLICATION_ACTIONS')
        
    Returns:
        Final combined list of dictionaries
    """

    def _hashable(val: Any):
        """Convert nested dict/list structures to hashable tuples for set membership checks."""
        if isinstance(val, dict):
            return tuple(sorted((k, _hashable(v)) for k, v in val.items()))
        if isinstance(val, list):
            return tuple(_hashable(v) for v in val)
        return val
    trace_in()
    log(f"Loading dict whitelist: {base_name}.{var_name}")
    debug(f"Starting load for {base_name}.{var_name}")
    
    # Detect project context
    project_name, project_root = detect_project_context()
    debug(f"Project: {project_name}, root: {project_root}")
    
    # Determine paths
    hh_conf = project_root / "hh" / "deploy" / "conf"
    ext_conf = project_root / "ext" / "deploy" / "conf"
    debug(f"HH conf path: {hh_conf}")
    debug(f"EXT conf path: {ext_conf}")
    
    # Step 1: Load base whitelist
    base_file = hh_conf / f"{base_name}.py"
    debug(f"Loading base file: {base_file}")
    loaded_result = _load_list_from_file(base_file, var_name)
    
    result: List[Dict[str, Any]] = []
    if loaded_result is None:
        warn(f"Base whitelist {base_name}.{var_name} not found in {base_file}")
        debug(f"Base whitelist NOT FOUND at {base_file}")
    else:
        # Make a copy to avoid modifying the original
        if not isinstance(loaded_result, list):
            warn(f"Base whitelist {base_name}.{var_name} is not a list, got {type(loaded_result)}")
            debug(f"Base whitelist wrong type: {type(loaded_result)}")
        else:
            result = list(loaded_result)
            log(f"Loaded base whitelist: {len(result)} items")
            debug(f"Base whitelist loaded: {len(result)} items")
            for idx, item in enumerate(result):
                debug(f"Base item {idx}: {item}")
    
    # Track blacklisted items (for warning purposes)
    # For dicts, we'll compare by converting to a normalized form (sorted tuple of items)
    blacklisted_items: set[tuple[tuple[str, Any], ...]] = set()
    
    # Step 2: Load and apply blacklist
    blacklist_file = ext_conf / f"{base_name}_blacklist.py"
    debug(f"Checking blacklist file: {blacklist_file}")
    # Use same variable name - the file name already indicates it's a blacklist
    blacklist_var_name = var_name
    
    blacklist = _load_list_from_file(blacklist_file, blacklist_var_name)
    if blacklist is None:
        debug(f"Blacklist file not found or empty: {blacklist_file}")
    elif len(blacklist) == 0:
        debug(f"Blacklist file exists but is empty: {blacklist_file}")
    if blacklist is not None and len(blacklist) > 0:
        debug(f"Blacklist loaded: {len(blacklist)} items")
        for idx, item in enumerate(blacklist):
            debug(f"Blacklist item {idx}: {item}")
        # Check if blacklist contains strings (group names) or dicts (full dict matching)
        if isinstance(blacklist[0], str):
            # Blacklist contains strings - match by 'group' key for site_links, application_actions, etc.
            debug(f"Blacklist contains strings (group names)")
            blacklisted_groups = set(blacklist)
            debug(f"Blacklisted groups: {blacklisted_groups}")
            original_count = len(result)
            debug(f"Before blacklist: {original_count} items")
            result = [
                item for item in result
                if isinstance(item, dict) and item.get('group') not in blacklisted_groups
            ]
            removed_count = original_count - len(result)
            log(f"Applied blacklist (by group name): removed {removed_count} items, {len(result)} remaining")
            debug(f"After blacklist: {len(result)} items, removed {removed_count}")
            for idx, item in enumerate(result):
                debug(f"Remaining item {idx}: {item}")
        else:
            # Blacklist contains dicts - match by full dictionary structure
            debug(f"Blacklist contains dicts (full dict matching)")
            blacklisted_dicts = {tuple(sorted(d.items())) if isinstance(d, dict) else d for d in blacklist}
            blacklisted_items = blacklisted_dicts
            debug(f"Blacklisted dicts: {len(blacklisted_dicts)} items")
            original_count = len(result)
            debug(f"Before blacklist: {original_count} items")
            
            # Remove blacklisted items from result
            result = [
                item for item in result
                if (tuple(sorted(item.items())) if isinstance(item, dict) else item) not in blacklisted_items
            ]
            removed_count = original_count - len(result)
            log(f"Applied blacklist (by dict match): removed {removed_count} items, {len(result)} remaining")
            debug(f"After blacklist: {len(result)} items, removed {removed_count}")
    
    # Step 3: Load and apply extension
    ext_file = ext_conf / f"{base_name}.py"
    debug(f"Checking extension file: {ext_file}")
    ext_list = _load_list_from_file(ext_file, var_name)
    
    if ext_list is None:
        debug(f"Extension file not found or empty: {ext_file}")
    elif len(ext_list) == 0:
        debug(f"Extension file exists but is empty: {ext_file}")
    if ext_list is not None:
        debug(f"Extension loaded: {len(ext_list)} items")
        for idx, item in enumerate(ext_list):
            debug(f"Extension item {idx}: {item}")
        # Convert result items to comparable form for duplicate checking
        result_keys = {_hashable(r) for r in result}
        debug(f"Before extension: {len(result)} items, result_keys: {len(result_keys)}")
        
        added_count = 0
        for item in ext_list:
            item_key = _hashable(item)
            if item_key in result_keys and item_key not in blacklisted_items:
                warn(f"Duplicate item in extension (not blacklisted): {item} in {ext_file}")
                debug(f"Duplicate detected (not blacklisted): {item}")
            if item_key not in result_keys:
                result.append(item)
                result_keys.add(item_key)
                added_count += 1
                debug(f"Added extension item: {item}")
        log(f"Applied extension: added {added_count} items, final count: {len(result)}")
        debug(f"After extension: {len(result)} items, added {added_count}")
        for idx, item in enumerate(result):
            debug(f"Final item {idx}: {item}")
    
    debug(f"Final result: {len(result)} items")
    trace_out()
    return result


# ============ Registry scanning functions ============

def scan_for_decorator(
    decorator_name: str,
    exclude_cache: bool = True
) -> List[str]:
    """
    Scan hh/ and ext/ folders for Python files containing a decorator pattern.
    
    This function scans both the framework (hh/) and user extension (ext/) folders
    for files containing the specified decorator pattern (e.g., "@register_action").
    
    Args:
        decorator_name: Name of the decorator to search for (e.g., "register_action")
                       The function will search for the pattern "@{decorator_name}"
        exclude_cache: If True, skip files starting with "cache_" (default: True)
    
    Returns:
        List of module paths found:
        - For hh/ files: "hh.subfolder.module"
        - For ext/ files: "ext.subfolder.module"
    """
    trace_in()
    found_files: List[str] = []
    pattern = f"@{decorator_name}"
    
    try:
        import hh
        hh_path = Path(hh.__file__).parent
        project_root = hh_path.parent
        
        # Build list of paths to scan
        scan_paths: List[Tuple[Path, str]] = [(hh_path, "hh")]
        
        # Check if ext/ exists and add it to scan paths
        ext_path = project_root / "ext"
        if ext_path.exists() and ext_path.is_dir():
            scan_paths.append((ext_path, "ext"))
            log(f"Found ext/ folder, will scan for {decorator_name}")
        
        # Scan each path
        for scan_path, module_prefix in scan_paths:
            for py_file in scan_path.rglob("*.py"):
                # Skip cache files if requested
                if exclude_cache and py_file.name.startswith("cache_"):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if pattern in content:
                            rel_path = py_file.relative_to(scan_path)
                            module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                            module_path = f"{module_prefix}." + ".".join(module_parts)
                            found_files.append(module_path)
                            log(f"Found {decorator_name} in {module_path}")
                except Exception as e:
                    warn(f"Error reading {py_file}: {e}")
                
    except Exception as e:
        warn(f"Error scanning for {decorator_name}: {e}")
    
    trace_out()
    return found_files


# ============ Certificate management functions ============

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
