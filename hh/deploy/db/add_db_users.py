import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload

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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

# Import detect_project_context from utils
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.error.error_store import report_error

def read_user_password(project_name: str, tier: str) -> Optional[str]:
    """Read password from user's .<project>.cnf file."""
    trace_in()
    try:
        username = f"{project_name}_{tier}"
        config_file = Path(f"/home/{username}/.{project_name}.cnf")
        
        debug(f"Looking for password file: {config_file}")
        debug(f"Username: {username}")
        debug(f"Project name: {project_name}")
        debug(f"Tier: {tier}")
        
        if not config_file.exists():
            warn(f"Config file not found for {username}: {config_file}")
            debug(f"Config file does not exist at: {config_file}")
            trace_out()
            return None
        
        debug(f"Config file exists, reading content...")
        with open(config_file, 'r') as f:
            content = f.read()
        
        debug(f"Config file content length: {len(content)}")
        debug(f"Config file content preview: {content[:100]}...")
        
        # Parse the config file to extract password
        password_lines = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            debug(f"Line {line_num}: {line}")
            if line.startswith('password='):
                password = line.split('=', 1)[1].strip()
                password_lines.append((line_num, password))
                debug(f"Found password on line {line_num}: length={len(password)}")
        
        if password_lines:
            # Use the last password found (in case there are multiple)
            password = password_lines[-1][1]
            log(f"Found password for {username}")
            debug(f"Using password from line {password_lines[-1][0]}, length={len(password)}")
            trace_out()
            return password
        
        warn(f"No password found in config file for {username}")
        debug(f"Parsed {len(content.split())} lines, found {len(password_lines)} password lines")
        trace_out()
        return None
        
    except Exception as e:
        warn(f"Failed to read password for {username}: {e}")
        debug(f"Exception in read_user_password: type={type(e).__name__}, message={str(e)}")
        trace_out()
        return None

def get_tier_permissions(tier: str) -> List[str]:
    """Get database permissions for a given tier."""
    if tier == 'rando':
        return ['SELECT']
    elif tier == 'verified':
        return ['SELECT', 'INSERT']
    elif tier == 'admin':
        return ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    elif tier == 'root':
        return ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'INDEX', 'REFERENCES']
    else:
        return ['SELECT']

def check_and_update_permissions(username: str, db_name: str, required_permissions: List[str]) -> Dict[str, Any]:
    """Check and update permissions for an existing user."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return {
            "status": "error",
            "message": "No gateway or connection available"
        }
    
    conn = gateway.conn.main
    try:
        # Check that user has NO global privileges (all should be 'N')
        global_privileges_ok = True
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT Select_priv, Insert_priv, Update_priv, Delete_priv, 
                       Create_priv, Drop_priv, Index_priv, References_priv
                FROM mysql.user 
                WHERE User = %s AND Host = '%%'
            """, (username,))
            user_results = cursor.fetchall()
            
            if user_results:
                row = user_results[0]
                global_privs = ['Select_priv', 'Insert_priv', 'Update_priv', 'Delete_priv', 
                              'Create_priv', 'Drop_priv', 'Index_priv', 'References_priv']
                for priv in global_privs:
                    if row[priv] == 'Y':
                        global_privileges_ok = False
                        warn(f"User {username} has global privilege {priv} set to Y - this should be N")
        
        # Get current database-specific permissions
        current_permissions = []
        
        # Then check database-specific privileges in mysql.db
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT Db, Select_priv, Insert_priv, Update_priv, Delete_priv, 
                       Create_priv, Drop_priv, Index_priv, References_priv
                FROM mysql.db 
                WHERE User = %s AND Host = '%%' AND Db = %s
            """, (username, db_name))
            db_results = cursor.fetchall()
            
            # Add database-specific privileges (these override global if more restrictive)
            if db_results:
                row = db_results[0]
                if row['Select_priv'] == 'Y' and 'SELECT' not in current_permissions: 
                    current_permissions.append('SELECT')
                if row['Insert_priv'] == 'Y' and 'INSERT' not in current_permissions: 
                    current_permissions.append('INSERT')
                if row['Update_priv'] == 'Y' and 'UPDATE' not in current_permissions: 
                    current_permissions.append('UPDATE')
                if row['Delete_priv'] == 'Y' and 'DELETE' not in current_permissions: 
                    current_permissions.append('DELETE')
                if row['Create_priv'] == 'Y' and 'CREATE' not in current_permissions: 
                    current_permissions.append('CREATE')
                if row['Drop_priv'] == 'Y' and 'DROP' not in current_permissions: 
                    current_permissions.append('DROP')
                if row['Index_priv'] == 'Y' and 'INDEX' not in current_permissions: 
                    current_permissions.append('INDEX')
                if row['References_priv'] == 'Y' and 'REFERENCES' not in current_permissions: 
                    current_permissions.append('REFERENCES')
        
        debug(f"Current permissions for {username}: {current_permissions}")
        debug(f"Required permissions: {required_permissions}")
        
        # Check which permissions are missing
        missing_permissions = [perm for perm in required_permissions if perm not in current_permissions]
        extra_permissions = [perm for perm in current_permissions if perm not in required_permissions]
        
        if not missing_permissions and not extra_permissions:
            debug(f"Permissions for {username} are already correct")
            return {
                "status": "correct",
                "message": "Permissions already correct"
            }
        
        # Update permissions
        if missing_permissions:
            debug(f"Granting missing permissions: {missing_permissions}")
            for permission in missing_permissions:
                with conn.cursor() as cursor:
                    cursor.execute(f"GRANT {permission} ON {db_name}.* TO %s@'%%'", (username,))
                    log(f"Granted {permission} on {db_name} to {username}")
        
        # Note: We don't revoke extra permissions to avoid breaking existing functionality
        if extra_permissions:
            debug(f"User has extra permissions (not revoked): {extra_permissions}")
        
        # Flush privileges
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")
            log("Flushed privileges after permission update")
        
        trace_out()
        message_parts = []
        if missing_permissions:
            message_parts.append(f"granted: {', '.join(missing_permissions)}")
        if extra_permissions:
            message_parts.append(f"had extra: {', '.join(extra_permissions)} (kept)")
        
        return {
            "status": "updated",
            "message": f"Updated permissions: {'; '.join(message_parts)}"
        }
        
    except Exception as e:
        warn(f"Failed to check/update permissions for {username}: {e}")
        trace_out()
        return {
            "status": "error",
            "message": f"Permission check failed: {str(e)}"
        }

def create_database_user(project_name: str, cache_db_name: str, tier: str, password: str) -> Dict[str, Any]:
    """Create a database user for the given tier."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return {
            "username": f"{project_name}_{tier}",
            "tier": tier,
            "status": "failed",
            "field_type": "user_failed",
            "error": "No gateway or connection available",
            "permissions": []
        }
    
    conn = gateway.conn.main
    username = f"{project_name}_{tier}"
    permissions = get_tier_permissions(tier)
    db_targets = [
        ("main", project_name),
        ("cache", cache_db_name)
    ]
    
    debug(f"Starting database user creation for: {username}")
    debug(f"Project: {project_name}, Tier: {tier}")
    debug(f"Permissions to grant: {permissions}")
    debug(f"Password length: {len(password) if password else 'None'}")
    
    try:
        # Check if user already exists
        debug(f"Checking if user {username} already exists...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT User FROM mysql.user WHERE User=%s AND host='%%'", (username,))
            result = cursor.fetchone()
            user_exists = result is not None
            debug(f"User existence check result: {user_exists}")
            if result:
                debug(f"Existing user details: {result}")
        
        if user_exists:
            log(f"Database user {username} already exists, updating password and permissions")
            debug(f"User {username} already exists, updating password and checking permissions")
            
            # Update password for existing user
            debug(f"Updating password for existing user {username}...")
            with conn.cursor() as cursor:
                cursor.execute("ALTER USER %s@'%%' IDENTIFIED BY %s", (username, password))
                log(f"Updated password for {username}")
                debug(f"ALTER USER password command executed successfully")
            
            # Check and update permissions for existing user
            permission_status = {}
            for label, db_target in db_targets:
                permission_status[label] = check_and_update_permissions(username, db_target, permissions)
                debug(f"Permission check result for {label}: {permission_status[label]}")
            
            # Flush privileges after password change
            with conn.cursor() as cursor:
                cursor.execute("FLUSH PRIVILEGES")
                log("Flushed privileges after password update")
            
            trace_out()
            return {
                "username": username,
                "tier": tier,
                "status": "updated",
                "field_type": "user_updated",
                "permissions": permissions,
                "permission_status": permission_status
            }
        
        # Create user
        debug(f"Creating user {username} with password...")
        with conn.cursor() as cursor:
            cursor.execute("CREATE USER %s@'%%' IDENTIFIED BY %s", (username, password))
            log(f"Created user {username}")
            debug(f"CREATE USER command executed successfully for {username}")
        
        # Grant permissions
        debug(f"Granting permissions to {username}...")
        for permission in permissions:
            for _, target_db in db_targets:
                debug(f"Granting {permission} permission on {target_db}.* to {username}")
                with conn.cursor() as cursor:
                    cursor.execute(f"GRANT {permission} ON {target_db}.* TO %s@'%%'", (username,))
                    log(f"Granted {permission} on {target_db} to {username}")
                    debug(f"GRANT {permission} command executed successfully for {target_db}")
        
        # Flush privileges
        debug("Flushing privileges...")
        with conn.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")
            log("Flushed privileges")
            debug("FLUSH PRIVILEGES command executed successfully")
        
        # Verify user was created successfully
        debug(f"Verifying user {username} was created...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT User, Host FROM mysql.user WHERE User=%s AND host='%%'", (username,))
            verify_result = cursor.fetchone()
            debug(f"User verification result: {verify_result}")
        
        log(f"Successfully created database user {username} with permissions: {', '.join(permissions)} on main and cache databases")
        debug(f"Database user creation completed successfully for {username}")
        trace_out()
        return {
            "username": username,
            "tier": tier,
            "status": "created",
            "field_type": "user_created",
            "permissions": permissions
        }
        
    except Exception as e:
        warn(f"Failed to create database user {username}: {e}")
        debug(f"Exception details: type={type(e).__name__}, message={str(e)}")
        if hasattr(e, 'errno'):
            debug(f"MySQL error number: {e.errno}")
        if hasattr(e, 'sqlstate'):
            debug(f"MySQL SQL state: {e.sqlstate}")
        trace_out()
        return {
            "username": username,
            "tier": tier,
            "status": "failed",
            "field_type": "user_failed",
            "error": str(e),
            "permissions": permissions
        }

@register_action('add_db_users')
@register_command('add_db_users')
def add_db_users() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    try:
        # Require -root flag and sudo/root privileges
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            warn("add_db_users requires sudo/root privileges")
            report_error("action", "add_db_users requires sudo/root privileges")
            trace_out()
            return False
        
        if not gateway.get_arg('root'):
            warn("Root flag (-root) is required for add_db_users")
            report_error("action", "Root flag (-root) is required for add_db_users")
            trace_out()
            return False

        # Gateway should automatically use RootConnection when -root flag is present
        if not gateway.conn or not gateway.conn.main:
            warn("No root connection available - gateway should create RootConnection when -root flag is present")
            report_error("action", "No root connection available")
            trace_out()
            return False

        # Detect project context
        project_name, project_path = detect_project_context()
        log(f"Starting database user deployment for project: {project_name}")
        debug(f"Project path: {project_path}")
        debug(f"Available tiers: {HENHOUSE_TIERS}")
        
        cache_db_name = f"{project_name}_cache"
        # Create database users for each tier
        user_results = []
        
        for tier in HENHOUSE_TIERS:
            log(f"Processing tier: {tier}")
            debug(f"Starting processing for tier: {tier}")
            
            # Read password from user's config file
            password = read_user_password(project_name, tier)
            if not password:
                warn(f"No password found for {project_name}_{tier}, skipping")
                debug(f"Password file not found or empty for {project_name}_{tier}")
                user_results.append({
                    "username": f"{project_name}_{tier}",
                    "tier": tier,
                    "status": "failed",
                    "error": "no password"
                })
                continue
            
            debug(f"Password found for {project_name}_{tier}: length={len(password)}")
            
            # Create database user
            debug(f"Calling create_database_user for {project_name}_{tier}")
            result = create_database_user(project_name, cache_db_name, tier, password)
            debug(f"create_database_user result: {result}")
            user_results.append(result)
        
        # Prepare result data
        result_data = {
            "project_name": project_name,
            "user_results": user_results
        }
        
        gateway.response.set_action_response(success_payload(result_data))
        log("Database user deployment completed successfully")
        
        # Clear registry cache to prevent permission issues
        from hh.deploy.cache.cache_cleanup_registry import clean_all_caches
        clean_all_caches()
        
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Database user deployment failed: {str(e)}")
        report_error("backend", f"Database user deployment failed: {str(e)}")
        trace_out()
        return False