# Chapter 6: Git and Staging Workflows

## Overview

After installation, you can immediately start syncing code between your developer box and deployment server using Henhouse's git and staging workflows. This chapter covers setting up git sync, using stage branches for recovery, and syncing code in both directions.

**Note**: This chapter describes one approach to git workflow. If you prefer to use git in other ways, that's perfectly fine. These tools provide convenience features like syncing from any directory and automatically clearing caches, but you can always use standard git push/pull commands if you prefer.

## Prerequisites

Before using git operations, ensure you have:

1. **Chapter 5**: Installation completed (git repository must exist)
2. **Git installed**: Git must be installed on both developer box and deployment server
3. **SSH access**: Developer box must have SSH access to deployment server

The git operations system uses the git repository (`/srv/{project_name}/git/{project_name}.git`) created during installation.

## Developer Box Setup

### Clone from Server

Once your server has a valid domain you can connect to, clone from the server instead of GitHub:

```bash
# On your developer box, clone from your server's bare repository
git clone user@your-server:/srv/{project_name}/git/{project_name}.git
cd {project_name}

# Open this folder in Cursor as a new project
# Your origin will point to the server's bare repo
```

This sets up your developer box to sync directly with the deployment server.

### Optional: Add GitHub Remote

You can add GitHub as an additional remote if you want:

```bash
# Add GitHub as additional remote (optional)
git remote add github https://github.com/henhouseai/henhouse.git
```

This allows you to pull framework updates from GitHub while keeping your server as the primary remote.

## Technical Details: Git Repository Architecture

The installation system creates a bare git repository on the server:

- **Location**: `/srv/{project_name}/git/{project_name}.git`
- **Type**: Bare repository (no working directory)
- **Branch**: `{project_name}` (not `main` or `master`)
- **Purpose**: Central repository for syncing between developer box and server

The file deployment system preserves this repository across deployments by temporarily moving it during deployment and restoring it afterward. This ensures your git history is never lost during code deployments.

The `pull-project` and `push-project` commands use `detect_project_context()` from `hh/deploy/utils.py` to automatically find the project name and repository root, so you can run these commands from any directory within the project.

## Technical Details: Project Context Detection

**Function**: `detect_project_context()` from `hh/deploy/utils.py`

This utility function is used throughout the deployment system to automatically detect project information:

- **Project name**: Automatically detected from folder name containing `hh/` directory
- **Project root**: Automatically detected by walking up from current working directory
- **Detection method**: Walks up directory tree from `Path.cwd()` until it finds a directory containing an `hh/` folder
- **Returns**: Tuple of `(project_name, project_root_path)`

**Usage**: This function is used by:
- Git operations (`pull-project`, `push-project`) - to find repository root
- File deployment (`deploy`) - to determine project name and deployment path
- Installation system - to detect project context during setup
- Cache cleanup - to determine project root for cache operations

**Critical requirement**: You must run commands from within the project directory (or any subdirectory) for automatic detection to work. The function walks up the directory tree, so it works from any subdirectory within the project.

## Basic Git Sync Workflow

### Pull Latest Code (Server)

On the deployment server, pull the latest code from remote:

```bash
{hen_script_name} pull-project
```

**What this does**:
- Fetches latest changes from remote
- Switches to `{project_name}` branch if needed
- Hard resets to `origin/{project_name}` (discards local changes)
- Automatically clears all caches
- Shows commit hash, message, and time

**Use cases**:
- Syncing server code to match remote after deployment
- Recovering to a known good state from remote
- Pulling latest changes from another development machine

### Push Changes (Developer Box or Server)

Push local changes to remote via a stage branch:

```bash
{hen_script_name} push-project --message "your descriptive message"
```

**What this does**:
- Creates a timestamped stage branch: `stage/linux/{timestamp}-{sanitized_message}`
- Stages all changes (including deletions)
- Creates a commit with structured metadata
- Pushes to remote repository
- Creates a `stage` signal file in repository root

**Requirements**:
- `--message` argument is mandatory (describes what this push is for)
- Must be run from within a git repository

## Technical Details: Pull Project Implementation

The `pull-project` command (`hh/deploy/git/pull_project.py`) performs these steps:

1. **Project Detection**: Uses `detect_project_context()` to find project name and repository root
2. **Branch Check**: Determines current branch via `git branch --show-current`
3. **Branch Switch**: Switches to `{project_name}` branch if not already on it
4. **Fetch**: Runs `git fetch origin` to get latest remote refs
5. **Hard Reset**: Runs `git reset --hard origin/{project_name}` to match remote exactly
6. **Git Info**: Extracts short hash, commit message, and relative time
7. **Cache Cleanup**: Calls `clean_all_caches()` from cache cleanup registry

The command returns status information including project name, branch status, commit details, and list of cleared cache items. All git operations use `run_git()` helper function with proper error handling that raises exceptions on failure.

## Technical Details: Integration with Cache Management

The `pull-project` command integrates automatically with the cache management system:

- **Automatic Cache Clearing**: After pulling code, `pull-project` automatically calls `clean_all_caches()` from the cache cleanup registry
- **Prevents Stale State**: Clearing caches ensures that registry caches, Python bytecode caches, and other cached files don't contain stale data from the previous code version
- **Integration Point**: This integration ensures that when code is synced from remote, all cached data is refreshed to match the new code state
- **No Manual Steps Required**: Cache clearing happens automatically as part of the pull operation - no separate cache clearing command is needed

## Technical Details: Push Project Implementation

The `push-project` command (`hh/deploy/git/push_project.py`) performs these steps:

1. **Message Validation**: Ensures `--message` argument is provided and non-empty
2. **Project Detection**: Uses `detect_project_context()` to find project name and repository root
3. **Stage Signal File**: Writes message to `{repo_root}/stage` file (UTF-8, Unix line endings)
4. **Branch Name Generation**: Creates `stage/linux/{timestamp}-{sanitized_message}` format
   - Timestamp: `YYYY-MM-DD-HHMMSS` (UTC)
   - Message sanitization: Unicode normalize, ASCII fold, lowercase, whitespace to hyphens, remove disallowed characters, collapse hyphens
5. **Branch Creation**: Uses `git checkout -B {branch}` to create or reset branch
6. **Stage Changes**: Runs `git add -A` to stage all changes
7. **Change Detection**: Checks if anything is staged (uses `--allow-empty` if no changes)
8. **Commit Creation**: Creates commit with:
   - Title: `Stage: {message}`
   - Body/Trailers:
     ```
     Stage-Done: true
     Env: linux
     Hook: {message}
     ```
9. **Push**: Runs `git push -u origin {branch}` to push and set upstream

Helper functions include:
- `run_git(repo_path, args, check=True)`: Executes git commands with error handling
- `sanitize_for_ref(text)`: Converts text to safe git ref slug
- `build_stage_names(env, hook_id, desc)`: Builds stage branch name and commit title
- `write_stage_signal(repo_path, text)`: Writes stage signal file

## Stage Branch Recovery Workflow

Stage branches provide a mechanism for recovering and referencing previous working states. The `stage` script (available as `stage.py` or `stage.ps1` on Windows) provides interactive tools for managing stage branches on your laptop.

### Create Stage Branch from Server

Create a recovery point from the current server state:

```bash
# On deployment server
{hen_script_name} push-project --message "emergency revert - {description}"
```

This creates:
- Timestamped stage branch: `stage/linux/{timestamp}-{sanitized_message}`
- Pushes current server state to remote
- Creates `stage` signal file in repository with the message

### Pull Stage Branch on Laptop

Fetch and materialize a stage branch on your developer box:

```bash
# On developer box
stage pull
```

**What this does**:
- Fetches remote branches and finds the latest stage branch
- Materializes the stage branch contents into a local `./stage` directory
- Creates a `.stage_changes.json` manifest file listing all changes (added, modified, deleted, renamed files)
- The `stage` signal file from the branch contains the recovery message

### Find Specific Stage Branch

If you have multiple stage branches and need a specific one:

```bash
# On developer box
stage find "search term"
```

This searches stage branches for one containing the search term in its message and pulls the matching stage branch if found.

### Review and Apply Changes

Review changes from a stage branch and selectively apply them:

```bash
# On developer box
stage push
```

**Interactive Review Interface**:
- **DELETE**: Files that exist in main but not in stage (would be deleted)
- **ADD**: Files that exist in stage but not in main (would be added)
- **EDIT**: Files that differ between stage and main (would be updated)
- **RENAME**: Files that were renamed (if detected in manifest)
- **WARNINGS**: Encoding, line ending, or indentation issues

For each change, you can:
- Accept (Y): Apply the change immediately to your main codebase
- Skip (N): Leave the file unchanged

After review, the `./stage` directory is automatically cleaned up.

### Manual Recovery (Alternative)

If you prefer not to use the interactive stage script:

```bash
# On developer box
git checkout stage/linux/{timestamp}-{description} -- {file_path}
```

This restores specific files from a stage branch without using the stage script, allowing granular recovery without full interactive review.

## Development-to-Production Sync Workflow

Syncing changes from your laptop to the server:

### Step 1: Push Changes from Laptop

```bash
# On developer box
{hen_script_name} push-project --message "deploy fix for X"
```

This creates a stage branch with your descriptive message and pushes all local changes to remote.

### Step 2: Pull and Deploy on Server

```bash
# On deployment server
{hen_script_name} pull-project
sudo {hen_script_name} deploy
```

This pulls the latest code and deploys it to `/srv/{project_name}/`.

**Result**: Changes synced from development to production.

## Server-to-Laptop Sync Workflow

Syncing changes from server to laptop (useful for capturing server-side changes):

### Step 1: Push Current State from Server

```bash
# On deployment server
{hen_script_name} push-project --message "server changes - {description}"
```

This creates a timestamped stage branch and pushes current server state to remote.

### Step 2: Pull Stage Branch on Laptop

```bash
# On developer box
stage pull
```

Or find a specific stage branch:

```bash
stage find "search term"
```

This materializes the stage branch contents into `./stage` directory with a manifest file.

### Step 3: Review and Apply Changes

```bash
# On developer box
stage push
```

Use the interactive review interface to selectively apply changes from the server to your development codebase.

**Use Cases**:
- Capturing emergency fixes made directly on the server
- Bringing database migrations or schema changes back to development
- Syncing content updates or configuration changes made on server
- Recovering from accidental deletions or overwrites
- Reviewing what changed on the server before integrating into main codebase

## Testing Git Sync Before Deployment

You can test the entire git sync workflow before running `deploy`. After installation, the only thing in `/srv` is the git repository, so you can:

1. **On developer box**: Make changes, commit, push
2. **On server**: Pull and verify changes
3. **On server**: Create stage branches and test recovery
4. **On developer box**: Pull stage branches and test recovery workflow

All of this works without deploying code to `/srv/{project_name}/`. The git repository is independent of the deployment system.

## Rollback Workflow

If you need to rollback to a previous commit:

### Step 1: Reset to Previous Commit

```bash
# On deployment server
cd /path/to/project
git reset --hard <commit_hash>
```

Replace `<commit_hash>` with the hash of the stable commit (find via `git log` or GitHub interface).

### Step 2: Redeploy Previous Version

```bash
# On deployment server
sudo {hen_script_name} deploy
```

This redeploys the rolled-back code state. All services restart with the previous version.

### Step 3: Document Rollback (Optional)

```bash
# On deployment server
{hen_script_name} push-project --message "revert to working version"
```

This creates a recovery point documenting the rollback.

## Integration with Deployment

Git operations integrate with the deployment system:

- **Pull before Deploy**: Standard workflow is `pull-project` → `sudo deploy`
- **Cache Clearing**: `pull-project` automatically clears all caches to prevent stale state (see Technical Details: Integration with Cache Management)
- **Repository Preservation**: File deployment preserves git repository across deployments
- **Stage Branches**: Can be checked out on server for deployment
- **Signal Files**: Stage signal file can trigger automated deployment processes
- **Workflow Integration**: `pull-project` is designed to be run before `deploy` - it prepares the codebase by syncing from remote and clearing caches, then `deploy` handles file copying and service management

## Troubleshooting

### Git Operations Fail

**Problem**: `pull-project` or `push-project` fails

**Solutions**:
1. Verify git repo exists: `/srv/{project_name}/git/{project_name}.git` (created during installation)
2. Check remote configuration: `git remote -v`
3. Verify SSH access: Test SSH connection to remote repository
4. Ensure you're in a git repository: Check for `.git` directory

### Stage Script Not Found

**Problem**: `stage pull` or `stage push` command not found

**Solutions**:
1. Verify stage script exists: `stage.py` (Mac/Linux) or `stage.ps1` (Windows) in project root
2. Check PATH: Ensure project folder is in your PATH
3. Make executable (Mac/Linux): `chmod +x stage.py`

### Branch Conflicts

**Problem**: Git operations fail with branch conflicts

**Solutions**:
1. Check current branch: `git branch --show-current`
2. Ensure on `{project_name}` branch: `git checkout {project_name}`
3. Resolve conflicts manually if needed: `git status` to see conflicts

## Next Steps

After setting up git sync:

1. **Database Setup**: Proceed to Chapter 7 to initialize the database
2. **File Deployment**: Deploy your code to `/srv/` (see Chapter 8)
3. **Deployment**: Deploy code and configure web server (see Chapter 8)

