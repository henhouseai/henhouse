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

Stage branches provide a mechanism for recovering and referencing previous working states:

1. **Create Stage Branch from Server**:
   ```bash
   hen push_project --message "emergency revert - {description}"
   ```
   - Creates timestamped stage branch: `stage/linux/{timestamp}-{description}` (see `git.md`)
   - Pushes current server state to remote
   - Creates `stage` signal file in repository

2. **Pull Stage Branch on Laptop**:
   ```bash
   hen pull_project
   ```
   - Or manually: `git checkout stage/linux/{timestamp}-{description}`
   - Extracts the stage branch to local repository (see `git.md`)

3. **Access Stage Folder**:
   - After pull, `{repo_root}/stage` file contains the recovery message
   - Can use this to:
     - **Manual Recovery**: Review files in that commit, copy specific files back
     - **Agent Recovery**: Point agent to stage folder: "Look in the stage folder, see the previous working version that you forgot how it worked. I've recovered a copy for you."
     - **Interactive Recovery**: Use git's interactive tools to selectively restore files

4. **Selective File Recovery** (Optional):
   ```bash
   git checkout stage/linux/{timestamp}-{description} -- {file_path}
   ```
   - Restores specific files from stage branch
   - Allows granular recovery without full rollback

**Result**: Previous working state available for reference and recovery.

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

## Complete Workflow Summary

**Initial Setup** (One-time):
1. `sudo hen install` - Create users, groups, SSH keys, git repo (see `installation.md`)
2. `sudo hen init_db` - Initialize databases (see `database.md`)
3. `sudo hen add_db_users` - Create database users (see `database.md`)
4. `sudo hen http_deploy` - Configure NGINX (HTTP) (see `http-nginx.md`)
5. `sudo hen http_deploy_ssl` - Configure NGINX (HTTPS, optional) (see `http-nginx.md`)
6. `sudo hen deploy` - Deploy initial code (see `file-deployment.md`)

**Ongoing Operations** (Repeatable):
- **Standard Deploy**: `hen pull_project` (see `git.md`) → `sudo hen deploy` (see `file-deployment.md`)
- **Rollback**: `git reset --hard {hash}` → `sudo hen deploy` (see `file-deployment.md`)
- **Recovery**: `hen push_project --message "..."` (see `git.md`) → `hen pull_project` (see `git.md`) → review stage folder
- **Development Sync**: `hen push_project --message "..."` (laptop, see `git.md`) → `hen pull_project` + `sudo hen deploy` (server, see `git.md` and `file-deployment.md`)

**Key Benefits**:
- **Repeatable**: Same process every time
- **Reversible**: Easy rollback to any commit
- **Traceable**: Stage branches document recovery points (see `git.md`)
- **Recoverable**: Stage folder provides reference for agents/humans
- **Simple**: After setup, only two commands needed for normal deployment

## Integration Points

All workflows integrate with:

- **Git Operations** (`git.md`): `pull_project`, `push_project` for code sync
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

