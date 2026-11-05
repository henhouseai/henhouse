# Chapter 16: Upgrading the Framework

## Overview

`upgrade` replaces the framework code in an existing project with the code from a newer Henhouse checkout, without touching your customizations in `ext/`.

The framework is made of module folders (see `context/modules.md`). An upgrade replaces:

- `hh/`
- every other top-level folder in the source that has a `__module__.py` (for example `hh_page/`, `hh_video/`, `maintenance/`, `users/`, `work/`, `accounting/`), except `ext/`
- `context/` and `README/`
- the top-level files (`hen.py`, `mcp_wrapper.py`, `README.md`, ...)

It never touches:

- `ext/`
- module folders that exist only in the target (a project's own modules)
- the database
- the deployed copy in `/srv/{project_name}/` (run `deploy` afterwards)

Modules turned off in the target's `ext/deploy/conf/module_blacklist.py` are still copied, and stay turned off.

## Prerequisites

1. **Existing project**: a Henhouse project (it must have `hh/gateway/gateway.py`)
2. **Newer Henhouse checkout**: a clone of `henhouseai/henhouse` on the `henhouse` branch
3. **Access**: your user can read the source and write the target

## Upgrade Process

### Step 1: Get the newer code

```bash
cd ~
git clone git@github.com:henhouseai/henhouse.git
# Or, in an existing clone:
cd ~/henhouse
git pull origin henhouse
```

### Step 2: Preview the upgrade

Run the command from **inside the newer checkout**. It uses `detect_project_context()`, which walks up from the current directory to find the source project.

```bash
cd ~/henhouse
python3 hen.py upgrade --target /path/to/existing/project -dry-run
```

The dry run lists the folders that will be replaced and every file that will be created, updated, lost, restored or preserved. Nothing is changed.

### Step 3: Run the upgrade

```bash
python3 hen.py upgrade --target /path/to/existing/project
```

## What the Command Does

The implementation is `hh/deploy/upgrade/upgrade.py`.

1. **Validate**: the target exists, is not the source or a parent of it, and is a Henhouse project.
2. **Load the preserve list** from the target's `ext/deploy/conf/upgrade_preserve.py`.
3. **Compare** each folder that will be replaced, and the top-level files, against the source. Generated cache files (`__pycache__`, `*-reg.json`, `module*.json`, ...) are ignored.
4. **Back up**: creates `backup/` in the target (or `backup_2/`, `backup_3/`, ... if it exists) and moves the target's copies of those folders and its top-level files into it.
5. **Copy** each folder and the top-level files from the source. Cache files are left out, so the target rebuilds its registries on the next run.
6. **Restore** every file listed in `UPGRADE_PRESERVE` from the backup.

All file operations are scheduled and run together when the command finishes. If one fails, the gateway rolls the others back.

## Preserving Edited Framework Files

If you changed a framework file directly (not recommended), list it in the target's `ext/deploy/conf/upgrade_preserve.py`. Paths are relative to the project root and can point into any module folder:

```python
UPGRADE_PRESERVE = [
    'hh/gateway/custom.py',
    'hh_page/my_tweak.py',
]
```

**Warning**: preserved files can break against newer framework code. Prefer moving the change into `ext/` or into a module of your own.

## After Upgrading

### Test the project

```bash
cd /path/to/existing/project
{hen_script_name} command-list
```

Check that your `ext/` customizations still work and the database connects.

### Deploy

```bash
sudo {hen_script_name} deploy
```

This copies the upgraded code to `/srv/{project_name}/` and restarts the Flask and maintenance daemons.

If the new code adds tables for a module (a new `deploy/db/schema.sql`), run the matching SQL by hand or re-run `init-db` on a fresh database. `upgrade` does not change the database.

### Remove the backup

Once everything works:

```bash
cd /path/to/existing/project
rm -rf backup
```

Keep the most recent backup until you are sure the upgrade is stable.

## Troubleshooting

**"Target does not contain hh/ folder"**: the `--target` path is wrong, or it is not a Henhouse project.

**"Target cannot be the same as source"**: you ran the command from inside the project you are upgrading. `cd` into the newer checkout first.

**A file you changed disappeared**: it is in `backup/` at the same relative path. Copy it back, and add it to `UPGRADE_PRESERVE` (or move the change into `ext/`) before the next upgrade.

**Upgrading a project from before module folders (January 2026 layout)**: the upgrade adds all the module folders, but code in that project's `ext/` that imports old paths such as `hh.page.page` must be moved to the new paths (`hh_page.page`) by hand.
