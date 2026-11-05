import fnmatch
import importlib.util
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Set
from dataclasses import dataclass, field
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.deploy.deploy_utils import detect_project_context

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


# Folders that are copied from the source as a whole (besides module folders found by __module__.py).
DOC_FOLDERS = ("context", "README")

# Generated files never copied into the target or counted as differences (mirrors the cache entries in .gitignore).
CACHE_PATTERNS = (
    "__pycache__", ".cache", "*.pyc", "*.pyo", "*.cache",
    "*-reg.json", "*-whitelist-*.json", "*.cycle.json", "cache.json",
    "page-classes.json", "tp-decorators.json", "config-registry.json", "module*.json",
)


def get_upgrade_folders(source_path: Path) -> List[str]:
    """Folders the upgrade replaces: hh/, every other source module folder except ext/, then context/ and README/.

    Module folders the target has but the source does not (a project's own modules) are left alone, and ext/ is
    never touched.  Blacklisted modules are still copied; the target's module_blacklist keeps them switched off.
    """
    trace_in()
    modules = sorted(
        item.name for item in source_path.iterdir()
        if item.is_dir() and item.name != "ext" and (item / "__module__.py").exists()
    )
    if "hh" in modules:
        modules.remove("hh")
        modules.insert(0, "hh")
    folders = modules + [name for name in DOC_FOLDERS if (source_path / name).is_dir()]
    return trace_out(folders)


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

def create_unified_backup(target_path: Path, gateway) -> Path:
    """Pick a free backup folder name (backup, backup_2, ...) and schedule its creation. Returns its path."""
    trace_in()
    dry_run = gateway.is_set('dry-run') or gateway.is_set('dry_run')

    backup_path = target_path / "backup"
    counter = 2
    while backup_path.exists():
        backup_path = target_path / f"backup_{counter}"
        counter += 1

    if not dry_run:
        gateway.files.schedule_create_directory(str(backup_path))
        log(f"Scheduled backup directory creation: {backup_path}")
    else:
        log(f"Would create backup directory: {backup_path} (dry-run)")

    trace_out()
    return backup_path


def move_to_backup(target_path: Path, backup_path: Path, item_name: str, gateway) -> bool:
    """Move an item (folder or file) into the backup folder."""
    trace_in()
    item_path = target_path / item_name
    
    if not item_path.exists():
        log(f"{item_name} does not exist: {item_path}, skipping backup")
        trace_out()
        return False
    
    backup_item = backup_path / item_name
    gateway.files.schedule_move(str(item_path), str(backup_item))
    log(f"Scheduled backup: {item_path} -> {backup_item}")
    trace_out()
    return True

def copy_folder(source_path: Path, target_path: Path, name: str, gateway) -> bool:
    """Schedule a copy of one framework folder from source to target, leaving out generated cache files."""
    trace_in()
    source_dir = source_path / name
    target_dir = target_path / name

    if not source_dir.exists():
        warn(f"Source {name}/ folder does not exist: {source_dir}")
        report_error("action", f"Source {name}/ folder does not exist: {source_dir}")
        trace_out()
        return False

    gateway.files.schedule_copy_tree(str(source_dir), str(target_dir), ignore=list(CACHE_PATTERNS))
    log(f"Scheduled copy of {name}/ to {target_dir}")
    trace_out()
    return True


def copy_top_level_files(source_path: Path, target_path: Path, gateway) -> List[str]:
    """Schedule copy of top-level files (not directories) from source to target. Returns list of copied files."""
    trace_in()
    copied_files = []
    
    # Get all top-level files in source (excluding directories)
    for item in source_path.iterdir():
        if item.is_file():
            target_file = target_path / item.name
            gateway.files.schedule_copy(str(item), str(target_file))
            copied_files.append(item.name)
            log(f"Scheduled copy of top-level file: {item.name}")
    
    log(f"Scheduled copy of {len(copied_files)} top-level files")
    trace_out()
    return copied_files

def restore_preserved(target_path: Path, backup_path: Path, gateway, preserve_set: Set[str]) -> List[str]:
    """Schedule restore of files from backup that are listed in upgrade_preserve.py.
    
    Note: backup_path is now the unified backup folder, so hh/ files are in backup_path/hh/
    Files are scheduled to restore from backup location, trusting that moves will have
    completed by the time restore operations execute during commit.
    """
    trace_in()
    restored_files = []
    
    # Schedule restore of each file in preserve set
    # preserve_set now contains project-relative paths (e.g., "hh/deploy/site/js/...", "context/...", "accounting.md")
    for rel_path_str in preserve_set:
        # Backup structure matches project-relative paths: backup/hh/..., backup/context/..., backup/README/..., backup/accounting.md
        backup_file = backup_path / rel_path_str
        target_file = target_path / rel_path_str
        
        # Schedule restore - file will be in backup location when this executes during commit
        gateway.files.schedule_copy(str(backup_file), str(target_file))
        restored_files.append(rel_path_str)
        log(f"Scheduled restore: {rel_path_str}")
    
    log(f"Scheduled restore of {len(restored_files)} files from backup")
    trace_out()
    return restored_files

def is_cache_file(file_path: Path) -> bool:
    """True for generated files (see CACHE_PATTERNS) that are neither copied nor compared."""
    return any(fnmatch.fnmatch(part, pattern) for part in file_path.parts for pattern in CACHE_PATTERNS)


def compute_file_hash(file_path: Path) -> Optional[str]:
    """Compute MD5 hash of a file. Returns None if file doesn't exist or error."""
    trace_in()
    try:
        if not file_path.exists() or not file_path.is_file():
            trace_out()
            return None
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        result = hash_md5.hexdigest()
        trace_out()
        return result
    except Exception as e:
        warn(f"Error computing hash for {file_path}: {e}")
        trace_out()
        return None

@dataclass
class FileDifferences:
    """Categorized file differences between source and target directories."""
    will_be_lost: List[str] = field(default_factory=list)  # Files in target but not in source (not preserved)
    will_be_restored: List[str] = field(default_factory=list)  # Files in target but not in source (preserved)
    will_be_created: List[str] = field(default_factory=list)  # Files in source but not in target
    will_be_updated: List[str] = field(default_factory=list)  # Files that differ (not preserved)
    will_be_preserved: List[str] = field(default_factory=list)  # Files that differ (preserved)
    
    def total_count(self) -> int:
        """Get total count of all differences."""
        return (len(self.will_be_lost) + len(self.will_be_restored) + 
                len(self.will_be_created) + len(self.will_be_updated) + 
                len(self.will_be_preserved))

def load_preserve_list(target_path: Path) -> Set[str]:
    """Load UPGRADE_PRESERVE list from target project's ext folder."""
    trace_in()
    preserve_file = target_path / "ext" / "deploy" / "conf" / "upgrade_preserve.py"
    preserve_list: List[str] = []
    
    if preserve_file.exists():
        try:
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
        log("No upgrade_preserve.py found, no files will be preserved")
    
    # Convert to set for faster lookups, normalize paths
    preserve_set = set()
    for path in preserve_list:
        # Normalize path separators
        normalized = str(path).replace('\\', '/')
        preserve_set.add(normalized)
    
    trace_out()
    return preserve_set

def compare_directories(source_dir: Path, target_dir: Path, preserve_set: Optional[Set[str]] = None, project_root: Optional[Path] = None) -> FileDifferences:
    """Compare two directories recursively and return categorized file differences.
    
    Returns FileDifferences object with files categorized as:
    - will_be_lost: Files in target but not in source (not preserved)
    - will_be_restored: Files in target but not in source (preserved)
    - will_be_created: Files in source but not in target
    - will_be_updated: Files that differ (not preserved)
    - will_be_preserved: Files that differ (preserved)
    """
    trace_in()
    if preserve_set is None:
        preserve_set = set()
    
    differences = FileDifferences()
    
    if not source_dir.exists():
        log(f"Source directory does not exist: {source_dir}")
        trace_out()
        return differences
    
    # Get all files in source directory (excluding cache files)
    source_files: Set[Path] = set()
    if source_dir.is_dir():
        for file_path in source_dir.rglob('*'):
            if file_path.is_file() and not is_cache_file(file_path):
                source_files.add(file_path)
    
    # Get all files in target directory (if it exists, excluding cache files)
    target_files: Set[Path] = set()
    if target_dir.exists() and target_dir.is_dir():
        for file_path in target_dir.rglob('*'):
            if file_path.is_file() and not is_cache_file(file_path):
                target_files.add(file_path)
    
    # Normalize preserve_set paths for comparison (use forward slashes)
    def normalize_path(path: str) -> str:
        return str(path).replace('\\', '/')
    
    # Compare files that exist in source
    for source_file in source_files:
        # For preserve_set check: use path relative to project_root if provided
        if project_root:
            rel_path_for_preserve = source_file.relative_to(project_root)
        else:
            rel_path_for_preserve = source_file.relative_to(source_dir)
        rel_path_str = normalize_path(str(rel_path_for_preserve))
        
        # For file operations: use path relative to source_dir
        rel_path_for_file = source_file.relative_to(source_dir)
        target_file = target_dir / rel_path_for_file
        
        source_hash = compute_file_hash(source_file)
        if source_hash is None:
            continue  # Skip if we can't read source file
        
        target_hash = compute_file_hash(target_file)
        is_preserved = rel_path_str in preserve_set
        
        if target_hash is None:
            # File exists in source but not in target - will be created
            differences.will_be_created.append(rel_path_str)
            log(f"File will be created: {rel_path_str}")
        elif source_hash != target_hash:
            # File exists but is different
            if is_preserved:
                # Would be updated but is preserved - won't actually change
                differences.will_be_preserved.append(rel_path_str)
                log(f"File would be updated but is preserved: {rel_path_str}")
            else:
                # Will be updated
                differences.will_be_updated.append(rel_path_str)
                log(f"File will be updated: {rel_path_str}")
    
    # Find files that exist in target but not in source
    for target_file in target_files:
        target_rel_to_dir = target_file.relative_to(target_dir)
        
        # For preserve_set check: use path relative to project_root if provided
        if project_root:
            # Compute path relative to project root (e.g., hh/deploy/site/js/file.js)
            rel_path_for_preserve = project_root / target_dir.name / target_rel_to_dir
            rel_path_for_preserve = rel_path_for_preserve.relative_to(project_root)
        else:
            rel_path_for_preserve = target_rel_to_dir
        rel_path_str = normalize_path(str(rel_path_for_preserve))
        
        # For file operations: use path relative to source_dir
        source_file = source_dir / target_rel_to_dir
        
        if not source_file.exists():
            # File exists in target but not in source
            is_preserved = rel_path_str in preserve_set
            if is_preserved:
                # Will be lost but restored from backup
                differences.will_be_restored.append(rel_path_str)
                log(f"File will be restored from backup: {rel_path_str}")
            else:
                # Will be lost
                differences.will_be_lost.append(rel_path_str)
                log(f"File will be lost: {rel_path_str}")
    
    total = differences.total_count()
    log(f"Found {total} different files: {len(differences.will_be_lost)} lost, {len(differences.will_be_restored)} restored, {len(differences.will_be_created)} created, {len(differences.will_be_updated)} updated, {len(differences.will_be_preserved)} preserved")
    trace_out()
    return differences

def diff_folder(source_path: Path, target_path: Path, name: str, preserve_set: Set[str]) -> FileDifferences:
    """Compare one framework folder. Paths in the result are project-relative (e.g. "hh_page/add_page.py")."""
    trace_in()
    source_dir = source_path / name
    target_dir = target_path / name
    if target_dir.exists():
        diffs = compare_directories(source_dir, target_dir, preserve_set, source_path)
    else:
        diffs = FileDifferences()
        for file_path in source_dir.rglob('*'):
            if file_path.is_file() and not is_cache_file(file_path):
                diffs.will_be_created.append(str(file_path.relative_to(source_path)).replace('\\', '/'))
    log(f"Found {diffs.total_count()} files that differ in {name}/")
    return trace_out(diffs)


def merge_diffs(diff_list: List[FileDifferences]) -> FileDifferences:
    """Combine several FileDifferences into one."""
    merged = FileDifferences()
    for diffs in diff_list:
        merged.will_be_lost.extend(diffs.will_be_lost)
        merged.will_be_restored.extend(diffs.will_be_restored)
        merged.will_be_created.extend(diffs.will_be_created)
        merged.will_be_updated.extend(diffs.will_be_updated)
        merged.will_be_preserved.extend(diffs.will_be_preserved)
    return merged


def _add_diffs(result_data: dict, prefix: str, diffs: Optional[FileDifferences]) -> None:
    """Add <prefix>_diffs_<kind> lists and <prefix>_diff_count_<kind> counts to the payload."""
    if diffs is None:
        return
    for kind, files in (("lost", diffs.will_be_lost), ("restored", diffs.will_be_restored),
                        ("created", diffs.will_be_created), ("updated", diffs.will_be_updated),
                        ("preserved", diffs.will_be_preserved)):
        result_data[f"{prefix}_diffs_{kind}"] = files
        result_data[f"{prefix}_diff_count_{kind}"] = len(files)
    result_data[f"{prefix}_diff_count_total"] = diffs.total_count()


def report_results(target_path: Path, backup_path: Path, restored_files: List[str], diffs_by_prefix: Dict[str, Optional[FileDifferences]], folders: List[str], top_level_files: Optional[List[str]] = None, dry_run: bool = False) -> dict:
    """Create result payload for upgrade operation."""
    trace_in()
    result_data = {
        "target": str(target_path),
        "backup": str(backup_path),
        "backup_name": backup_path.name,
        "restored_files": restored_files,
        "restored_count": len(restored_files),
        "upgraded_folders": folders,
        "status": "upgraded" if not dry_run else "dry_run",
        "dry_run": dry_run
    }
    for prefix, diffs in diffs_by_prefix.items():
        _add_diffs(result_data, prefix, diffs)
    if top_level_files:
        result_data["top_level_files"] = top_level_files
        result_data["top_level_files_count"] = len(top_level_files)
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
    
    # Check for dry_run flag
    dry_run = gateway.is_set('dry-run') or gateway.is_set('dry_run')
    if dry_run:
        log("Dry run mode enabled - no files will be modified")
    
    # Load preserve list BEFORE comparison
    preserve_set = load_preserve_list(target_path)
    
    # Compare every framework folder BEFORE upgrade operations
    folders = get_upgrade_folders(source_path)
    log(f"Folders to upgrade: {', '.join(folders)}")
    folder_diffs = {name: diff_folder(source_path, target_path, name, preserve_set) for name in folders}
    module_names = [name for name in folders if name != "hh" and name not in DOC_FOLDERS]
    diffs_by_prefix: Dict[str, Optional[FileDifferences]] = {
        "hh": folder_diffs.get("hh"),
        "modules": merge_diffs([folder_diffs[name] for name in module_names]),
        "context": folder_diffs.get("context"),
        "readme": folder_diffs.get("README"),
    }

    # Compare top-level files
    top_level_diffs: Optional[FileDifferences] = None
    top_level_files_list: List[str] = []
    log("Comparing top-level files...")
    top_level_diffs = FileDifferences()
    
    # Get all top-level files from source (excluding directories and backup folder)
    source_files = {}
    for item in source_path.iterdir():
        if item.is_file():
            source_files[item.name] = item
    
    # Get all top-level files from target (excluding any existing backup folders)
    target_files = {}
    for item in target_path.iterdir():
        if item.is_file() and not item.name.startswith('backup'):
            target_files[item.name] = item
    
    # Normalize preserve_set paths for comparison
    def normalize_path(path: str) -> str:
        return str(path).replace('\\', '/')
    
    # Compare files
    for filename, source_file in source_files.items():
        target_file = target_files.get(filename)
        source_hash = compute_file_hash(source_file)
        if source_hash is None:
            continue
        
        # preserve_set holds project-relative paths, so a top-level file is just its name
        is_preserved = normalize_path(filename) in preserve_set
        
        if target_file is None:
            # File exists in source but not in target - will be created
            top_level_diffs.will_be_created.append(filename)
            top_level_files_list.append(filename)
            log(f"Top-level file will be created: {filename}")
        else:
            target_hash = compute_file_hash(target_file)
            if target_hash is None or source_hash != target_hash:
                # File exists but is different
                if is_preserved:
                    # Would be updated but is preserved
                    top_level_diffs.will_be_preserved.append(filename)
                    log(f"Top-level file would be updated but is preserved: {filename}")
                else:
                    # Will be updated
                    top_level_diffs.will_be_updated.append(filename)
                    top_level_files_list.append(filename)
                    log(f"Top-level file will be updated: {filename}")
    
    # Find files that exist in target but not in source
    for filename, target_file in target_files.items():
        if filename not in source_files:
            # Check if file is preserved
            is_preserved = normalize_path(filename) in preserve_set
            if is_preserved:
                # Will be lost but restored from backup
                top_level_diffs.will_be_restored.append(filename)
                log(f"Top-level file will be restored from backup: {filename}")
            else:
                # Will be lost
                top_level_diffs.will_be_lost.append(filename)
                log(f"Top-level file will be lost: {filename}")
    
    log(f"Found {top_level_diffs.total_count()} top-level files that differ")

    diffs_by_prefix["top_level"] = top_level_diffs
    
    # Create unified backup folder
    try:
        backup_path = create_unified_backup(target_path, gateway)
    except Exception as e:
        warn(f"Failed to create backup folder: {e}")
        report_error("action", f"Failed to create backup folder: {e}")
        trace_out()
        return False
    
    # Move each framework folder the target has into the backup
    for name in folders:
        move_to_backup(target_path, backup_path, name, gateway)
    
    # Move top-level files to backup
    for item in target_path.iterdir():
        if item.is_file() and item.name != backup_path.name:
            backup_file = backup_path / item.name
            gateway.files.schedule_move(str(item), str(backup_file))
            log(f"Scheduled backup of top-level file: {item.name}")
    
    # Schedule copy of each framework folder (cache files left out, so the target rebuilds its registries)
    for name in folders:
        if not copy_folder(source_path, target_path, name, gateway):
            trace_out()
            return False
    
    # Schedule copy of top-level files
    copy_top_level_files(source_path, target_path, gateway)
    
    # Schedule restore of preserved files (skip in dry-run mode)
    restored_files = []
    if not dry_run:
        restored_files = restore_preserved(target_path, backup_path, gateway, preserve_set)
    
    # File operations will be committed automatically by gateway dispatch
    result = not is_error()
    if result:
        if dry_run:
            log("Dry run completed successfully")
        else:
            log("Upgrade completed successfully")
        result_data = report_results(target_path, backup_path, restored_files, diffs_by_prefix, folders, top_level_files_list, dry_run)
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Upgrade encountered problems")
    
    trace_out()
    return result
