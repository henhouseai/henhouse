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
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.users.install import _install_config_path

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
    """Load root install config and return MySQL root passwords and TLS settings."""
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

@register_action('clean_db')
@register_command('clean_db')
def clean_db(args: Optional[List[str]] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    # Step 1: Validate required arguments and privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("clean_db requires sudo/root privileges")
        report_error("action", "clean_db requires sudo/root privileges")
        trace_out()
        return False
    
    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for clean_db")
        report_error("action", "Root flag (-root) is required for clean_db")
        trace_out()
        return False
    
    confirm = gateway.get_arg('confirm')
    if not confirm:
        warn("--confirm flag is required for clean_db")
        report_error("action", "--confirm flag is required for clean_db")
        trace_out()
        return False
    
    project_name, project_path = detect_project_context()
    log(f"Starting db cleanup for project: {project_name}")
    
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
    ssl_ca_path = str(cfg.get("ssl_ca_path", ""))
    cache_ssl_ca_path = str(cfg.get("cache_ssl_ca_path", ""))
    ssl_verify_mode = 0  # Hardcoded to disable SSL verification
    
    cache_db_name = f"{project_name}_cache"
    
    # Step 2: Locate clean scripts
    clean_sql_path = project_path / "hh" / "deploy" / "db" / "clean.sql"
    clean_cache_sql_path = project_path / "hh" / "deploy" / "db" / "clean_cache.sql"
    for path in [clean_sql_path, clean_cache_sql_path]:
        if not is_error():
            if not path.exists():
                warn(f"Required SQL file not found at: {path}")
                report_error("action", f"SQL file not found at: {path}")
            else:
                log(f"Using SQL file: {path}")
    
    def run_clean_script(target_db: str, sql_path: Path, label: str, password: str, ssl_ca_path: str) -> bool:
        if is_error():
            return False
        # Create temporary MySQL option file to avoid password on command line
        import tempfile
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
                warn(f"{label} failed with return code {result.returncode}")
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
    
    # Step 3: Execute clean scripts
    run_clean_script(project_name, clean_sql_path, "Main DB cleanup", root_password_main, ssl_ca_path)
    run_clean_script(cache_db_name, clean_cache_sql_path, "Cache DB cleanup", root_password_cache, cache_ssl_ca_path)
    
    # Step 4: Verify tables were dropped
    remaining_tables = []
    cache_remaining_tables = []
    if not is_error():
        try:
            tables_result = gateway.conn.read("SHOW TABLES")
            remaining_tables = tables_result
            log(f"Remaining tables after cleanup (main): {len(remaining_tables)}")
        except Exception as e:
            warn(f"Failed to verify main table cleanup: {str(e)}")
            report_error("action", f"Failed to verify main table cleanup: {str(e)}")
    
    if not is_error():
        try:
            # Use gateway's cache connection (RootConnection provides root access to cache)
            if gateway.conn.cache is None:
                warn("Cache connection not available")
                trace_out()
                return False
            with gateway.conn.cache.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                cache_remaining_tables = cursor.fetchall()
                log(f"Remaining tables after cleanup (cache): {len(cache_remaining_tables)}")
        except Exception as e:
            warn(f"Failed to verify cache table cleanup: {str(e)}")
            report_error("action", f"Failed to verify cache table cleanup: {str(e)}")
    
    # Step 5: Prepare response data
    if not is_error():
        try:
            result_data = {
                "project_name": project_name,
                "clean_sql_file": str(clean_sql_path),
                "clean_cache_sql_file": str(clean_cache_sql_path),
                "remaining_tables": len(remaining_tables) if remaining_tables else 0,
                "cache_remaining_tables": len(cache_remaining_tables) if cache_remaining_tables else 0,
                "cleanup_successful": (len(remaining_tables) if remaining_tables else 0) == 0 and (len(cache_remaining_tables) if cache_remaining_tables else 0) == 0
            }
            gateway.response.set_action_response(success_payload(result_data))
            log(f"Clean db completed successfully: {len(remaining_tables) if remaining_tables else 0} tables remaining")
        except Exception as e:
            warn(f"Failed to prepare response data: {str(e)}")
            report_error("action", f"Failed to prepare response data: {str(e)}")

    # Final result
    if is_error():
        log("Clean db completed with errors")
        trace_out()
        return False
    log("Clean db completed successfully")
    trace_out()
    return True
