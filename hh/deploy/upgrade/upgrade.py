import importlib.util
import shutil
from pathlib import Path
from typing import List, Optional
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.deploy_utils import detect_project_context

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def validate_target(target_path: Path, source_path: Path) -> bool:
    """Validate that target is a legitimate Henhouse project and is not the same as source."""
    trace_in()
    if not target_path.exists():
        warn(f"Target directory does not exist: {target_path}")
        report_error("action", f"Target directory does not exist: {target_path}")
        trace_out()
        return False
    
    # Check target is not same as source
    if target_path.resolve() == source_path.resolve():
        warn(f"Target cannot be the same as source: {target_path}")
        report_error("action", f"Target cannot be the same as source: {target_path}")
        trace_out()
        return False
    
    # Check target is not parent of source
    try:
        source_path.resolve().relative_to(target_path.resolve())
        warn(f"Target cannot be a parent of source: {target_path}")
        report_error("action", f"Target cannot be a parent of source: {target_path}")
        trace_out()
        return False
    except ValueError:
        pass  # Good - target is not a parent
    
    hh_path = target_path / "hh"
    if not hh_path.exists():
        warn(f"Target does not contain hh/ folder: {target_path}")
        report_error("action", f"Target does not contain hh/ folder: {target_path}")
        trace_out()
        return False
    
    if not (hh_path / "__init__.py").exists():
        warn(f"hh/ folder missing __init__.py")
        report_error("action", f"hh/ folder missing __init__.py")
        trace_out()
        return False
    
    if not (hh_path / "gateway" / "gateway.py").exists():
        warn(f"Not a valid Henhouse project - missing gateway")
        report_error("action", f"Not a valid Henhouse project - missing gateway")
        trace_out()
        return False
    
    log(f"Target validation passed: {target_path}")
    trace_out()
    return True


def create_backup(target_path: Path) -> Path:
    """Create backup of hh/ folder with incrementing names if backup already exists."""
    trace_in()
    hh_path = target_path / "hh"
    
    if not hh_path.exists():
        warn(f"hh/ folder does not exist: {hh_path}")
        report_error("action", f"hh/ folder does not exist: {hh_path}")
        trace_out()
        raise ValueError(f"hh/ folder does not exist: {hh_path}")
    
    # Find available backup name
    backup_name = "hh_backup"
    backup_path = target_path / backup_name
    counter = 2
    
    while backup_path.exists():
        backup_name = f"hh_backup_{counter}"
        backup_path = target_path / backup_name
        counter += 1
    
    # Rename hh/ to backup (atomic operation)
    hh_path.rename(backup_path)
    log(f"Created backup: {backup_path}")
    trace_out()
    return backup_path


def copy_hh(source_path: Path, target_path: Path) -> bool:
    """Copy hh/ folder from source to target, then clean up cache files."""
    trace_in()
    source_hh = source_path / "hh"
    target_hh = target_path / "hh"
    
    if not source_hh.exists():
        warn(f"Source hh/ folder does not exist: {source_hh}")
        report_error("action", f"Source hh/ folder does not exist: {source_hh}")
        trace_out()
        return False
    
    try:
        # Copy entire hh/ folder (no exclusions)
        shutil.copytree(source_hh, target_hh)
        log(f"Copied hh/ to {target_hh}")
    except Exception as e:
        warn(f"Failed to copy hh/ folder: {e}")
        report_error("action", f"Failed to copy hh/ folder: {e}")
        trace_out()
        return False
    
    # Clean up cache files (same pattern as deploy.py)
    cache_cleaned = {
        'pycache_dirs': 0,
        'pyc_files': 0,
        'pyo_files': 0,
        'cache_files': 0,
        'cache_dirs': 0
    }
    
    try:
        # Remove __pycache__ directories
        for pycache_dir in target_hh.rglob('__pycache__'):
            shutil.rmtree(pycache_dir)
            cache_cleaned['pycache_dirs'] += 1
            log(f"Removed __pycache__ directory: {pycache_dir}")
        
        # Remove .pyc files
        for pyc_file in target_hh.rglob('*.pyc'):
            pyc_file.unlink()
            cache_cleaned['pyc_files'] += 1
            log(f"Removed .pyc file: {pyc_file}")
        
        # Remove .pyo files
        for pyo_file in target_hh.rglob('*.pyo'):
            pyo_file.unlink()
            cache_cleaned['pyo_files'] += 1
            log(f"Removed .pyo file: {pyo_file}")
        
        # Remove cache files
        cache_patterns = ['*-reg.json', '*.cycle.json', 'cache.json', '*.cache']
        for pattern in cache_patterns:
            for cache_file in target_hh.rglob(pattern):
                cache_file.unlink()
                cache_cleaned['cache_files'] += 1
                log(f"Removed cache file: {cache_file}")
        
        # Remove .cache directories
        for cache_dir in target_hh.rglob('.cache'):
            shutil.rmtree(cache_dir)
            cache_cleaned['cache_dirs'] += 1
            log(f"Removed .cache directory: {cache_dir}")
        
        log(f"Cache cleanup complete: {cache_cleaned['pycache_dirs']} __pycache__ dirs, {cache_cleaned['pyc_files']} .pyc files, {cache_cleaned['pyo_files']} .pyo files, {cache_cleaned['cache_files']} cache files, {cache_cleaned['cache_dirs']} .cache dirs")
    except Exception as e:
        warn(f"Failed to clean cache files: {e}")
        report_error("action", f"Failed to clean cache files: {e}")
        trace_out()
        return False
    
    trace_out()
    return True


def restore_preserved(target_path: Path, backup_path: Path) -> List[str]:
    """Restore files from backup that are listed in upgrade_preserve.py."""
    trace_in()
    restored_files = []
    
    # Load UPGRADE_PRESERVE from ext/deploy/conf/upgrade_preserve.py
    preserve_file = target_path / "ext" / "deploy" / "conf" / "upgrade_preserve.py"
    preserve_list: List[str] = []
    
    if preserve_file.exists():
        try:
            # Load module using importlib
            spec = importlib.util.spec_from_file_location("upgrade_preserve", preserve_file)
            if spec is None or spec.loader is None:
                warn(f"Failed to create module spec for {preserve_file}")
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'UPGRADE_PRESERVE'):
                    preserve_list = getattr(module, 'UPGRADE_PRESERVE')
                    log(f"Loaded UPGRADE_PRESERVE: {len(preserve_list)} files")
                else:
                    warn(f"UPGRADE_PRESERVE not found in {preserve_file}")
        except Exception as e:
            warn(f"Error loading upgrade_preserve.py: {e}")
            report_error("action", f"Failed to load upgrade_preserve.py: {e}")
    else:
        log("No upgrade_preserve.py found, skipping file restoration")
    
    # Restore each file
    for rel_path in preserve_list:
        backup_file = backup_path / rel_path
        target_file = target_path / rel_path
        
        if backup_file.exists():
            try:
                # Ensure parent directory exists
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                restored_files.append(rel_path)
                log(f"Restored: {rel_path}")
            except Exception as e:
                warn(f"Failed to restore {rel_path}: {e}")
                report_error("action", f"Failed to restore {rel_path}: {e}")
        else:
            warn(f"Preserved file not found in backup: {rel_path}")
    
    log(f"Restored {len(restored_files)} files from backup")
    trace_out()
    return restored_files


def report_results(target_path: Path, backup_path: Path, restored_files: List[str]) -> dict:
    """Create result payload for upgrade operation."""
    trace_in()
    result_data = {
        "target": str(target_path),
        "backup": str(backup_path),
        "backup_name": backup_path.name,
        "restored_files": restored_files,
        "restored_count": len(restored_files),
        "status": "upgraded"
    }
    trace_out()
    return result_data


@register_action('upgrade')
@register_command('upgrade')
def do_upgrade() -> bool:
    """Main upgrade function."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Get source (current Henhouse repo) using detect_project_context()
    source_name, source_path = detect_project_context()
    log(f"Source project: {source_name} at {source_path}")
    
    # Get target from --target argument
    target_arg = gateway.get_arg('target')
    if not target_arg:
        warn("--target argument is required")
        report_error("action", "--target argument is required")
        trace_out()
        return False
    
    target_path = Path(target_arg).resolve()
    log(f"Target project: {target_path}")
    
    # Validate target
    if not validate_target(target_path, source_path):
        trace_out()
        return False
    
    # Create backup
    try:
        backup_path = create_backup(target_path)
    except Exception as e:
        warn(f"Failed to create backup: {e}")
        report_error("action", f"Failed to create backup: {e}")
        trace_out()
        return False
    
    # Copy new hh/
    if not copy_hh(source_path, target_path):
        trace_out()
        return False
    
    # Restore preserved files
    restored_files = restore_preserved(target_path, backup_path)
    
    # Report results
    result = not is_error()
    if result:
        log("Upgrade completed successfully")
        result_data = report_results(target_path, backup_path, restored_files)
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Upgrade encountered problems")
    
    trace_out()
    return result

