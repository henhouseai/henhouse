# Chapter 16: Upgrading the Framework

## Overview

The upgrade feature allows you to upgrade the framework code (`hh/` folder) in an existing project without affecting your customizations (`ext/` folder). This is useful when you want to pull in framework improvements from a fresh Henhouse clone.

## Prerequisites

Before upgrading, ensure you have:

1. **Existing project**: Project with `hh/` and optionally `ext/` folders
2. **Fresh Henhouse clone**: Clone from GitHub (or updated local copy) with latest framework code
3. **Access**: Must be logged in as a user with access to both source and target directories

## Upgrade Process

### Step 1: Clone Fresh Henhouse

Clone a fresh copy of Henhouse (or update existing clone):

```bash
cd ~
git clone https://github.com/henhouseai/henhouse.git
# Or if you already have a clone:
cd ~/henhouse
git pull origin main
```

### Step 2: Change to Fresh Henhouse Directory

**CRITICAL**: You MUST be inside the fresh Henhouse directory when running upgrade. The upgrade command uses `detect_project_context()` which walks up from the current working directory looking for an `hh/` folder.

```bash
cd ~/henhouse
```

### Step 3: Run Upgrade Command

Run the upgrade command with the `--target` argument pointing to your existing project:

```bash
python hen.py upgrade --target /path/to/existing/project
```

**Example**: If upgrading a project called "foxhouse":

```bash
python hen.py upgrade --target /root/foxhouse
```

## Technical Details: Upgrade Command Implementation

The upgrade command (`hh/deploy/upgrade.py`) performs a safe, atomic upgrade of the framework code:

**Command**: `python hen.py upgrade --target /path/to/project`

**Process Flow**:

1. **Project Context Detection**:
   - Uses `detect_project_context()` to find source `hh/` folder (walks up from current working directory)
   - Validates source contains `hh/` folder
   - Validates target directory exists and contains `hh/` folder

2. **Target Validation**:
   - Checks target directory exists and is accessible
   - Verifies target contains `hh/` folder (must be a Henhouse project)
   - Ensures target is not the same as source (prevents self-upgrade)
   - Ensures target is not a parent of source (prevents accidental parent upgrade)
   - Validates paths are absolute (prevents relative path issues)

3. **Backup Creation**:
   - Creates backup by renaming `hh/` to `hh_backup/` (atomic operation via `os.rename()`)
   - If `hh_backup/` exists, tries `hh_backup_2/`, `hh_backup_3/`, etc. (increments until available)
   - Backup preserves entire original `hh/` folder structure

4. **Framework Copy**:
   - Copies entire `hh/` folder from source to target using `shutil.copytree()`
   - Preserves file permissions and timestamps
   - Replaces old framework code with new framework code
   - **Never touches `ext/` folder** (customizations remain intact)

5. **Cache Cleanup**:
   - Removes Python cache: `__pycache__/` directories, `.pyc`, `.pyo` files
   - Removes registry cache: `*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache` files
   - Removes cache directories: `.cache/` directories
   - Ensures clean state after upgrade

6. **File Preservation** (if configured):
   - Checks for `ext/deploy/conf/upgrade_preserve.py`
   - Reads `UPGRADE_PRESERVE` list (relative paths from project root)
   - Restores each file from backup to target (overwrites new file with preserved version)
   - Logs which files were preserved

7. **Result Reporting**:
   - Shows backup location (`hh_backup/` or `hh_backup_N/`)
   - Lists preserved files (if any)
   - Provides reminder to test and deploy

**Safety Features**:
- **Atomic backup**: Rename operation is atomic (no partial state)
- **Validation**: Multiple checks prevent accidental data loss
- **Preservation system**: Allows preserving customizations in `hh/` (though not recommended)
- **Non-destructive**: `ext/` folder never touched, database never modified

## What the Upgrade Command Does

1. **Validates Target**: 
   - Checks that target directory exists
   - Verifies target contains `hh/` folder
   - Ensures target is not the same as source
   - Ensures target is not a parent of source

2. **Creates Backup**: 
   - Creates a backup of the existing `hh/` folder as `hh_backup/`
   - If backup already exists, uses `hh_backup_2/`, `hh_backup_3/`, etc.
   - Backup is created by renaming (atomic operation)

3. **Copies New Framework**: 
   - Copies the entire `hh/` folder from source to target
   - Replaces the old framework code with new framework code
   - Preserves `ext/` folder (never touched)

4. **Cleans Cache Files**: 
   - Removes `__pycache__` directories
   - Removes `.pyc` files
   - Removes `.pyo` files
   - Removes cache JSON files (`*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache`)
   - Removes `.cache` directories

5. **Restores Preserved Files**: 
   - If `ext/deploy/conf/upgrade_preserve.py` exists, restores any files listed in `UPGRADE_PRESERVE` from the backup to the target
   - This allows you to preserve customizations you made directly in `hh/`

6. **Reports Results**: 
   - Shows backup location
   - Lists restored files (if any)
   - Provides reminder messages

## File Preservation

If you've modified files in `hh/` directly (not recommended, but sometimes necessary), you can preserve them during upgrades by creating `ext/deploy/conf/upgrade_preserve.py`:

```python
# ext/deploy/conf/upgrade_preserve.py
UPGRADE_PRESERVE = [
    'hh/gateway/custom.py',  # Path relative to project root
    'hh/some/other/file.py',
]
```

**Warning**: Preserving files in `hh/` is risky. Prefer moving customizations to `ext/` instead. Preserved files may become incompatible with framework upgrades.

## After Upgrade

### Step 1: Test the Upgraded Project

Verify that everything still works:

```bash
cd /path/to/existing/project
{hen_script_name} dependency-list  # Or whatever your project command is
```

Test key functionality:
- Run a few commands to verify they work
- Check that customizations in `ext/` still function
- Verify database connections work

### Step 2: Deploy if Needed

If you're upgrading a production project, deploy the upgraded code:

```bash
sudo {hen_script_name} deploy
```

This will:
- Copy upgraded `hh/` folder to `/srv/{project_name}/`
- Restart Flask daemons
- Restart maintenance daemon
- Clear caches

### Step 3: Clean Up Backups

Once you've verified everything works, you can remove old backups:

```bash
cd /path/to/existing/project
rm -rf hh_backup
rm -rf hh_backup_2  # If you have multiple backups
```

**Note**: Keep at least one recent backup until you're confident the upgrade is stable.

## Upgrade Safety

### What Gets Upgraded

- **`hh/` folder**: Entire framework code is replaced
- **Framework modules**: All Python modules in `hh/` are upgraded
- **Deployment scripts**: All deployment code in `hh/deploy/` is upgraded
- **Core functionality**: Gateway, Page system, Registry, etc. are upgraded

### What Doesn't Get Touched

- **`ext/` folder**: Never modified during upgrades
- **Database**: Database schema and data are not changed
- **User configs**: User configuration files are not modified
- **Deployed code**: Code in `/srv/` is not automatically upgraded (you must deploy)

### What Gets Preserved (if configured)

- **Files in `UPGRADE_PRESERVE`**: Files listed in `ext/deploy/conf/upgrade_preserve.py` are restored from backup
- **Backup folder**: Original `hh/` folder is backed up before upgrade

## Troubleshooting

### Upgrade Fails: Target Validation

**Problem**: Upgrade fails with "Target validation failed"

**Solutions**:
1. Verify target directory exists and is accessible
2. Check target contains `hh/` folder
3. Ensure target is not the same as source directory
4. Verify target is not a parent of source directory

### Customizations Break After Upgrade

**Problem**: Custom code in `ext/` stops working after upgrade

**Solutions**:
1. Check if framework APIs changed (review upgrade notes)
2. Update custom code to match new framework APIs
3. Test customizations before deploying to production
4. Review framework changelog for breaking changes

### Preserved Files Cause Issues

**Problem**: Preserved files from `UPGRADE_PRESERVE` cause errors

**Solutions**:
1. Remove problematic files from `UPGRADE_PRESERVE`
2. Move customizations to `ext/` instead of preserving in `hh/`
3. Review preserved files for compatibility with new framework
4. Test thoroughly before deploying

### Backup Creation Fails

**Problem**: Upgrade fails when creating backup

**Solutions**:
1. Check disk space (backup requires space equal to `hh/` folder)
2. Verify write permissions in target directory
3. Check for file locks on `hh/` folder
4. Ensure no processes are using files in `hh/`

## Best Practices

1. **Test upgrades in development first**: Upgrade a development copy before production
2. **Keep backups**: Don't delete backups immediately after upgrade
3. **Review changelog**: Check what changed in the framework version
4. **Move customizations to `ext/`**: Avoid preserving files in `hh/` if possible
5. **Deploy after upgrade**: Run `deploy` to update production code
6. **Test thoroughly**: Verify all functionality works after upgrade

## Upgrade Workflow Summary

**Standard Upgrade Process**:

1. Clone fresh Henhouse: `git clone https://github.com/henhouseai/henhouse.git`
2. Change to fresh clone: `cd ~/henhouse`
3. Run upgrade: `python hen.py upgrade --target /path/to/project`
4. Test upgraded project: `cd /path/to/project && {hen_script_name} dependency-list`
5. Deploy if production: `sudo {hen_script_name} deploy`
6. Clean up backups: `rm -rf hh_backup` (after verifying everything works)

## Next Steps

After learning about upgrades, you now have a complete understanding of the Henhouse deployment system. You can:

- Set up new installations
- Deploy and manage projects
- Customize via the EXT folder
- Upgrade the framework while preserving customizations

For additional information, see the other chapters in this deployment guide.

