# Deployment Workflows

The complete deployment workflow ties together all the individual components into repeatable, automated processes for syncing code between development and production environments.

## Prerequisites

Before using deployment workflows, you must have completed:
- Installation system (see `installation.md`)
- Database deployment (see `database.md`)
- HTTP/NGINX deployment (see `http-nginx.md`)
- Initial file deployment (see `file-deployment.md`)

After initial setup, the standard workflow is simple and repeatable.

## Standard Deployment Workflow

**Repeatable Deployment Process**:

Once the initial setup is complete (installation, database initialization, HTTP configuration), the standard workflow is:

1. **Pull Latest Code**:
   ```bash
   hen pull_project
   ```
   - Fetches latest from remote (see `git.md`)
   - Hard resets to `origin/{project_name}`
   - Clears all caches (see `cache.md`)
   - Ensures clean state

2. **Deploy Everything**:
   ```bash
   sudo hen deploy
   ```
   - Stops running daemons (Flask, maintenance) - see `flask.md` and `maintenance.md`
   - Copies all whitelisted files to `/srv/{project_name}` (see `file-deployment.md`)
   - Cleans deploy folder (preserves whitelisted items) - see `configuration.md`
   - Sets permissions (see `file-deployment.md`)
   - Restarts daemons (see `flask.md` and `maintenance.md`)
   - Clears registry cache (see `cache.md`)

**Result**: Fresh instance of latest code running on server.

**Key Point**: After initial setup, you never need to run installation, database setup, or HTTP configuration again. The repeatable workflow is just `pull_project` → `sudo hen deploy`.

## Rollback Workflow

**Recovering to Previous Stable Point**:

If you need to rollback to a previous commit:

1. **Reset to Specific Commit**:
   ```bash
   git reset --hard {commit_hash}
   ```
   - Replace `{commit_hash}` with the hash of the stable commit
   - Can find hash via `git log` or GitHub interface

2. **Deploy Rolled-Back Version**:
   ```bash
   sudo hen deploy
   ```
   - Deploys the rolled-back code state (see `file-deployment.md`)
   - All services restart with previous version (see `flask.md` and `maintenance.md`)

3. **Verify and Document** (Optional):
   ```bash
   hen push_project --message "emergency revert - {description}"
   ```
   - Creates stage branch documenting the rollback (see `git.md`)
   - Useful for tracking what was reverted and why

**Result**: Server running previous stable version.

## Stage Branch Recovery Workflow

**Using Stage Branches for Recovery**:

Stage branches provide a mechanism for recovering and referencing previous working states. The `stage` script (available as `stage.py` or `stage.ps1` on Windows) provides interactive tools for managing stage branches on your laptop.

1. **Create Stage Branch from Server**:
   ```bash
   hen push_project --message "emergency revert - {description}"
   ```
   - Creates timestamped stage branch: `stage/linux/{timestamp}-{sanitized_message}` (see `git.md`)
   - Pushes current server state to remote
   - Creates `stage` signal file in repository with the message

2. **Pull Stage Branch on Laptop**:
   ```bash
   stage pull
   ```
   - Fetches remote branches and finds the latest stage branch
   - Materializes the stage branch contents into a local `./stage` directory
   - Creates a `.stage_changes.json` manifest file listing all changes (added, modified, deleted, renamed files)
   - The `stage` signal file from the branch contains the recovery message

   **Finding a Specific Stage Branch**:
   ```bash
   stage find "search term"
   ```
   - Searches stage branches for one containing the search term in its message
   - Pulls the matching stage branch if found
   - Useful when you have multiple stage branches and need a specific one

3. **Review and Apply Changes**:
   ```bash
   stage push
   ```
   - Compares files in `./stage` directory with your main codebase
   - Provides interactive review interface showing:
     - **DELETE**: Files that exist in main but not in stage (would be deleted)
     - **ADD**: Files that exist in stage but not in main (would be added)
     - **EDIT**: Files that differ between stage and main (would be updated)
     - **RENAME**: Files that were renamed (if detected in manifest)
     - **WARNINGS**: Encoding, line ending, or indentation issues
   - For each change, you can accept (Y) or skip (N)
   - Accepted changes are immediately applied to your main codebase
   - After review, the `./stage` directory is automatically cleaned up

4. **Manual Recovery** (Alternative):
   ```bash
   git checkout stage/linux/{timestamp}-{description} -- {file_path}
   ```
   - Restores specific files from stage branch without using the stage script
   - Allows granular recovery without full interactive review

**Result**: Previous working state available for reference and recovery, with interactive tools for selective restoration.

## Development-to-Production Sync Workflow

**Syncing Changes from Laptop to Server**:

1. **On Laptop - Push Changes**:
   ```bash
   hen push_project --message "deploy fix for X"
   ```
   - Creates stage branch with descriptive message (see `git.md`)
   - Pushes all local changes to remote

2. **On Server - Pull and Deploy**:
   ```bash
   hen pull_project
   sudo hen deploy
   ```
   - Pulls the stage branch (or merge it into main branch first) - see `git.md`
   - Deploys the changes - see `file-deployment.md`

**Result**: Changes synced from development to production.

## Server-to-Laptop Sync Workflow

**Syncing Changes from Server to Laptop**:

This workflow allows you to capture server-side changes (like database migrations, content updates, or emergency fixes) and bring them back to your development laptop for review and integration.

1. **On Server - Push Current State**:
   ```bash
   hen push_project --message "server changes - {description}"
   ```
   - Creates timestamped stage branch: `stage/linux/{timestamp}-{sanitized_message}` (see `git.md`)
   - Pushes current server state to remote repository
   - Creates `stage` signal file in repository with the message

2. **On Laptop - Pull Stage Branch**:
   ```bash
   stage pull
   ```
   - Fetches remote branches and finds the latest stage branch
   - Materializes the stage branch contents into a local `./stage` directory
   - Creates a `.stage_changes.json` manifest file listing all changes
   - The `stage` signal file from the branch contains the description message

   **Finding a Specific Stage Branch**:
   ```bash
   stage find "search term"
   ```
   - Searches stage branches for one containing the search term in its message
   - Pulls the matching stage branch if found
   - Useful when you have multiple stage branches and need a specific one

3. **Review and Apply Changes**:
   ```bash
   stage push
   ```
   - Compares files in `./stage` directory with your main codebase
   - Provides interactive review interface showing:
     - **DELETE**: Files that exist in main but not in stage (would be deleted)
     - **ADD**: Files that exist in stage but not in main (would be added)
     - **EDIT**: Files that differ between stage and main (would be updated)
     - **RENAME**: Files that were renamed (if detected in manifest)
     - **WARNINGS**: Encoding, line ending, or indentation issues
   - For each change, you can accept (Y) or skip (N)
   - Accepted changes are immediately applied to your main codebase
   - After review, the `./stage` directory is automatically cleaned up

**Alternative - Manual Recovery**:
   ```bash
   git checkout stage/linux/{timestamp}-{sanitized_message} -- {file_path}
   ```
   - Restores specific files from stage branch without using the stage script
   - Allows granular recovery without full interactive review

**Result**: Server changes synced to laptop with interactive review and selective application.

**Use Cases**:
- Capturing emergency fixes made directly on the server
- Bringing database migrations or schema changes back to development
- Syncing content updates or configuration changes made on server
- Recovering from accidental deletions or overwrites
- Reviewing what changed on the server before integrating into main codebase

## Complete Workflow Summary

**First-Time Server Setup** (One-time):

1. **Clone Repository**: At server root (`/`), clone from GitHub:
   ```bash
   cd /
   sudo git clone https://github.com/henhouseai/henhouse.git
   ```

2. **Rename Project** (Optional): If you want a different project name:
   ```bash
   sudo mv henhouse foxhouse  # or myproject, etc.
   cd foxhouse
   ```

3. **Install Infrastructure**: Create users, groups, SSH keys, git repo:
   ```bash
   sudo python hen.py install -hen fox  # Use -hen to customize command name
   ```
   Note: The `install` command copies SSH keys from the project owner's `~/.ssh/` to all tier users.

4. **Deploy Application**: Copy files to `/srv/{project_name}/`:
   ```bash
   sudo fox deploy
   ```

5. **Initialize Database**: Set up MySQL databases and users:
   ```bash
   sudo fox init-db --confirm -password <mysql_root_password>
   sudo fox add-db-users -password <mysql_root_password>
   fox init-homepage
   ```

6. **Configure HTTP/NGINX**: Set up web server (see `http-nginx.md`):
   ```bash
   sudo fox http-deploy -domain foxhouse.ai
   # After SSL certificates are installed:
   sudo fox http-deploy-ssl -domain foxhouse.ai
   ```

**Developer Laptop Setup** (after server setup):

Clone from your server's bare repository for development:

```bash
# Clone from server's bare repo (not GitHub)
git clone user@your-server:/srv/foxhouse/git/foxhouse.git
cd foxhouse

# Work locally, then sync to server:
git push origin foxhouse
# On server: fox pull-project && sudo fox deploy
```

**Initial Setup** (Alternative - if you already have a project folder):
1. `sudo hen install` - Create users, groups, SSH keys, git repo (see `installation.md`)
2. `sudo hen init_db` - Initialize databases (see `database.md`)
3. `sudo hen add_db_users` - Create database users (see `database.md`)
4. `sudo hen http_deploy` - Configure NGINX (HTTP) (see `http-nginx.md`)
5. `sudo hen http_deploy_ssl` - Configure NGINX (HTTPS, optional) (see `http-nginx.md`)
6. `sudo hen deploy` - Deploy initial code (see `file-deployment.md`)

**Ongoing Operations** (Repeatable):
- **Standard Deploy**: `hen pull_project` (see `git.md`) → `sudo hen deploy` (see `file-deployment.md`)
- **Rollback**: `git reset --hard {hash}` → `sudo hen deploy` (see `file-deployment.md`)
- **Laptop → Server Sync**: `hen push_project --message "..."` (laptop, see `git.md`) → `hen pull_project` + `sudo hen deploy` (server, see `git.md` and `file-deployment.md`)
- **Server → Laptop Sync**: `hen push_project --message "..."` (server, see `git.md`) → `stage pull` + `stage push` (laptop, see Server-to-Laptop Sync Workflow above)
- **Framework Upgrade**: Clone fresh Henhouse → `hen upgrade --target /path/to/project` (see Upgrade Workflow below)

**Key Benefits**:
- **Repeatable**: Same process every time
- **Reversible**: Easy rollback to any commit
- **Traceable**: Stage branches document recovery points (see `git.md`)
- **Recoverable**: Stage folder provides reference for agents/humans
- **Simple**: After setup, only two commands needed for normal deployment

## Upgrade Workflow

**Upgrading Framework Code (`hh/` folder) in an Existing Project**:

The upgrade workflow allows you to upgrade the framework code (`hh/` folder) in an existing project without affecting your customizations (`ext/` folder). This is useful when you want to pull in framework improvements from a fresh Henhouse clone.

**Prerequisites**:
- Existing project with `hh/` and optionally `ext/` folders
- Fresh Henhouse clone from GitHub (or updated local copy)
- Must be logged in as a user with access to both source and target directories

**Upgrade Process**:

1. **Clone Fresh Henhouse** (or update existing clone):
   ```bash
   cd ~
   git clone https://github.com/henhouseai/henhouse.git
   # Or if you already have a clone:
   cd ~/henhouse
   git pull origin main
   ```

2. **Change to Fresh Henhouse Directory**:
   ```bash
   cd ~/henhouse
   ```
   **CRITICAL**: You MUST be inside the fresh Henhouse directory when running upgrade. The upgrade command uses `detect_project_context()` which walks up from the current working directory looking for an `hh/` folder.

3. **Run Upgrade Command**:
   ```bash
   python hen.py upgrade --target /path/to/existing/project
   ```
   For example, if upgrading foxhouse:
   ```bash
   python hen.py upgrade --target /root/foxhouse
   ```

**What the Upgrade Command Does**:

1. **Validates Target**: Checks that target directory exists, contains `hh/` folder, is not the same as source, and is not a parent of source
2. **Creates Backup**: Creates a backup of the existing `hh/` folder as `hh_backup/` (or `hh_backup_2/`, `hh_backup_3/`, etc. if backups already exist)
3. **Copies New Framework**: Copies the entire `hh/` folder from source to target, replacing the old framework code
4. **Cleans Cache Files**: Removes `__pycache__` directories, `.pyc` files, `.pyo` files, cache JSON files, and `.cache` directories from the new `hh/` folder
5. **Restores Preserved Files**: If `ext/deploy/conf/upgrade_preserve.py` exists, restores any files listed in `UPGRADE_PRESERVE` from the backup to the target
6. **Reports Results**: Shows backup location, restored files, and reminder messages

**File Preservation**:

If you've modified files in `hh/` directly (not recommended), you can preserve them during upgrades by creating `ext/deploy/conf/upgrade_preserve.py`:

```python
# ext/deploy/conf/upgrade_preserve.py
UPGRADE_PRESERVE = [
    'hh/gateway/custom.py',  # Path relative to project root
    'hh/some/other/file.py',
]
```

**Warning**: Preserving files in `hh/` is risky. Prefer moving customizations to `ext/` instead. Preserved files may become incompatible with framework upgrades.

**After Upgrade**:

1. **Test the Upgraded Project**: Verify that everything still works:
   ```bash
   cd /path/to/existing/project
   fox dependency-list  # Or whatever your project command is
   ```

2. **Deploy if Needed**: If you're upgrading a production project, deploy the upgraded code:
   ```bash
   sudo fox deploy
   ```

3. **Clean Up Backups**: Once you've verified everything works, you can remove old backups:
   ```bash
   rm -rf /path/to/existing/project/hh_backup*
   ```

**Key Points**:
- **`ext/` folder is never touched**: Your customizations in `ext/` are completely safe during upgrades
- **Backup is created automatically**: Always creates a backup before replacing `hh/`
- **Preserved files are optional**: Only needed if you've modified `hh/` files directly
- **Upgrade is reversible**: You can restore from backup if something goes wrong

**Example - Upgrading foxhouse from fresh henhouse clone**:

```bash
# 1. Clone fresh Henhouse
cd ~
git clone https://github.com/henhouseai/henhouse.git

# 2. Change to fresh Henhouse directory
cd ~/henhouse

# 3. Run upgrade
python hen.py upgrade --target /root/foxhouse

# 4. Test upgraded project
cd /root/foxhouse
fox dependency-list

# 5. Deploy if needed
sudo fox deploy

# 6. Clean up backups (after verifying everything works)
rm -rf /root/foxhouse/hh_backup*
```

**Troubleshooting Upgrades**:

- **"Target directory does not exist"**: Check that the path to your existing project is correct
- **"Target cannot be the same as source"**: Make sure you're running upgrade from a different directory than the target
- **"Target does not contain hh/ folder"**: Verify the target is a valid Henhouse project
- **Preserved files not restored**: Check that `ext/deploy/conf/upgrade_preserve.py` exists and contains correct paths (relative to project root)

## Integration Points

All workflows integrate with:

- **Git Operations** (`git.md`): `pull_project`, `push_project` for code sync
- **Stage Script** (`stage.py`/`stage.ps1`): Interactive tools for managing stage branches on laptop (`stage pull`, `stage push`, `stage find`)
- **File Deployment** (`file-deployment.md`): `deploy` script for copying files
- **Service Management**: Automatic daemon restart (Flask - see `flask.md`, maintenance - see `maintenance.md`)
- **Cache Management** (`cache.md`): Automatic cache clearing on pull
- **Database** (`database.md`): No database changes needed for code deployments
- **HTTP/NGINX** (`http-nginx.md`): No reconfiguration needed for code deployments

## Component Dependencies

Understanding the dependencies helps when troubleshooting:

1. **Installation** (`installation.md`) must be done first - creates users, groups, git repo
2. **Database** (`database.md`) depends on installation - uses credential files created during installation
3. **File Deployment** (`file-deployment.md`) depends on installation - uses users/groups for permissions
4. **Flask** (`flask.md`) depends on installation and file deployment - runs as tier users, uses deployed files
5. **HTTP/NGINX** (`http-nginx.md`) depends on installation and file deployment - uses auth files, serves deployed files
6. **Maintenance** (`maintenance.md`) depends on installation, file deployment, and database - runs as root user, uses deployed tools, queries databases
7. **Git Operations** (`git.md`) depend on installation - uses git repo created during installation
8. **Cache Management** (`cache.md`) is used by all systems - clears caches during deployment and pull operations
9. **Configuration** (`configuration.md`) is used by all systems - whitelists control what gets deployed
10. **Site Assets** (`site-assets.md`) are deployed by file deployment and served by HTTP/NGINX
11. **User Management** (`user-management.md`) is the inverse of installation - removes everything created during installation

## Troubleshooting Workflows

**If deployment fails**:
1. Check service status: `hen flask-status` (see `flask.md`), `hen maintenance-status` (see `maintenance.md`)
2. Check logs: `/srv/{project_name}/logs/` (created by file deployment - see `file-deployment.md`)
3. Verify permissions: Files should be owned by `{project_name}_root:{project_name}_deploy` (see `installation.md` and `file-deployment.md`)
4. Check cache: Run `hen clear-cache` (see `cache.md`) to clear stale caches
5. Verify whitelists: Check `hh/deploy/conf/` whitelists (see `configuration.md`) to ensure files are included

**If services won't start**:
1. Check user exists: `id {project_name}_root` (see `installation.md`)
2. Check database connectivity: `hen check-db` (see `database.md`)
3. Check file permissions: Files in `/srv/{project_name}` should have correct ownership (see `file-deployment.md`)
4. Check logs: `/srv/{project_name}/logs/` for error messages

**If git operations fail**:
1. Verify git repo exists: `/srv/{project_name}/git/{project_name}.git` (created by installation - see `installation.md`)
2. Check remote configuration: `git remote -v`
3. Verify SSH access: Test SSH connection to remote repository

See individual component documentation for more detailed troubleshooting:
- `installation.md` - User and group setup
- `database.md` - Database connectivity
- `file-deployment.md` - File copying and permissions
- `flask.md` - Web application issues
- `http-nginx.md` - Web server configuration
- `maintenance.md` - Background daemon issues
- `git.md` - Code synchronization
- `cache.md` - Cache cleanup issues
- `configuration.md` - Whitelist configuration

