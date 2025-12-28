# Installation System

The installation system creates the complete user and group infrastructure needed for a Henhouse deployment. It sets up four tier-based system users, transfers SSH keys, creates credential files, initializes git repositories, and configures entry points.

## Prerequisites

Before running the installation system, you must have:
- **Sudo/root privileges** on the target system
- **Four passwords ready** (one for each tier: guest, verified, admin, root)
- **Passwordless SSH keys set up**: You MUST have passwordless SSH keys configured in the project owner's `~/.ssh/` directory BEFORE running install. The install command scans `~/.ssh/authorized_keys` from the project owner's account and copies all keys to all tier users.
- **Project folder with `hh/` directory structure**
- **Logged in as project owner**: You MUST be logged in as the user who owns the project directory. The install command detects the project owner from directory ownership (UID lookup) and uses that user's SSH keys.
- **Inside project directory**: You MUST `cd` into the project directory before running install. The install command uses `detect_project_context()` which walks up from the current working directory (`Path.cwd()`) looking for an `hh/` folder. If you run install from outside the project directory, it will not find the project.

The installation system is the **first step** in deploying Henhouse. All other deployment components (database, file deployment, Flask applications, HTTP/NGINX, maintenance daemon) depend on the users and groups created by this system.

## Install Command

**File**: `hh/deploy/users/install.py`

**Root install config and manifest**:
- First install run creates `/root/.{project}-install.cnf` (600, root). Edit required fields, then rerun install.
- `manifest_users` section records per-user data as JSON: `{uid, installed_at, removed_at}`. Install writes `installed_at`; uninstall sets `removed_at`. Manifest entries must be cleared manually before reinstall.
- `manifest_sites` section records deployed domains (http/https) with timestamps. `http_deploy`/`http_deploy_ssl` add entries; `http_remove` removes entries. Uninstall will refuse to run while `manifest_sites` has entries—remove sites first.

The `install` command performs complete system initialization:

**Prerequisites**:
- **Must run with sudo/root privileges** (checked via `gateway.os.require_privileged()`)
- **Requires 4 passwords** (one per tier: guest, verified, admin, root)
- Password arguments: `-password1/-pwd1/-p1`, `-password2/-pwd2/-p2`, `-password3/-pwd3/-p3`, `-password4/-pwd4/-p4`
- **CRITICAL: Must be inside project directory**: The install command uses `detect_project_context()` which starts from `Path.cwd()` (current working directory) and walks up looking for an `hh/` folder. You MUST `cd` into the project directory before running install.
- **CRITICAL: Must be logged in as project owner**: The install command detects the project owner from directory ownership (UID lookup). You MUST be logged in as the user who owns the project directory.
- **CRITICAL: Passwordless SSH keys must be set up BEFORE install**: The install command scans the project owner's `~/.ssh/authorized_keys` file. You MUST have passwordless SSH keys configured in the project owner's account BEFORE running install.
- Optional: `-hen <script_name>` to use custom script name (defaults to 'hen')
- Optional: `-user_key <ssh_key>` to add additional SSH key to all users
- Optional: `-clean` to remove existing .git directory before reinstall

**Project Detection**:
- **Project name**: Automatically detected from folder name containing `hh/` directory. The `detect_project_context()` function walks up from the current working directory (`Path.cwd()`) until it finds a directory containing an `hh/` folder, then uses that directory's name as the project name.
- **Project owner**: Automatically detected from folder ownership (UID lookup). The function uses `detect_project_owner(project_path)` which looks up the UID of the project directory and finds the corresponding username.
- These values determine file ownerships, permissions, and user access throughout deployment

## Installation Process Flow

1. **Validation**:
   - Checks for existing setup (users, groups, directories, git repo)
   - Checks for script name conflicts in `/root/` and project owner's home
   - Validates all four passwords are provided

2. **Core Groups Creation** (before users):
   - `{project_name}` - Main project group
   - `{project_name}_deploy` - Deployment group (all tier users)
   - `{project_name}_admin` - Admin group (admin tier user's primary group)

3. **User Creation**:
   - Creates 4 system users: `{project_name}_guest`, `{project_name}_verified`, `{project_name}_admin`, `{project_name}_root`
   - Each user: system user (`-r` flag), `/bin/bash` shell, home directory at `/home/{user}`
   - Admin tier user gets `{project_name}_admin` as primary group
   - All users get `{project_name}_deploy` as supplementary group
   - Highest tier (root) user gets both `{project_name}` and `{project_name}_deploy` groups

4. **SSH Key Management**:
   - **Auto-scan**: Scans project owner's `~/.ssh/authorized_keys` file (all non-comment lines)
   - **Generate**: Creates new SSH keypair for each tier user (`ssh-keygen -t rsa -b 4096`)
   - **Transfer**: Adds all discovered keys (auto-scanned + user-provided) to each tier user's `authorized_keys`
   - All users own their own `.ssh` directories and files

5. **Credential Files**:
   - Creates `~/.{project_name}.cnf` for each tier user
   - Format: INI-style with `[client]` section containing `user`, `password`, `host=db.{project_name}.ai` (DB subdomain), `database={project_name}`
   - Permissions: `0o600` (read/write for owner only)
   - Owned by respective user
   - These credential files are used by the database deployment system (see `database.md`) to create MySQL users

6. **Git Repository Setup**:
   - Creates `/srv/{project_name}/git/{project_name}.git` bare repository
   - Initializes git in project folder if not already a repo
   - Configures git user: `{project_name} System` / `system@{project_name}.local`
   - Creates initial commit with all files
   - Renames branch to `{project_name}` (regardless of git default)
   - Adds bare repo as `origin` remote and pushes
   - Sets bare repo HEAD to `{project_name}` branch
   - Ownership: `{project_owner}:{project_name}` with `0o770` directories, `0o660` files
   - This git repository is used by the git operations system (see `git.md`) for code synchronization

7. **Entry Points**:
   - **Tier users**: Creates `gateway.py` and `{hen_script_name}` in each user's home
     - `gateway.py`: Modified `hen.py` with `/srv/{project_name}` added to Python path
     - `{hen_script_name}`: Wrapper script that calls `python3 gateway.py "$@"`
   - **Project owner (human user)**: Creates `{hen_script_name}` in `/home/{project_owner}/`
     - Points to project folder's `hen.py` (for testing experimental code)
   - **Root user**: Creates `{hen_script_name}` in `/root/`
     - Points to project folder's `hen.py` with cache cleanup after execution

8. **PATH Configuration**:
   - Updates `.profile` for all tier users: `export PATH="/home/{user}:$PATH"`
   - Updates `.profile` for project owner and root: `export PATH="{user_home}:/root:$PATH"`
   - All users can now run `hen` command from anywhere

**Developer Box Wrapper Scripts**:

The project includes wrapper scripts for developer boxes (laptops/desktops) on all major operating systems:

- **Windows**: `hen.ps1` and `stage.ps1` (PowerShell scripts)
- **Mac/Linux**: `hen.sh` and `stage.sh` (bash scripts)

These scripts change to the project directory and run the Python scripts, allowing you to use `hen` and `stage` commands from anywhere.

**Setup Process**:

1. **Add project folder to PATH**:
   - **Windows**: Add the project folder (e.g., `C:\Users\username\Desktop\henhouse`) to your user PATH environment variable via System Properties → Environment Variables
   - **Mac/Linux**: Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):
     ```bash
     export PATH="/path/to/henhouse:$PATH"
     ```

2. **Make scripts executable** (Mac/Linux only):
   ```bash
   chmod +x hen.sh stage.sh
   ```

3. **Optional: Remove extensions** (Mac/Linux only):
   ```bash
   mv hen.sh hen
   mv stage.sh stage
   ```
   This lets you type `hen` instead of `hen.sh`. On Windows, PowerShell automatically recognizes `.ps1` files.

After setup, you can use `hen` and `stage` commands from any directory. The scripts are already marked as executable in git (for Mac/Linux), so they'll be executable when cloned.

9. **HTTP Basic Auth Files**:
   - Creates `/var/www/.htpasswd_{admin_tier}` for admin subdomain
   - Creates `/var/www/.htpasswd_panel` for root/panel subdomain
   - Uses `htpasswd -b` for batch mode password setting
   - These files are used by the HTTP/NGINX deployment system (see `http-nginx.md`) for subdomain authentication

10. **Directory Setup**:
    - Creates `/srv/images/{project_name}` with `deleted/` subdirectory
    - Creates `/srv/files/{project_name}` with `deleted/` subdirectory
    - Creates `/srv/audio/{project_name}` with `deleted/` subdirectory
    - Creates `/srv/video/{project_name}` with `deleted/` subdirectory
    - Permissions: `0o2775` (setgid for group write), owned by `{project_name}_root:{project_name}_admin`
    - These directories are used by the file deployment system (see `file-deployment.md`) for storing uploaded images, files, audio, and video

11. **Group Membership**:
    - Adds current user (running install) to all project groups
    - Adds project owner to all project groups
    - Adds `www-data` to `{project_name}_deploy` and `{project_name}_admin` groups
    - This allows NGINX (running as `www-data`) to access files needed for web serving

12. **Project Ownership**:
    - Sets entire project folder ownership to `{project_owner}:{project_name}`
    - Sets setgid bit (`0o2750`) on directories so new files inherit group ownership

**See also**: `hh/deploy/users/install.py` function `install`

## User Account Utilities

**File**: `hh/deploy/users/user_accounts.py`

Provides helper functions for user account management:

- **`create_user_config_file(user, project_name, password)`**: Creates credential file
- **`update_user_paths(project_name)`**: Updates PATH in all tier users' `.profile` files
- **`create_user_gateway_scripts(project_name, hen_script_name)`**: Creates `gateway.py` for tier users
- **`create_user_hen_scripts(project_name, hen_script_name)`**: Creates `hen` wrapper scripts for tier users
- **`setup_user_entry_points(...)`**: Sets up entry points for human/root users
- **`setup_human_user_home(...)`**: Sets up project owner's home directory
- **`setup_root_user_script(...)`**: Sets up root user's convenience script with cache cleanup
- **`detect_project_owner(project_path)`**: Detects project folder owner via UID lookup

## SSH Key Management

**File**: `hh/deploy/users/access.py`

Provides SSH key scanning and management:

- **`auto_scan_user_keys(project_owner)`**: Scans project owner's SSH keys
  - Reads `~/.ssh/authorized_keys` (all non-comment lines)
  - Returns list of public keys
- **`generate_ssh_keys(user, project_name)`**: Generates new SSH keypair for user
  - Creates `~/.ssh/id_rsa` and `~/.ssh/id_rsa.pub`
  - Returns public key and file paths
- **`add_user_key(user, user_key)`**: Adds SSH key to user's `authorized_keys`
  - Appends key to `~/.ssh/authorized_keys`
  - Sets proper ownership

## User Tier Configuration

**File**: `hh/deploy/conf/user_account_suffixes.py`

Defines the four user tiers:

- **`HENHOUSE_TIERS`**: `['guest', 'verified', 'admin', 'root']`
- Used throughout deployment system to generate user names: `{project_name}_{tier}`
- Order matters: first is lowest privilege, last is highest privilege

This configuration is used by:
- Installation system (this document) - creates users
- Database deployment system (`database.md`) - creates database users with tier-specific permissions
- Flask application management (`flask.md`) - creates tier-specific Flask instances
- HTTP/NGINX deployment (`http-nginx.md`) - routes subdomains to tier-specific Flask apps
- File deployment (`file-deployment.md`) - sets tier-based file permissions

## Integration with Other Systems

The installation system is the foundation for all other deployment components:

1. **Database Deployment** (`database.md`): Uses credential files created during installation to set up MySQL users with tier-specific permissions.

2. **File Deployment** (`file-deployment.md`): Uses the users and groups created here to set proper file ownership and permissions in `/srv/{project_name}`.

3. **Flask Application Management** (`flask.md`): Each Flask daemon runs as its corresponding tier user (`{project_name}_{tier}`), using the credentials and permissions established during installation.

4. **HTTP/NGINX Deployment** (`http-nginx.md`): Uses the HTTP Basic Auth files (`.htpasswd_admin`, `.htpasswd_panel`) created during installation to protect admin and panel subdomains.

5. **Maintenance Daemon** (`maintenance.md`): The maintenance worker runs as `{project_name}_root` user, using the highest tier user created during installation.

6. **Git Operations** (`git.md`): Uses the git repository created during installation for code synchronization between development and production.

7. **Cache Management** (`cache.md`): Cache directories use the deploy group created during installation to allow all tier users to write cache files via group permissions.

8. **Configuration System** (`configuration.md`): The user tier configuration (`HENHOUSE_TIERS`) is defined in `hh/deploy/conf/user_account_suffixes.py` and used throughout the deployment system.

9. **User Management** (`user-management.md`): The uninstall command removes all users, groups, and infrastructure created by the install command.

## Next Steps

After running the `install` command, proceed with:

1. **Database Setup**: Run `init-db` and `add-db-users` (see `database.md`)
2. **Initial Deployment**: Run `deploy` to copy files to `/srv/{project_name}` (see `file-deployment.md`)
3. **HTTP Configuration**: Run `http-deploy` and optionally `http-deploy-ssl` (see `http-nginx.md`)
4. **Start Services**: The `deploy` command automatically starts Flask and maintenance daemons

See `workflows.md` for complete deployment workflow documentation.

