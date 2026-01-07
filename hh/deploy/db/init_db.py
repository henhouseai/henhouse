import os
import subprocess
import configparser
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.deploy_utils import detect_project_context, ensure_certificate_exists
from hh.deploy.users.install import _install_config_path

def _extract_domain_from_host(host: str) -> Optional[str]:
    """
    Extract domain from database host.
    
    Examples:
        db.example.com -> example.com
        cache.example.com -> example.com
        example.com -> example.com
        localhost -> None
        127.0.0.1 -> None
    
    Returns:
        Domain string or None if host is localhost/127.0.0.1
    """
    if not host:
        return None
    host = host.strip().lower()
    if host in ["localhost", "127.0.0.1", "::1"]:
        return None
    # Remove subdomain prefix (e.g., "db." or "cache.")
    parts = host.split('.')
    if len(parts) >= 2:
        # Return the last two parts (domain.tld)
        return '.'.join(parts[-2:])
    return host

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

def _load_install_config(project_name: str) -> Optional[Dict[str, Union[str, int]]]:
    """Load root install config and return MySQL root passwords."""
    cfg_path = _install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Root install config not found: {cfg_path}")
        return None
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        return None
    sec = parser["install"]
    def req(key: str) -> str:
        val = sec.get(key, "").strip()
        if not val:
            raise ValueError(f"Missing required field {key} in {cfg_path}")
        return val
    data: Dict[str, Union[str, int]] = {
        "mysql_root_password_main": req("mysql_root_password_main"),
        "mysql_root_password_cache": req("mysql_root_password_cache"),
    }
    # MySQL TLS enabled setting
    mysql_tls_enabled_str = sec.get("mysql_tls_enabled", "0").strip()
    try:
        data["mysql_tls_enabled"] = int(mysql_tls_enabled_str) != 0
    except ValueError:
        data["mysql_tls_enabled"] = False  # Default to disabled if invalid value
    # MySQL SSL paths (configurable)
    data["mysql_ssl_dir"] = sec.get("mysql_ssl_dir", "/etc/mysql/ssl").strip()
    data["mysql_server_cert_path"] = sec.get("mysql_server_cert_path", "/etc/mysql/ssl/server-cert.pem").strip()
    data["mysql_server_key_path"] = sec.get("mysql_server_key_path", "/etc/mysql/ssl/server-key.pem").strip()
    data["mysql_config_path"] = sec.get("mysql_config_path", "/etc/mysql/mysql.conf.d/mysqld.cnf").strip()
    # SSL settings (optional, only used if mysql_tls_enabled = 1)
    data["ssl_ca_path"] = sec.get("ssl_ca_path", "").strip()
    data["cache_ssl_ca_path"] = sec.get("cache_ssl_ca_path", "").strip()
    # Database hosts (for domain extraction)
    data["db_host"] = sec.get("db_host", "").strip()
    # Read ssl_verify_mode from root user's .{project}.cnf file (not install config)
    root_config_path = Path('/root') / f'.{project_name}.cnf'
    ssl_verify_mode = 2  # default
    if root_config_path.exists():
        root_config = configparser.ConfigParser()
        root_config.read(root_config_path)
        if 'client' in root_config:
            try:
                ssl_verify_mode = int(root_config.get('client', 'ssl_verify_mode', fallback='2'))
            except (ValueError, configparser.NoOptionError):
                ssl_verify_mode = 2
    data["ssl_verify_mode"] = ssl_verify_mode
    return data

@register_action('init_db')
@register_command('init_db')
def init_db(args: Optional[List[str]] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    # Step 1: Validate required arguments and privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("init_db requires sudo/root privileges")
        report_error("action", "init_db requires sudo/root privileges")
        trace_out()
        return False
    
    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for init_db")
        report_error("action", "Root flag (-root) is required for init_db")
        trace_out()
        return False
    
    confirm = gateway.get_arg('confirm')
    if not confirm:
        warn("--confirm flag is required for init_db")
        report_error("action", "--confirm flag is required for init_db")
        trace_out()
        return False
    
    project_name, project_path = detect_project_context()
    log(f"Starting db initialization for project: {project_name}")
    
    # Load root passwords from install config
    cfg = _load_install_config(project_name)
    if not cfg:
        warn("Failed to load root install config")
        report_error("action", "Failed to load root install config")
        trace_out()
        return False
    
    root_password_main = str(cfg["mysql_root_password_main"])
    root_password_cache = str(cfg["mysql_root_password_cache"])
    mysql_tls_enabled = bool(cfg.get("mysql_tls_enabled", False))
    mysql_ssl_dir = str(cfg.get("mysql_ssl_dir", "/etc/mysql/ssl"))
    mysql_server_cert_path = str(cfg.get("mysql_server_cert_path", "/etc/mysql/ssl/server-cert.pem"))
    mysql_server_key_path = str(cfg.get("mysql_server_key_path", "/etc/mysql/ssl/server-key.pem"))
    mysql_config_path = str(cfg.get("mysql_config_path", "/etc/mysql/mysql.conf.d/mysqld.cnf"))
    ssl_ca_path = str(cfg.get("ssl_ca_path", ""))
    cache_ssl_ca_path = str(cfg.get("cache_ssl_ca_path", ""))
    ssl_verify_mode = int(cfg.get("ssl_verify_mode", 2))
    db_host = str(cfg.get("db_host", ""))
    
    # Extract domain from db_host for Let's Encrypt certificates
    domain = _extract_domain_from_host(db_host)
    
    cache_db_name = f"{project_name}_cache"
    
    # Step 1.5: Check MySQL user exists (hard error if missing)
    try:
        import pwd  # type: ignore[import-untyped]
        try:
            pwd.getpwnam('mysql')  # type: ignore[attr-defined]
            log("MySQL user exists")
        except KeyError:
            warn("MySQL user 'mysql' does not exist - this is required for database initialization")
            report_error("action", "MySQL user 'mysql' does not exist - this is required for database initialization")
            trace_out()
            return False
    except ImportError:
        # Windows or pwd not available - skip check
        warn("Cannot verify MySQL user existence (pwd module not available)")
    
    # Step 1.6: Validate certificate if TLS is enabled
    if mysql_tls_enabled and ssl_ca_path:
        # Check for certificate creation flags
        create_mode = None
        if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
            create_mode = "self-cert"
        elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
            create_mode = "get-cert"
            if not domain:
                warn("Cannot obtain Let's Encrypt certificate for localhost or 127.0.0.1")
                warn(f"db_host is set to '{db_host}' - Let's Encrypt requires a public domain name")
                warn("Use -self-cert flag to generate a self-signed certificate instead")
                report_error("action", "Cannot obtain Let's Encrypt certificate for localhost")
                trace_out()
                return False
        
        # Validate certificate exists and has correct permissions
        if not ensure_certificate_exists(
            cert_path=ssl_ca_path,
            cert_owner_user="mysql",
            cert_owner_group="mysql",
            create_mode=create_mode,
            domain=domain if create_mode == "get-cert" else None
        ):
            warn("Certificate validation failed")
            report_error("action", "Certificate validation failed")
            trace_out()
            return False
        log("Certificate validated successfully")
    elif not mysql_tls_enabled:
        log("MySQL TLS is disabled - skipping certificate validation")
    
    # Step 2: Locate init scripts
    init_sql_path = project_path / "hh" / "deploy" / "db" / "init.sql"
    init_cache_sql_path = project_path / "hh" / "deploy" / "db" / "init_cache.sql"
    for path in [init_sql_path, init_cache_sql_path]:
        if not is_error():
            if not path.exists():
                warn(f"Required SQL file not found at: {path}")
                report_error("action", f"SQL file not found at: {path}")
            else:
                log(f"Using SQL file: {path}")
    
    # Step 3: Ensure databases exist
    if not is_error():
        # Create main database
        main_stmt = f"CREATE DATABASE IF NOT EXISTS `{project_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='mysql_', suffix='.cnf') as opt_file:
            opt_file.write(f"[client]\n")
            opt_file.write(f"user=root\n")
            opt_file.write(f"password={root_password_main}\n")
            if mysql_tls_enabled and ssl_ca_path:
                opt_file.write(f"ssl-ca={ssl_ca_path}\n")
                # Map verify_mode to MySQL ssl-mode (fallback to less strict if mode not supported)
                if ssl_verify_mode == 0:
                    opt_file.write(f"ssl-mode=REQUIRED\n")
                elif ssl_verify_mode == 1:
                    opt_file.write(f"ssl-mode=REQUIRED\n")
                elif ssl_verify_mode == 2:
                    opt_file.write(f"ssl-mode=VERIFY_CA\n")
                elif ssl_verify_mode == 3:
                    opt_file.write(f"ssl-mode=VERIFY_IDENTITY\n")
                else:
                    opt_file.write(f"ssl-mode=REQUIRED\n")
            opt_file_path_main = opt_file.name
        try:
            os.chmod(opt_file_path_main, 0o600)
            result = subprocess.run(
                ["mysql", f"--defaults-file={opt_file_path_main}", "-e", main_stmt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                warn(f"Failed to create main database: {result.stderr}")
                report_error("action", f"Main database creation failed: {result.stderr}")
        finally:
            try:
                if os.path.exists(opt_file_path_main):
                    os.unlink(opt_file_path_main)
            except Exception:
                pass
        
        # Create cache database
        if not is_error():
            cache_stmt = f"CREATE DATABASE IF NOT EXISTS `{cache_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='mysql_', suffix='.cnf') as opt_file:
                opt_file.write(f"[client]\n")
                opt_file.write(f"user=root\n")
                opt_file.write(f"password={root_password_cache}\n")
                if mysql_tls_enabled and cache_ssl_ca_path:
                    opt_file.write(f"ssl-ca={cache_ssl_ca_path}\n")
                    # Map verify_mode to MySQL ssl-mode (fallback to less strict if mode not supported)
                    if ssl_verify_mode == 0:
                        opt_file.write(f"ssl-mode=REQUIRED\n")
                    elif ssl_verify_mode == 1:
                        opt_file.write(f"ssl-mode=REQUIRED\n")
                    elif ssl_verify_mode == 2:
                        opt_file.write(f"ssl-mode=VERIFY_CA\n")
                    elif ssl_verify_mode == 3:
                        opt_file.write(f"ssl-mode=VERIFY_IDENTITY\n")
                    else:
                        opt_file.write(f"ssl-mode=REQUIRED\n")
                opt_file_path_cache = opt_file.name
            try:
                os.chmod(opt_file_path_cache, 0o600)
                result = subprocess.run(
                    ["mysql", f"--defaults-file={opt_file_path_cache}", "-e", cache_stmt],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    warn(f"Failed to create cache database: {result.stderr}")
                    report_error("action", f"Cache database creation failed: {result.stderr}")
            finally:
                try:
                    if os.path.exists(opt_file_path_cache):
                        os.unlink(opt_file_path_cache)
                except Exception:
                    pass
    
    # Step 4: Execute init scripts
    def run_sql_script(target_db: str, sql_path: Path, label: str, password: str) -> bool:
        if is_error():
            return False
        # Create temporary MySQL option file to avoid password on command line
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='mysql_', suffix='.cnf') as opt_file:
            opt_file.write(f"[client]\n")
            opt_file.write(f"user=root\n")
            opt_file.write(f"password={password}\n")
            if mysql_tls_enabled and ssl_ca_path:
                opt_file.write(f"ssl-ca={ssl_ca_path}\n")
                # Map verify_mode to MySQL ssl-mode (fallback to less strict if mode not supported)
                if ssl_verify_mode == 0:
                    opt_file.write(f"ssl-mode=REQUIRED\n")
                elif ssl_verify_mode == 1:
                    opt_file.write(f"ssl-mode=REQUIRED\n")
                elif ssl_verify_mode == 2:
                    opt_file.write(f"ssl-mode=VERIFY_CA\n")
                elif ssl_verify_mode == 3:
                    opt_file.write(f"ssl-mode=VERIFY_IDENTITY\n")
                else:
                    opt_file.write(f"ssl-mode=REQUIRED\n")
            opt_file_path = opt_file.name
        try:
            os.chmod(opt_file_path, 0o600)
            mysql_cmd = ["mysql", f"--defaults-file={opt_file_path}", target_db]
            with open(sql_path, 'r') as sql_file:
                result = subprocess.run(
                    mysql_cmd,
                    stdin=sql_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            if result.returncode != 0:
                warn(f"{label} execution failed with return code {result.returncode}")
                warn(f"{label} stderr: {result.stderr}")
                report_error("action", f"{label} failed: {result.stderr}")
                return False
            log(f"{label} completed successfully")
            return True
        except Exception as e:
            warn(f"{label} execution failed: {str(e)}")
            report_error("action", f"{label} execution failed: {str(e)}")
            return False
        finally:
            # Clean up temporary option file
            try:
                if os.path.exists(opt_file_path):
                    os.unlink(opt_file_path)
            except Exception:
                pass
    
    run_sql_script(project_name, init_sql_path, "Main DB initialization", root_password_main)
    run_sql_script(cache_db_name, init_cache_sql_path, "Cache DB initialization", root_password_cache)
    
    # Step 4.5: Execute extension schema if it exists
    ext_schema_path = project_path / "ext" / "deploy" / "db" / "schema_ext.sql"
    if ext_schema_path.exists():
        run_sql_script(project_name, ext_schema_path, "Extension schema", root_password_main)
    
    # Step 4.6: Re-initialize connection now that databases exist
    if not is_error():
        try:
            gateway.conn.initialize()
            log("Re-initialized database connection after database creation")
        except Exception as e:
            warn(f"Failed to re-initialize connection: {str(e)}")
            report_error("action", f"Failed to re-initialize connection: {str(e)}")
    
    # Step 5: Verify tables were created
    created_tables = []
    cache_tables = []
    if not is_error():
        try:
            created_tables = gateway.conn.read("SHOW TABLES")
            log(f"Main DB tables after initialization: {len(created_tables)}")
        except Exception as e:
            warn(f"Failed to verify main tables: {str(e)}")
            report_error("action", f"Failed to verify main tables: {str(e)}")
    
    if not is_error():
        try:
            # Use gateway's cache connection (RootConnection provides root access to cache)
            if gateway.conn.cache is None:
                warn("Cache connection not available")
                trace_out()
                return False
            with gateway.conn.cache.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                cache_tables = cursor.fetchall()
                log(f"Cache DB tables after initialization: {len(cache_tables)}")
        except Exception as e:
            warn(f"Failed to verify cache tables: {str(e)}")
            report_error("action", f"Failed to verify cache tables: {str(e)}")
    
    # Step 6: Create homepage if pages table is empty
    homepage_created = False
    if not is_error():
        try:
            # Check if page with id=1 already exists
            check_query = "SELECT COUNT(*) as count FROM pages WHERE id = 1"
            check_results: List[Dict[str, Any]] = gateway.conn.read(check_query)
            if check_results and check_results[0]['count'] == 0:
                # Pages table exists but no page with id=1, create homepage
                import datetime as dt
                now = dt.datetime.now()
                user_results: List[Dict[str, Any]] = gateway.conn.read("SELECT USER() as db_user")
                db_user = user_results[0]['db_user'] if user_results else 'unknown'
                
                insert_query = """
                    INSERT INTO pages (id, parent, name, link, class, text, last_modified, username, visibility, displayStyle)
                    VALUES (1, 0, %s, NULL, 'page', 'Hello, World!', %s, %s, 1, 1)
                """
                gateway.conn.create(insert_query, (project_name, now, str(db_user)))  # type: ignore[arg-type]
                log(f"Created homepage: id=1, name='{project_name}', parent=0")
                homepage_created = True
            else:
                log("Homepage already exists (page with id=1 found)")
        except Exception as e:
            # Non-fatal - homepage creation is optional
            warn(f"Could not create homepage (non-fatal): {str(e)}")
            log("Continuing without homepage creation")
    
    # Step 7: Prepare response data
    if not is_error():
        try:
            result_data = {
                "project_name": project_name,
                "init_sql_file": str(init_sql_path),
                "cache_sql_file": str(init_cache_sql_path),
                "created_tables": len(created_tables),
                "cache_tables": len(cache_tables),
                "cache_database": cache_db_name,
                "homepage_created": homepage_created,
                "initialization_successful": len(created_tables) > 0 and len(cache_tables) > 0
            }
            gateway.response.set_action_response(success_payload(result_data))
            log(f"Init db completed successfully: {len(created_tables)} tables created")
        except Exception as e:
            warn(f"Failed to prepare response data: {str(e)}")
            report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Init db completed with errors")
        trace_out()
        return False
    log("Init db completed successfully")
    trace_out()
    return True
