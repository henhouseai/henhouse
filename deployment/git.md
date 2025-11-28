# Git Operations

The git operations system provides commands for syncing code between development environments (laptop) and deployment servers. It supports pulling the latest code from remote repositories and pushing changes via stage branches.

## Prerequisites

Before using git operations, you must have:
- Installation system completed (see `installation.md`) - git repository must exist
- Git installed and configured
- Remote repository access configured

The git operations system depends on the installation system because it uses the git repository (`/srv/{project_name}/git/{project_name}.git`) created during installation.

## Architecture Overview

The git system uses a stage branch workflow:
- **Pull**: Hard resets local repository to `origin/{project_name}` for clean state
- **Push**: Creates timestamped stage branches with commit messages for syncing changes
- **Project Detection**: Automatically detects project name and repository root
- **Cache Management**: Automatically clears caches after pull operations

The git repository is created by the installation system (see `installation.md`) and is preserved across deployments by the file deployment system (see `file-deployment.md`).

## Pull Project

**File**: `hh/deploy/git/pull_project.py`

Pulls the latest code from remote and resets to a clean state:

**Command**: `pull_project`

**Process Flow**:

1. **Detect Project Context**:
   - Uses `detect_project_context()` to find project name and repository root
   - Validates that repository root exists

2. **Check Current Branch**:
   - Runs `git branch --show-current` to determine current branch
   - Logs current branch name

3. **Switch to Project Branch**:
   - If not already on `{project_name}` branch, switches to it
   - Uses `git checkout {project_name}`
   - Tracks whether branch switch occurred
   - The `{project_name}` branch is created by the installation system (see `installation.md`)

4. **Fetch from Remote**:
   - Runs `git fetch origin` to get latest remote refs
   - Does not merge or modify working directory yet

5. **Hard Reset to Remote**:
   - Runs `git reset --hard origin/{project_name}`
   - **Discards all local changes** (clean state)
   - Ensures local matches remote exactly

6. **Get Git Information**:
   - **Short Hash**: `git rev-parse --short HEAD` (7 characters)
   - **Commit Message**: `git log -1 --pretty=format:%s` (first line only)
   - **Time Ago**: `git log -1 --pretty=format:%ar` (relative time)

7. **Clear All Caches**:
   - Calls `clean_all_caches()` from cache cleanup registry (see `cache.md`)
   - Clears registered caches, `__pycache__` directories, `.pyc` files
   - Collects list of cleared cache items for reporting

**Returns**: Status dict with:
- `project_name`: Project name
- `project_path`: Repository root path
- `current_branch`: Branch name before switch
- `branch_switched`: Boolean indicating if branch switch occurred
- `short_hash`: 7-character commit hash
- `commit_message`: First line of commit message
- `time_ago`: Relative time string (e.g., "2 hours ago")
- `cache_cleared`: List of cleared cache file/directory paths
- `status`: "pulled"

**Parser**: `render_pull_project.py` renders table with project info, branch status, commit details, and cache clearing results.

**Use Cases**:
- Syncing server code to match remote after deployment
- Recovering to a known good state from remote
- Pulling latest changes from another development machine
- Resetting local changes to match remote exactly

## Push Project

**File**: `hh/deploy/git/push_project.py`

Pushes local changes to remote via a stage branch:

**Command**: `push_project --message "your message"`

**Prerequisites**:
- **Message Required**: `--message` argument is mandatory
- Must be run from a git repository (validates `.git` directory exists)

**Process Flow**:

1. **Validate Message**:
   - Checks that `--message` argument is provided and non-empty
   - Returns error if message is missing

2. **Detect Project Context**:
   - Uses `detect_project_context()` to find project name and repository root
   - Validates that repository root is a git repository

3. **Create Stage Signal File**:
   - Writes message to `{repo_root}/stage` file
   - Used as a signal file for deployment processes
   - UTF-8 encoded with Unix line endings

4. **Build Stage Branch Name**:
   - Format: `stage/linux/{timestamp}-{sanitized_message}`
   - **Timestamp**: `YYYY-MM-DD-HHMMSS` (UTC)
   - **Message Sanitization**: Converts to safe git ref slug:
     - Unicode normalize and ASCII fold
     - Lowercase
     - Replace whitespace with hyphens
     - Remove disallowed characters
     - Collapse multiple hyphens
   - Example: `stage/linux/2024-01-15-143022-deploy-fix`

5. **Create/Checkout Branch**:
   - Uses `git checkout -B {branch}` to create or reset branch
   - Forces branch to current HEAD state

6. **Stage All Changes**:
   - Runs `git add -A` to stage all changes (including deletions)
   - Captures all modifications in working directory

7. **Detect Changes**:
   - Runs `git status --porcelain` to check if anything is staged
   - If no changes, uses `--allow-empty` flag for commit

8. **Create Commit**:
   - **Title**: `Stage: {message}`
   - **Body/Trailers**:
     ```
     Stage-Done: true
     Env: linux
     Hook: {message}
     ```
   - Uses `--allow-empty` if no changes detected (allows empty commits)

9. **Push to Remote**:
   - Runs `git push -u origin {branch}` to push and set upstream
   - Creates branch on remote if it doesn't exist
   - Pushes to the remote repository configured during installation (see `installation.md`)

**Returns**: Status dict with:
- `project_name`: Project name
- `project_path`: Repository root path
- `message`: Original push message
- `branch`: Created stage branch name
- `title`: Commit title
- `has_changes`: Boolean indicating if changes were committed
- `stage_file_created`: Boolean (always true)
- `status`: "pushed"

**Parser**: `render_push_project.py` renders table with project info, message, branch name, change status, and stage file creation.

**Use Cases**:
- Pushing development changes from laptop to server
- Creating deployment snapshots with descriptive messages
- Syncing code between development environments
- Creating recovery points before major changes

## Stage Branch Workflow

The stage branch system provides a structured way to sync code:

**Branch Naming Convention**:
- Format: `stage/{environment}/{timestamp}-{description}`
- **Environment**: Currently hardcoded to `"linux"` (for server deployment)
- **Timestamp**: UTC timestamp for chronological ordering
- **Description**: Sanitized message from user

**Commit Structure**:
- **Title**: Descriptive message prefixed with "Stage: "
- **Trailers**: Structured metadata for automation:
  - `Stage-Done: true` - Marks commit as stage operation
  - `Env: linux` - Deployment environment
  - `Hook: {message}` - Original user message

**Stage Signal File**:
- Created at `{repo_root}/stage` with the push message
- Used by deployment processes to detect stage operations
- UTF-8 encoded, single line

## Helper Functions

**File**: `hh/deploy/git/push_project.py`

- **`run_git(repo_path, args, check=True)`**: Executes git commands with proper error handling
  - Uses `git -C {repo_path}` for directory context
  - Returns `(exit_code, stdout, stderr)` tuple
  - Raises `RuntimeError` if `check=True` and command fails

- **`sanitize_for_ref(text)`**: Converts arbitrary text to safe git ref slug
  - Unicode normalization (NFKD)
  - ASCII folding
  - Lowercase conversion
  - Whitespace to hyphens
  - Character sanitization
  - Hyphen collapsing

- **`build_stage_names(env, hook_id, desc)`**: Builds stage branch name, tag, and title
  - Generates timestamp
  - Sanitizes hook_id and description
  - Constructs branch name and commit title

- **`write_stage_signal(repo_path, text)`**: Writes stage signal file
  - Creates `{repo_root}/stage` file
  - UTF-8 encoding with Unix line endings

## Integration with Deployment

**Pull Integration**:
- Used during deployment recovery operations
- Ensures server code matches remote exactly
- Clears caches to prevent stale state issues (uses cache management system - see `cache.md`)

**Push Integration**:
- Used to sync development changes to server
- Stage branches can be checked out on server for deployment
- Stage signal file can trigger automated deployment processes

## Configuration Labels

**File**: `hh/deploy/git/config_labels.py`

Defines render labels for CLI output:
- Git repository labels
- Pull project status labels (branch, hash, message, time)
- Push project status labels (message, branch, changes, stage file)

## Error Handling

Both commands use Gateway error reporting:
- **Pull**: Reports errors for branch switch failures, fetch failures, reset failures, cache cleanup failures
- **Push**: Reports errors for missing message, invalid repository, git command failures

All git operations use `run_git()` with `check=True` by default, which raises exceptions on failure for proper error propagation.

## Integration with Other Systems

The git operations system integrates with:

1. **Installation System** (`installation.md`): Uses the git repository (`/srv/{project_name}/git/{project_name}.git`) created during installation. The `{project_name}` branch is created during installation.

2. **File Deployment** (`file-deployment.md`): The git repository is preserved across deployments. The file deployment system moves the git folder temporarily during deployment and restores it afterward.

3. **Cache Management** (`cache.md`): Automatically clears all caches after pull operations to prevent stale state issues.

4. **Configuration System** (`configuration.md`): Uses `detect_project_context()` from `hh/deploy/utils.py` to find project name and repository root.

## Deployment Workflow

Git operations are part of the standard deployment workflow:

**Standard Deployment**:
```bash
hen pull_project    # Get latest code from remote
sudo hen deploy     # Deploy the code (see file-deployment.md)
```

**Development-to-Production Sync**:
```bash
# On laptop:
hen push_project --message "deploy fix for X"

# On server:
hen pull_project
sudo hen deploy
```

See `workflows.md` for complete deployment workflow documentation.

