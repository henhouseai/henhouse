# Chapter 17: Uninstalling Henhouse

## Overview

The uninstall process removes all project users, groups, and deployment infrastructure created during installation. This chapter covers the complete uninstall workflow, including prerequisites, what gets removed, and what gets preserved.

**Important**: Uninstall is a destructive operation. Ensure you have backups of any important data before proceeding.

## Prerequisites

Before running uninstall, you must:

1. **Stop all services**: Flask daemons and maintenance daemon must be stopped
2. **Remove HTTP/NGINX sites**: All deployed HTTP/NGINX sites must be removed first (required)
3. **Optional**: Remove database users (not required - database can remain intact)

The uninstall command will refuse to run if HTTP/NGINX sites are still deployed.

## Pre-Uninstall Steps

### Step 1: Stop All Services

Stop all running services before uninstall:

```bash
# Stop Flask daemons
sudo {hen_script_name} flask-stop

# Stop maintenance daemon
sudo {hen_script_name} maintenance-stop
```

**Why**: Services run as tier users that will be removed during uninstall. Stopping them first prevents errors.

### Step 2: Remove HTTP/NGINX Sites

**Required**: Remove all deployed HTTP/NGINX sites before uninstall:

```bash
# Remove HTTP/NGINX configuration for each domain
sudo {hen_script_name} http-remove -domain example.com
```

Repeat for each domain you've deployed. The uninstall command checks for deployed sites and will refuse to run if any remain.

**Why**: NGINX configuration references project users and groups. Removing sites first ensures clean uninstall.

### Step 3: Optional - Remove Database Users

Database users can be removed, but this is optional:

```bash
# Remove database users (optional)
sudo {hen_script_name} remove-db-users -root
```

**Note**: You don't need to remove database users. The database can remain intact, and you can reinstall without reinitializing the database. Tables are dropped during uninstall, but the databases themselves remain.

## Running Uninstall

After completing prerequisites, run the uninstall command:

```bash
sudo {hen_script_name} uninstall
```

The uninstall command:
- Automatically detects project name and owner
- Discovers script name from tier user directories
- Validates all users before deletion (safety checks)
- Removes users, groups, and infrastructure

## Technical Details: Uninstall Process

The uninstall command (`hh/deploy/users/uninstall.py`) performs these steps:

1. **User Removal** (with safety validation):
   - Validates each user before deletion (see Safety Validation below)
   - Changes home directory ownership back to user before deletion
   - Removes users with `userdel -r` (removes home directory)
   - Handles leftover home directories for non-existent users
   - Removes the 4 tier users: `{project_name}_guest`, `{project_name}_verified`, `{project_name}_admin`, `{project_name}_root`

2. **Project Directory Removal**:
   - Removes `/srv/{project_name}` if highest tier user doesn't exist
   - **Preserves**: `/srv/images/{project_name}`, `/srv/files/{project_name}`, `/srv/audio/{project_name}`, `/srv/video/{project_name}` (media assets remain intact)
   - Safety check: Won't delete if highest tier user still exists

3. **Group Cleanup**:
   - Removes project owner from `{project_name}` group BEFORE deleting group
   - Deletes groups: `{project_name}`, `{project_name}_deploy`, `{project_name}_admin`

4. **Script Cleanup** (only if project users were removed):
   - Removes `{hen_script_name}` from project owner's home directory
   - Removes PATH modification from project owner's `.profile`
   - Removes `{hen_script_name}` from root user's home directory
   - Removes PATH modification from root user's `.profile`
   - Safety check: Only cleans up if at least one project user was actually removed

5. **HTTP Basic Auth Cleanup**:
   - Removes users from `/var/www/.htpasswd_admin` and `/var/www/.htpasswd_panel`
   - Uses `htpasswd -D` to delete users from files

6. **Project Group Ownership Reset**:
   - Resets project folder group ownership to project owner's primary group
   - Deletes all project groups

7. **Cache Cleanup**:
   - Calls `clean_all_caches()` from cache cleanup registry
   - Prevents permission issues from stale cache files

## Technical Details: Safety Validation System

The uninstall process includes extensive safety checks to prevent accidental deletion of non-project users:

### User Validation

Each user is validated before deletion:

1. **System User Check**: UID must be < 1000 (system users only)
2. **Shell Check**: Shell must be `/bin/bash`
3. **Home Directory Check**: Home must be `/home/{user}`
4. **Naming Pattern Check**: User must match `{project_name}_*` pattern

### Directory Validation

Leftover home directories are validated before deletion:

1. **Existence Check**: Directory must exist
2. **Path Check**: Must be under `/home/`
3. **Ownership Check**: Must be owned by expected user (UID match)
4. **Structure Check**: Must have expected agent user structure:
   - `.profile` (custom profile)
   - `gateway.py` (gateway script)
   - `hen` or custom name (hen wrapper)
   - `.ssh` directory (with only expected files)
   - `.{project_name}.cnf` (config file)
   - No unexpected non-hidden files

**Safety Philosophy**: The system is designed to be conservative - it will skip deletion rather than risk deleting something that doesn't match the expected project user pattern.

### Script Name Discovery

The uninstall command automatically discovers the script name used during installation:

- Checks first tier user's home directory
- Looks for executable files containing `'python3 gateway'`
- Defaults to `'hen'` if not found
- Used to clean up the correct script names

## What Gets Removed

The uninstall process removes:

- **Tier users**: All 4 tier users (`{project_name}_guest`, `{project_name}_verified`, `{project_name}_admin`, `{project_name}_root`)
- **Project groups**: `{project_name}`, `{project_name}_deploy`, `{project_name}_admin`
- **Project directory**: `/srv/{project_name}/` (including git repository)
- **Entry scripts**: `{hen_script_name}` from project owner and root user home directories
- **PATH modifications**: Updates to `.profile` files
- **HTTP Basic Auth**: Users removed from `.htpasswd` files
- **Database tables**: All tables in main and cache databases are dropped (but databases remain)

## What Gets Preserved

The uninstall process preserves:

- **Media assets**: `/srv/images/{project_name}/`, `/srv/files/{project_name}/`, `/srv/audio/{project_name}/`, `/srv/video/{project_name}/` (all remain intact)
- **Database structure**: Databases themselves remain (only tables are dropped)
- **Config files**: `/root/.{project}-install.cnf` and manifests remain (for reinstall)
- **NGINX configs**: NGINX configuration files remain (but sites should be removed first)

## Complete Uninstall Workflow

Here's the complete workflow for uninstalling:

```bash
# 1. Stop all services
sudo {hen_script_name} flask-stop
sudo {hen_script_name} maintenance-stop

# 2. Remove HTTP/NGINX sites (REQUIRED)
sudo {hen_script_name} http-remove -domain example.com

# 3. Optional: Remove database users
sudo {hen_script_name} remove-db-users -root

# 4. Uninstall users and infrastructure
sudo {hen_script_name} uninstall
```

## Reinstallation After Uninstall

After uninstall, you can reinstall without touching the database:

### Step 1: Reinstall Infrastructure

```bash
sudo {hen_script_name} install
```

This recreates users, groups, and infrastructure. The install config file (`/root/.{project}-install.cnf`) was preserved, so you can use the same configuration.

### Step 2: Redeploy Code

```bash
sudo {hen_script_name} deploy
```

This deploys code to `/srv/{project_name}/` and starts services.

### Step 3: Redeploy HTTP/NGINX

```bash
# HTTP deployment
sudo {hen_script_name} http-deploy -domain example.com

# SSL deployment (after certificates are installed)
sudo {hen_script_name} http-deploy-ssl -domain example.com
```

**Note**: You don't need to reinitialize the database. The database structure remains, and you can continue using it. If you want to start fresh, you can run `init-db` and `add-db-users` again, but it's not required.

## Complete Wipe (Manual Cleanup)

If you want to completely remove everything, including media assets and config files:

### Step 1: Run Standard Uninstall

Follow the complete uninstall workflow above.

### Step 2: Manually Remove Media Assets

```bash
# Remove media directories
sudo rm -rf /srv/images/{project_name}
sudo rm -rf /srv/files/{project_name}
sudo rm -rf /srv/audio/{project_name}
sudo rm -rf /srv/video/{project_name}
```

### Step 3: Manually Remove Config Files

```bash
# Remove install config and manifests
sudo rm -f /root/.{project}-install.cnf
```

### Step 4: Optional - Drop Databases

If you want to completely remove the databases:

```bash
# Connect to MySQL
mysql -h db.yourdomain.tld -u root -p

# Drop databases
DROP DATABASE {project_name};
DROP DATABASE {project_name}_cache;
```

## Troubleshooting

### Uninstall Refuses to Run

**Problem**: Uninstall fails with "deployed sites found" error

**Solution**: Remove all HTTP/NGINX sites first:
```bash
sudo {hen_script_name} http-remove -domain example.com
```

### Services Still Running

**Problem**: Uninstall fails because services are still running

**Solution**: Stop all services first:
```bash
sudo {hen_script_name} flask-stop
sudo {hen_script_name} maintenance-stop
```

### User Validation Fails

**Problem**: Uninstall skips some users with validation errors

**Solution**: This is expected behavior - the safety system skips users that don't match the expected pattern. If you need to remove users manually:
```bash
sudo userdel -r {project_name}_guest
# Repeat for other tier users
```

### Media Assets Not Preserved

**Problem**: Media assets were removed during uninstall

**Solution**: This shouldn't happen - media directories are explicitly preserved. If they were removed, they may have been manually deleted or the uninstall process encountered an error. Check `/srv/` to verify.

## Next Steps

After uninstall:

- **Reinstall**: Follow the reinstallation workflow above
- **Start Fresh**: If you want a completely clean start, follow the complete wipe workflow
- **Keep Database**: You can reinstall and continue using the existing database without reinitializing

