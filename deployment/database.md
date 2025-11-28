# Database Deployment

The database deployment system manages MySQL database initialization, user creation, permissions, and data management for both the main application database and the cache database.

## Prerequisites

Before using the database deployment system, you must have:
- MySQL server installed and running
- MySQL root password
- Installation system completed (see `installation.md`) - credential files must exist for each tier user
- Root/sudo access for database initialization commands

The database deployment system depends on the installation system because it reads passwords from the credential files (`~/.{project_name}.cnf`) created during installation.

## Database Architecture

Henhouse uses a two-database architecture:

- **Main Database**: `{project_name}` - Contains all application tables (pages, images, agents, work dockets, etc.)
- **Cache Database**: `{project_name}_cache` - Contains cache tables (pages, images, files) for performance optimization

Both databases use:
- **Character Set**: `utf8mb4`
- **Collation**: `utf8mb4_unicode_ci`
- **Engine**: InnoDB (for foreign key support)

The cache database is used by the cache management system (see `cache.md`) and the maintenance daemon (see `maintenance.md`) for storing cached page, image, and file data.

## Database Initialization

**File**: `hh/deploy/db/init_db.py`

The `init_db` command initializes both databases and creates all required tables:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)
- Requires: `--confirm` flag (safety check)

**Process Flow**:

1. **Database Creation**:
   - Creates `{project_name}` database if not exists
   - Creates `{project_name}_cache` database if not exists
   - Uses `CREATE DATABASE IF NOT EXISTS` with utf8mb4 charset

2. **Schema Execution**:
   - Executes `hh/deploy/db/init.sql` on main database
   - Executes `hh/deploy/db/init_cache.sql` on cache database
   - Uses `mysql` command-line client with root credentials

3. **Verification**:
   - Verifies tables were created in main database
   - Verifies tables were created in cache database
   - Returns table counts for both databases

**SQL Files**:
- **`init.sql`**: Creates all application tables (pages, images, files, image_instances, links, image_links, etc.)
- **`init_cache.sql`**: Creates cache tables (pages, images, files) with JSON columns for cached data

**See also**: `hh/deploy/db/init_db.py` function `init_db`

## Database User Management

**File**: `hh/deploy/db/add_db_users.py`

The `add_db_users` command creates database users for each tier with appropriate permissions:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)
- Requires: User credential files must exist (`~/.{project_name}.cnf` for each tier user)

**Process Flow**:

1. **Password Reading**:
   - Reads password from each tier user's credential file: `~/.{project_name}.cnf`
   - Parses INI-style config file to extract password
   - Skips tier if password file not found
   - These credential files are created by the installation system (see `installation.md`)

2. **User Creation/Update**:
   - Checks if user already exists
   - **If exists**: Updates password and checks/updates permissions
   - **If new**: Creates user with `CREATE USER {username}@'%' IDENTIFIED BY {password}`

3. **Permission Granting**:
   - Grants permissions on both main and cache databases
   - Permissions are tier-specific (see Tier Permissions below)
   - Uses `GRANT {permission} ON {database}.* TO {username}@'%'`

4. **Privilege Flushing**:
   - Executes `FLUSH PRIVILEGES` after all changes

**Tier Permissions**:

- **guest**: `SELECT` only (read-only access)
- **verified**: `SELECT`, `INSERT` (read and moderate write)
- **admin**: `SELECT`, `INSERT`, `UPDATE`, `DELETE` (full CRUD)
- **root**: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `INDEX`, `REFERENCES` (full database management)

**Permission Validation**:
- Checks that users have NO global privileges (all should be 'N' in `mysql.user`)
- Verifies database-specific privileges in `mysql.db`
- Updates missing permissions without revoking extra permissions (to avoid breaking existing functionality)

**See also**: `hh/deploy/db/add_db_users.py` functions `add_db_users`, `create_database_user`, `get_tier_permissions`, `check_and_update_permissions`

## Database User Removal

**File**: `hh/deploy/db/remove_db_users.py`

The `remove_db_users` command removes database users for all tiers:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)

**Process Flow**:

1. **User Removal**:
   - Checks if user exists before attempting removal
   - Drops user with `DROP USER {username}@'%'`
   - Flushes privileges after removal
   - Verifies user was removed successfully

2. **Result Tracking**:
   - Tracks which users were removed, not found, or failed
   - Returns status for each tier user

**See also**: `hh/deploy/db/remove_db_users.py` functions `remove_db_users`, `remove_database_user`

## Database Checking

**File**: `hh/deploy/db/check_db.py`

The `check_db` command verifies database connectivity and lists all tables:

**Prerequisites**:
- Requires: `-password <root_password>` (MySQL root password)

**Process Flow**:

1. **Table Discovery**:
   - Executes `SHOW TABLES` to get all table names
   - For each table, executes `SELECT COUNT(*)` to get row counts

2. **Result Formatting**:
   - Formats table information for display
   - Returns table count and detailed table info with row counts

**See also**: `hh/deploy/db/check_db.py` function `check_db`

## Database Export

**File**: `hh/deploy/db/export_db.py`

The `export_db` command exports a database to a SQL file:

**Prerequisites**:
- Requires: `-password <root_password>` (MySQL root password)
- Optional: `-database <db_name>` (defaults to main database)
- Optional: `-cache` flag (exports cache database instead)

**Process Flow**:

1. **Target Database Selection**:
   - Uses `-database` argument if provided
   - Uses `-cache` flag to select cache database
   - Defaults to main database (`{project_name}`)

2. **Table Information Collection**:
   - Collects table names and row counts before export
   - Uses main connection or cache connection as appropriate

3. **mysqldump Execution**:
   - Creates export file: `database_dumps/{project_name}_export_{timestamp}.sql`
   - Uses `mysqldump` with options:
     - `--single-transaction`: Consistent snapshot
     - `--skip-add-drop-table`: Preserves existing table structure
     - `--disable-keys`: Faster import
     - `--extended-insert`: More efficient SQL
   - Wraps export with transaction control:
     - `SET FOREIGN_KEY_CHECKS=0` at start
     - `SET UNIQUE_CHECKS=0` at start
     - `SET AUTOCOMMIT=0` and `START TRANSACTION` at start
     - `COMMIT` and re-enable checks at end

4. **File Ownership**:
   - Sets ownership to current user (from `SUDO_USER` or `USER` environment)

**Export Location**: `{project_path}/database_dumps/`

**See also**: `hh/deploy/db/export_db.py` function `export_db`

## Database Import

**File**: `hh/deploy/db/import_db.py`

The `import_db` command imports a database from a SQL file:

**Prerequisites**:
- Requires: `-password <root_password>` (MySQL root password)
- Requires: `-filename <path>` (path to SQL file to import)
- Optional: `-database <db_name>` (defaults to main database)
- Optional: `-cache` flag (imports to cache database instead)

**Process Flow**:

1. **File Validation**:
   - Checks that import file exists
   - Gets file size for reporting

2. **Target Database Selection**:
   - Uses `-database` argument if provided
   - Uses `-cache` flag to select cache database
   - Defaults to main database (`{project_name}`)

3. **Pre-Import Table Information**:
   - Collects current table names and row counts (before import)

4. **MySQL Import Execution**:
   - Uses `mysql` command-line client to import SQL file
   - Pipes SQL file content to mysql stdin

5. **Post-Import Verification**:
   - Collects final table names and row counts (after import)
   - Returns comparison data

**See also**: `hh/deploy/db/import_db.py` function `import_db`

## Database Cleaning

**File**: `hh/deploy/db/clean_db.py`

The `clean_db` command removes all tables from both databases:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)
- Requires: `--confirm` flag (safety check)

**Process Flow**:

1. **Clean Script Execution**:
   - Executes `hh/deploy/db/clean.sql` on main database
   - Executes `hh/deploy/db/clean_cache.sql` on cache database
   - Uses `mysql` command-line client with root credentials

2. **Verification**:
   - Verifies all tables were dropped
   - Checks both main and cache databases
   - Returns remaining table counts (should be 0)

**SQL Files**:
- **`clean.sql`**: Drops all application tables (disables foreign key checks, drops all tables, re-enables checks)
- **`clean_cache.sql`**: Drops all cache tables

**Warning**: This operation is destructive and cannot be undone. Use `export_db` first to create a backup.

**See also**: `hh/deploy/db/clean_db.py` function `clean_db`

## Homepage Initialization

**File**: `hh/deploy/db/init_homepage.py`

The `init_homepage` command creates the initial homepage (page ID 1):

**Prerequisites**:
- Pages table must be empty (safety check)
- Requires database connection (uses current user's credentials)

**Process Flow**:

1. **Safety Check**:
   - Verifies `pages` table is empty
   - Fails if table contains any records

2. **Homepage Creation**:
   - Inserts page with ID 1
   - Sets `parent = 0` (root page)
   - Sets `name = {project_name}`
   - Sets `text = 'Hello, World!'`
   - Sets `class = 'page'`
   - Sets `visibility = 1`, `displayStyle = 1`
   - Records current database user and timestamp

**Usage**: Run once after database initialization when pages table is empty.

**See also**: `hh/deploy/db/init_homepage.py` functions `init_homepage`, `create_homepage`, `check_pages_empty`

## Database Connection Management

The database system uses Gateway's connection management:

- **Root Connection**: Created automatically when `-password` argument is provided
  - Provides root MySQL access for administrative operations
  - Used by: `init_db`, `add_db_users`, `remove_db_users`, `check_db`, `export_db`, `import_db`, `clean_db`

- **Tier User Connections**: Created from credential files
  - Each tier user has `~/.{project_name}.cnf` with database credentials
  - Used for normal application operations
  - These credential files are created by the installation system (see `installation.md`)

- **Cache Connection**: Access via `gateway.conn.cache`
  - RootConnection provides root access to cache database
  - Used for cache table operations
  - The cache database is used by the cache management system (see `cache.md`) and maintenance daemon (see `maintenance.md`)

## SQL Schema Files

**Main Database Schema** (`init.sql`):
- Creates all application tables with foreign key relationships
- Includes: agents, pages, images, work dockets, subscriptions, watercooler, etc.
- Uses InnoDB engine for transaction support and foreign keys

**Cache Database Schema** (`init_cache.sql`):
- Creates three cache tables: `pages`, `images`, `files`
- Each table has JSON columns for cached data
- Includes `cache_built_at` timestamp for cache freshness tracking
- Used by the maintenance daemon (see `maintenance.md`) to track which items need cache refresh

**Clean Scripts**:
- `clean.sql`: Drops all main database tables
- `clean_cache.sql`: Drops all cache database tables
- Both disable foreign key checks during cleanup

## Integration with Other Systems

The database deployment system integrates with:

1. **Installation System** (`installation.md`): Reads credential files (`~/.{project_name}.cnf`) created during installation to set up database users with matching passwords.

2. **File Deployment** (`file-deployment.md`): The deployed Flask applications connect to the database using tier-specific credentials established here.

3. **Flask Application Management** (`flask.md`): Each Flask instance connects to the database using its tier user's credentials, enforcing tier-based permissions at the database level.

4. **Maintenance Daemon** (`maintenance.md`): Uses the cache database to store cached page, image, and file data. The maintenance worker refreshes stale caches by querying the cache database.

5. **Cache Management** (`cache.md`): The cache database stores JSON-encoded cached data for pages, images, and files. Cache cleanup operations may interact with the cache database.

6. **Configuration System** (`configuration.md`): The user tier configuration (`HENHOUSE_TIERS` from `user_account_suffixes.py`) determines which database users are created and what permissions they receive.

## Deployment Workflow

The typical database setup sequence is:

1. **Initial Setup** (one-time):
   ```bash
   sudo hen init-db --confirm -password <root_password>
   sudo hen add-db-users -password <root_password>
   hen init-homepage
   ```

2. **Ongoing Operations**:
   - Use `check-db` to verify database status
   - Use `export-db` before major changes to create backups
   - Use `import-db` to restore from backups
   - Use `clean-db` only when completely resetting the database (destructive)

See `workflows.md` for complete deployment workflow documentation.

