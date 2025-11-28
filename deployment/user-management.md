# User Management

The user management system provides comprehensive installation and uninstallation of the complete user infrastructure, with extensive safety checks to prevent accidental deletion of non-project users.

## Prerequisites

Before using user management, you must have:
- Installation system completed (see `installation.md`) - users and groups must exist
- Sudo/root privileges

The user management system is the inverse of the installation system (see `installation.md`). It removes all users, groups, and infrastructure created during installation.

## Uninstall Command

**File**: `hh/deploy/users/uninstall.py`

The `uninstall` command safely removes all project users, groups, and deployment infrastructure:

**Prerequisites**:
- Must run with sudo/root privileges
- Automatically detects project name and owner
- Discovers `hen` script name from tier user directories

**Optional Arguments**:
- `-remove_user <user1,user2,...>`: Additional users to remove beyond the 4 tier users

## Uninstall Process Flow

1. **User Removal** (with safety validation):
   - Validates each user before deletion (see Safety Checks below)
   - Changes home directory ownership back to user before deletion
   - Removes users with `userdel -r` (removes home directory)
   - Handles leftover home directories for non-existent users
   - Tracks which project users were actually removed
   - Removes the 4 tier users created by installation system (see `installation.md`): `{project_name}_guest`, `{project_name}_verified`, `{project_name}_admin`, `{project_name}_root`

2. **Project Directory Removal**:
   - Only removes `/srv/{project_name}` if highest tier user doesn't exist
   - **Preserves**: `/srv/images/{project_name}` and `/srv/files/{project_name}` are left untouched (created by installation system - see `installation.md`)
   - Safety check: Won't delete if highest tier user still exists

3. **Group Cleanup**:
   - Removes project owner from `{project_name}` group BEFORE deleting group
   - Deletes groups created by installation system (see `installation.md`): `{project_name}`, `{project_name}_deploy`, `{project_name}_admin`

4. **Script Cleanup** (only if project users were removed):
   - **Human user (project owner)**: Removes `{hen_script_name}` and PATH modification from `.profile` (created by installation system - see `installation.md`)
   - **Root user**: Removes `{hen_script_name}` and PATH modification from `.profile` (created by installation system - see `installation.md`)
   - Safety check: Only cleans up if at least one project user was actually removed (prevents accidental deletion on second uninstall run)

5. **HTTP Basic Auth Cleanup**:
   - Removes users from `/var/www/.htpasswd_{admin_tier}` and `/var/www/.htpasswd_panel` (created by installation system - see `installation.md`)
   - Uses `htpasswd -D` to delete users from files

6. **Project Group Ownership Reset**:
   - Resets project folder group ownership to project owner's primary group
   - Deletes all project groups

**See also**: `hh/deploy/users/uninstall.py` function `uninstall`

## Safety Validation System

The uninstall process includes extensive safety checks to prevent accidental deletion of non-project users:

### User Validation (`validate_user_for_deletion`)

Validates users before deletion:

1. **System User Check**: UID must be < 1000 (system users only)
2. **Shell Check**: Shell must be `/bin/bash`
3. **Home Directory Check**: Home must be `/home/{user}`
4. **Naming Pattern Check**: User must match `{project_name}_*` pattern

### Directory Validation (`validate_user_directory_for_deletion`)

Validates leftover home directories before deletion:

1. **Existence Check**: Directory must exist
2. **Path Check**: Must be under `/home/`
3. **Ownership Check**: Must be owned by expected user (UID match)
4. **Structure Check**: Must have expected agent user structure:
   - `.profile` (custom profile)
   - `gateway.py` (gateway script)
   - `hen` or custom name (hen wrapper)
   - `.ssh` directory (with only expected files: `id_rsa`, `id_rsa.pub`, `authorized_keys`)
   - `.{project_name}.cnf` (config file)
   - No unexpected non-hidden files

**Safety Philosophy**: The system is designed to be conservative - it will skip deletion rather than risk deleting something that doesn't match the expected project user pattern.

## Script Name Discovery

**Function**: `discover_script_names(project_name)`

Automatically discovers the `hen` script name used during installation:

- Checks first tier user's home directory
- Looks for executable files containing `'python3 gateway'`
- Defaults to `'hen'` if not found
- Used during uninstall to clean up the correct script names
- The script name is determined during installation (see `installation.md`)

## Integration Points

- **Project Detection**: Uses `detect_project_context()` from `hh/deploy/utils.py` (see `configuration.md`)
- **User Detection**: Uses `gateway.os.get_user_by_name()` and `gateway.os.user_exists()`
- **Group Detection**: Uses `gateway.os.group_exists()`
- **File Operations**: Uses `gateway.files.chown()`, `gateway.files.chmod()` for permission management
- **Cache Cleanup**: Calls `clean_all_caches()` from cache cleanup registry (see `cache.md`) at end of both install and uninstall to prevent permission issues

## Integration with Other Systems

The user management system integrates with:

1. **Installation System** (`installation.md`): 
   - Removes all users, groups, and infrastructure created by the `install` command
   - This is the inverse operation of installation

2. **Database Deployment** (`database.md`): 
   - Database users are not removed by uninstall (they must be removed separately using `remove-db-users`)
   - Credential files (`~/.{project_name}.cnf`) are removed when users are deleted

3. **File Deployment** (`file-deployment.md`): 
   - The `/srv/{project_name}` directory is removed if highest tier user doesn't exist
   - However, `/srv/images/{project_name}` and `/srv/files/{project_name}` are preserved

4. **Flask Application Management** (`flask.md`): 
   - Flask daemons should be stopped before uninstall (they run as tier users that will be removed)

5. **HTTP/NGINX Deployment** (`http-nginx.md`): 
   - HTTP Basic Auth files are cleaned up during uninstall
   - NGINX configuration is not removed (must be removed separately using `http-remove`)

6. **Maintenance Daemon** (`maintenance.md`): 
   - Maintenance daemon should be stopped before uninstall (it runs as `{project_name}_root` user that will be removed)

7. **Cache Management** (`cache.md`): 
   - All caches are cleared at end of uninstall to prevent permission issues

8. **Git Operations** (`git.md`): 
   - Git repository at `/srv/{project_name}/git/{project_name}.git` is removed if `/srv/{project_name}` is removed

## Deployment Workflow

User management (uninstall) is typically used for complete system removal:

**Complete Uninstall**:
```bash
# Stop all services first
sudo hen flask-stop
sudo hen maintenance-stop

# Remove HTTP configuration (optional)
sudo hen http-remove -domain example.com

# Remove database users (optional)
sudo hen remove-db-users -password <root_password>

# Uninstall users and infrastructure
sudo hen uninstall
```

**Warning**: Uninstall is a destructive operation. It removes all project users, groups, and most infrastructure. Some items are preserved (image/files directories) for safety.

**Re-installation**: After uninstall, you can run `install` again to recreate the user infrastructure.

See `workflows.md` for complete deployment workflow documentation.

