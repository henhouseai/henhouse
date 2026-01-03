# Chapter 7: Database Setup

## Overview

After installation, you need to initialize the database and create tier-based database users. This enables database access, page management, and full CRUD operations.

## Prerequisites

Before setting up the database, ensure you have:

1. **Chapter 5**: Installation completed
2. **Chapter 2**: MySQL server configured with SSL certificates
3. **Chapter 3**: SSL certificates installed (if not done during prerequisites)

## Database Initialization

### Initialize Database

Run the database initialization command:

```bash
# Initialize database (one-time setup)
# Creates databases and schema, automatically creates homepage if pages table is empty
sudo {hen_script_name} init-db -root -confirm
```

**What this does**:
- Creates the main database (`{project_name}`)
- Creates the cache database (`{project_name}_cache`)
- Executes schema scripts to create all tables
- Automatically creates homepage (page ID 1) if pages table is empty
- Requires `-root` flag and sudo privileges
- Uses MySQL root credentials from install config

**Requirements**:
- SSL certificates must be configured (see Chapter 3)
- MySQL root user must have access from deployment box IP (see Chapter 2)
- Install config must have valid `mysql_root_password_main` and `mysql_root_password_cache`

### Create Database Users

After initializing the database, create tier-based database users:

```bash
# Create tier-based database users
sudo {hen_script_name} add-db-users -root
```

**What this does**:
- Creates four MySQL users (one per tier):
  - `{project_name}_guest` - Guest tier user (SELECT only)
  - `{project_name}_verified` - Verified tier user (SELECT, INSERT)
  - `{project_name}_admin` - Admin tier user (SELECT, INSERT, UPDATE, DELETE)
  - `{project_name}_root` - Root tier user (full privileges)
- Grants appropriate permissions to each user
- Uses passwords from install config
- Requires `-root` flag and sudo privileges

## What This Enables

- **Database access**: Main database and cache database initialized
- **Tier-based database users**: Four MySQL users with appropriate permissions
- **Homepage created**: Page ID 1 ready to use
- **Full CRUD operations**: Create, read, update, delete pages via command line
- **Work page system**: Project planning and management features
- **Page management**: Hierarchical content, images, files, audio, video

## Testing Database Setup

Test page operations from the command line:

```bash
# View the homepage
{hen_script_name} show-page -id 1

# Create a test page (will be page ID 2)
{hen_script_name} add-page -target-page 1 -name "Test Page"

# Set the page text (assuming it's page ID 2)
{hen_script_name} modify-text -page-id 2 -text "Your text here"

# View the updated page
{hen_script_name} show-page -id 2
```

This demonstrates basic page creation and text modification from the command line.

## Database Backup and Restore

### Export Database

Create a backup of your database:

```bash
# Export main database
sudo {hen_script_name} export-db -root

# Export cache database
sudo {hen_script_name} export-db -root -cache
```

**What this does**:
- Creates export file: `database_dumps/{project_name}_export_{timestamp}.sql`
- Uses `mysqldump` with transaction control for consistent snapshot
- Includes all tables and data
- Sets file ownership to current user

**Export location**: `{project_path}/database_dumps/`

**Options**:
- `-database <db_name>`: Export specific database (defaults to main database)
- `-cache`: Export cache database instead of main database

### Import Database

Restore a database from a backup:

```bash
# Import main database
sudo {hen_script_name} import-db -root -filename database_dumps/{project_name}_export_{timestamp}.sql

# Import cache database
sudo {hen_script_name} import-db -root -cache -filename database_dumps/{project_name}_export_{timestamp}.sql
```

**What this does**:
- Imports SQL file into target database
- Replaces existing tables and data
- Shows before/after table counts for verification

**Options**:
- `-filename <path>`: Path to SQL file to import (required)
- `-database <db_name>`: Import to specific database (defaults to main database)
- `-cache`: Import to cache database instead of main database

**Warning**: Import is destructive - it replaces existing data. Always create a backup before importing.

### Check Database Status

Verify database connectivity and list all tables:

```bash
# Check database status
sudo {hen_script_name} check-db -root
```

**What this shows**:
- All tables in main database
- Row counts for each table
- Database connection status

## Technical Details: Database Export Implementation

The `export-db` command (`hh/deploy/db/export_db.py`) performs these steps:

1. **Target Database Selection**: Uses `-database` argument if provided, or `-cache` flag to select cache database, or defaults to main database
2. **Table Information Collection**: Collects table names and row counts before export
3. **mysqldump Execution**: Creates export file with options:
   - `--single-transaction`: Consistent snapshot
   - `--skip-add-drop-table`: Preserves existing table structure
   - `--disable-keys`: Faster import
   - `--extended-insert`: More efficient SQL
4. **Transaction Control**: Wraps export with:
   - `SET FOREIGN_KEY_CHECKS=0` at start
   - `SET UNIQUE_CHECKS=0` at start
   - `SET AUTOCOMMIT=0` and `START TRANSACTION` at start
   - `COMMIT` and re-enable checks at end
5. **File Ownership**: Sets ownership to current user (from `SUDO_USER` or `USER` environment)

The export uses MySQL root credentials from install config via temporary option files (mode 0600) to prevent password exposure in process lists.

## Technical Details: Database Import Implementation

The `import-db` command (`hh/deploy/db/import_db.py`) performs these steps:

1. **File Validation**: Checks that import file exists and gets file size
2. **Target Database Selection**: Uses `-database` argument, `-cache` flag, or defaults to main database
3. **Pre-Import Table Information**: Collects current table names and row counts (before import)
4. **MySQL Import Execution**: Uses `mysql` command-line client to import SQL file (pipes SQL file content to mysql stdin)
5. **Post-Import Verification**: Collects final table names and row counts (after import) and returns comparison data

The import uses MySQL root credentials from install config via temporary option files for secure password handling.

## Database Cleanup

### Clean Database (Remove All Tables)

Remove all tables from both databases:

```bash
# Clean both main and cache databases
sudo {hen_script_name} clean-db -root -confirm
```

**What this does**:
- Drops all tables from main database
- Drops all tables from cache database
- Verifies all tables were dropped
- Returns remaining table counts (should be 0)

**Warning**: This operation is destructive and cannot be undone. Use `export-db` first to create a backup.

**Requirements**:
- `-root` flag and sudo privileges
- `--confirm` flag (safety check)
- MySQL root password from install config

## Technical Details: Database Cleanup Implementation

The `clean-db` command (`hh/deploy/db/clean_db.py`) performs these steps:

1. **Clean Script Execution**: Executes `hh/deploy/db/clean.sql` on main database and `hh/deploy/db/clean_cache.sql` on cache database
2. **SQL Files**:
   - `clean.sql`: Drops all application tables (disables foreign key checks, drops all tables, re-enables checks)
   - `clean_cache.sql`: Drops all cache tables
3. **Verification**: Verifies all tables were dropped and checks both main and cache databases

The cleanup uses MySQL root credentials via temporary option files and executes SQL scripts that disable foreign key checks during cleanup to handle table dependencies.

## Technical Details: Database User Management

### Root Connection

Database administrative commands use a special root connection when the `-root` flag is provided:

- **Root Connection**: Created automatically when `-root` flag is used with database commands
- **Access Level**: Provides full MySQL root privileges for administrative operations
- **Used By**: `init-db`, `add-db-users`, `remove-db-users`, `check-db`, `export-db`, `import-db`, `clean-db`
- **Security**: Root passwords are read from install config (`/root/.{project}-install.cnf`) and passed via temporary option files (mode 0600) to prevent password exposure in process lists

### Database User Removal

The `remove-db-users` command removes database users for all tiers:

```bash
# Remove database users (optional)
sudo {hen_script_name} remove-db-users -root
```

**What this does**:
- Checks if each tier user exists before attempting removal
- Drops users with `DROP USER {username}@'%'`
- Flushes privileges after removal
- Verifies users were removed successfully

**Note**: User removal is optional. The database can remain intact with users, and you can reinstall without recreating users if they already exist.

## Troubleshooting

### Database Connection Failures

**Problem**: `init-db` or `add-db-users` fails with connection errors

**Solutions**:
1. Verify SSL certificates are configured: `ls -la /etc/mysql/ssl/ca.pem`
2. Check MySQL root user has access from deployment box IP (see Chapter 2)
3. Verify install config has correct `mysql_root_password_main` and `mysql_root_password_cache`
4. Test MySQL connection directly: `mysql -h db.yourdomain.tld -u root -p`

### Permission Denied Errors

**Problem**: Commands fail with "Access denied" errors

**Solutions**:
1. Ensure you're using `-root` flag: `sudo {hen_script_name} init-db -root -confirm`
2. Verify you're running with sudo/root privileges
3. Check MySQL root user permissions (see Chapter 2)

### Database Already Exists

**Problem**: `init-db` fails because database already exists

**Solutions**:
1. If you want to start fresh, drop the databases first (see `clean-db` command)
2. If you want to keep existing data, skip `init-db` and just run `add-db-users`

## Technical Details: Integration with Code Deployment

Database operations integrate with the code deployment system:

- **One-Time Setup**: Database initialization (`init-db`) and user creation (`add-db-users`) are one-time setup operations that happen before code deployment
- **No Database Changes During Deployment**: Code deployments (`deploy` command) do not require any database schema changes or database operations
- **Database Independence**: The database remains unchanged during code deployments - only application code files are updated
- **Separate Operations**: Database setup is separate from code deployment - you initialize the database once, then deploy code as needed without touching the database

## Next Steps

After database setup is complete:

1. **File Deployment**: Deploy your code to `/srv/` (see Chapter 8)
2. **Deployment**: Deploy code and configure web server (see Chapter 8)
3. **Daemon Management**: Verify and manage Flask and maintenance daemons (see Chapter 10)

