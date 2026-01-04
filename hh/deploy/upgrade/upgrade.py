import importlib.util
import shutil
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


def create_unified_backup(target_path: Path, gateway) -> Path:
    """Create a unified backup folder and move items into it. Returns the backup folder path."""
    trace_in()
    
    # Check for dry_run flag
    dry_run = gateway.is_set('dry-run') or gateway.is_set('dry_run')
    
    # Find available backup name
    backup_name = "backup"
    backup_path = target_path / backup_name
    counter = 2
    
    while backup_path.exists():
        backup_name = f"backup_{counter}"
        backup_path = target_path / backup_name
        counter += 1
    
    # Create backup directory (skip in dry-run mode)
    if not dry_run:
        gateway.files.create_directory(str(backup_path))
        log(f"Created backup directory: {backup_path}")
    else:
        log(f"Would create backup directory: {backup_path} (dry-run)")
    
    # Move hh/ into backup/hh/
    hh_path = target_path / "hh"
    if hh_path.exists():
        backup_hh = backup_path / "hh"
        gateway.files.schedule_move(str(hh_path), str(backup_hh))
        log(f"Scheduled backup: {hh_path} -> {backup_hh}")
    
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


def copy_hh(source_path: Path, target_path: Path, gateway) -> bool:
    """Schedule copy of hh/ folder from source to target."""
    trace_in()
    source_hh = source_path / "hh"
    target_hh = target_path / "hh"
    
    if not source_hh.exists():
        warn(f"Source hh/ folder does not exist: {source_hh}")
        report_error("action", f"Source hh/ folder does not exist: {source_hh}")
        trace_out()
        return False
    
    # Schedule copy of entire hh/ folder (no exclusions)
    gateway.files.schedule_copy_tree(str(source_hh), str(target_hh))
    log(f"Scheduled copy of hh/ to {target_hh}")
    
    trace_out()
    return True


def copy_context(source_path: Path, target_path: Path, gateway) -> bool:
    """Schedule copy of context/ folder from source to target."""
    trace_in()
    source_context = source_path / "context"
    target_context = target_path / "context"
    
    if not source_context.exists():
        warn(f"Source context/ folder does not exist: {source_context}")
        report_error("action", f"Source context/ folder does not exist: {source_context}")
        trace_out()
        return False
    
    # Schedule copy of entire context/ folder (no exclusions)
    gateway.files.schedule_copy_tree(str(source_context), str(target_context))
    log(f"Scheduled copy of context/ to {target_context}")
    
    trace_out()
    return True


def copy_readme(source_path: Path, target_path: Path, gateway) -> bool:
    """Schedule copy of README/ folder from source to target."""
    trace_in()
    source_readme = source_path / "README"
    target_readme = target_path / "README"
    
    if not source_readme.exists():
        warn(f"Source README/ folder does not exist: {source_readme}")
        report_error("action", f"Source README/ folder does not exist: {source_readme}")
        trace_out()
        return False
    
    # Schedule copy of entire README/ folder (no exclusions)
    gateway.files.schedule_copy_tree(str(source_readme), str(target_readme))
    log(f"Scheduled copy of README/ to {target_readme}")
    
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
    for rel_path_str in preserve_set:
        # Convert normalized path back to Path object (handle both / and \)
        rel_path = Path(rel_path_str.replace('/', '\\') if '\\' in str(backup_path) else rel_path_str.replace('\\', '/'))
        
        # Determine backup location: try hh/ first (for hh/ files), then top-level (for other files)
        backup_file = backup_path / "hh" / rel_path
        # If path doesn't start with hh/, it's a top-level file
        if not rel_path_str.startswith('hh/'):
            backup_file = backup_path / rel_path
        
        target_file = target_path / rel_path
        
        # Schedule restore - file will be in backup location when this executes during commit
        gateway.files.schedule_copy(str(backup_file), str(target_file))
        restored_files.append(rel_path_str)
        log(f"Scheduled restore: {rel_path_str}")
    
    log(f"Scheduled restore of {len(restored_files)} files from backup")
    trace_out()
    return restored_files


def is_cache_file(file_path: Path) -> bool:
    """Check if a file or directory should be excluded from comparison (cache files)."""
    trace_in()
    try:
        # Check if file is in __pycache__ directory
        parts = file_path.parts
        if '__pycache__' in parts:
            trace_out()
            return True
        
        # Check if file is in .cache directory
        if '.cache' in parts:
            trace_out()
            return True
        
        # Check file extensions
        if file_path.is_file():
            name = file_path.name
            # .pyc and .pyo files
            if name.endswith('.pyc') or name.endswith('.pyo'):
                trace_out()
                return True
            
            # Cache JSON files
            if name.endswith('-reg.json') or name.endswith('.cycle.json') or name == 'cache.json' or name.endswith('.cache'):
                trace_out()
                return True
        
        trace_out()
        return False
    except Exception as e:
        warn(f"Error checking if file is cache: {file_path}: {e}")
        trace_out()
        return False


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


def compare_directories(source_dir: Path, target_dir: Path, preserve_set: Optional[Set[str]] = None) -> FileDifferences:
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
        rel_path = source_file.relative_to(source_dir)
        rel_path_str = normalize_path(str(rel_path))
        target_file = target_dir / rel_path
        
        source_hash = compute_file_hash(source_file)
        if source_hash is None:
            continue  # Skip if we can't read source file
        
        target_hash = compute_file_hash(target_file)
        is_preserved = rel_path_str in preserve_set
        
        if target_hash is None:
            # File exists in source but not in target - will be created
            differences.will_be_created.append(rel_path_str)
            log(f"File will be created: {rel_path}")
        elif source_hash != target_hash:
            # File exists but is different
            if is_preserved:
                # Would be updated but is preserved - won't actually change
                differences.will_be_preserved.append(rel_path_str)
                log(f"File would be updated but is preserved: {rel_path}")
            else:
                # Will be updated
                differences.will_be_updated.append(rel_path_str)
                log(f"File will be updated: {rel_path}")
    
    # Find files that exist in target but not in source
    for target_file in target_files:
        rel_path = target_file.relative_to(target_dir)
        rel_path_str = normalize_path(str(rel_path))
        source_file = source_dir / rel_path
        
        if not source_file.exists():
            # File exists in target but not in source
            is_preserved = rel_path_str in preserve_set
            if is_preserved:
                # Will be lost but restored from backup
                differences.will_be_restored.append(rel_path_str)
                log(f"File will be restored from backup: {rel_path}")
            else:
                # Will be lost
                differences.will_be_lost.append(rel_path_str)
                log(f"File will be lost: {rel_path}")
    
    total = differences.total_count()
    log(f"Found {total} different files: {len(differences.will_be_lost)} lost, {len(differences.will_be_restored)} restored, {len(differences.will_be_created)} created, {len(differences.will_be_updated)} updated, {len(differences.will_be_preserved)} preserved")
    trace_out()
    return differences


def report_results(target_path: Path, backup_path: Path, restored_files: List[str], hh_diffs: Optional[FileDifferences] = None, context_diffs: Optional[FileDifferences] = None, readme_diffs: Optional[FileDifferences] = None, top_level_diffs: Optional[FileDifferences] = None, top_level_files: Optional[List[str]] = None, dry_run: bool = False) -> dict:
    """Create result payload for upgrade operation."""
    trace_in()
    result_data = {
        "target": str(target_path),
        "backup": str(backup_path),
        "backup_name": backup_path.name,
        "restored_files": restored_files,
        "restored_count": len(restored_files),
        "status": "upgraded" if not dry_run else "dry_run",
        "dry_run": dry_run
    }
    if top_level_files:
        result_data["top_level_files"] = top_level_files
        result_data["top_level_files_count"] = len(top_level_files)
    
    # Add file differences (categorized)
    if hh_diffs is not None:
        result_data["hh_diffs_lost"] = hh_diffs.will_be_lost
        result_data["hh_diffs_restored"] = hh_diffs.will_be_restored
        result_data["hh_diffs_created"] = hh_diffs.will_be_created
        result_data["hh_diffs_updated"] = hh_diffs.will_be_updated
        result_data["hh_diffs_preserved"] = hh_diffs.will_be_preserved
        result_data["hh_diff_count_lost"] = len(hh_diffs.will_be_lost)
        result_data["hh_diff_count_restored"] = len(hh_diffs.will_be_restored)
        result_data["hh_diff_count_created"] = len(hh_diffs.will_be_created)
        result_data["hh_diff_count_updated"] = len(hh_diffs.will_be_updated)
        result_data["hh_diff_count_preserved"] = len(hh_diffs.will_be_preserved)
        result_data["hh_diff_count_total"] = hh_diffs.total_count()
    if context_diffs is not None:
        result_data["context_diffs_lost"] = context_diffs.will_be_lost
        result_data["context_diffs_restored"] = context_diffs.will_be_restored
        result_data["context_diffs_created"] = context_diffs.will_be_created
        result_data["context_diffs_updated"] = context_diffs.will_be_updated
        result_data["context_diffs_preserved"] = context_diffs.will_be_preserved
        result_data["context_diff_count_lost"] = len(context_diffs.will_be_lost)
        result_data["context_diff_count_restored"] = len(context_diffs.will_be_restored)
        result_data["context_diff_count_created"] = len(context_diffs.will_be_created)
        result_data["context_diff_count_updated"] = len(context_diffs.will_be_updated)
        result_data["context_diff_count_preserved"] = len(context_diffs.will_be_preserved)
        result_data["context_diff_count_total"] = context_diffs.total_count()
    if readme_diffs is not None:
        result_data["readme_diffs_lost"] = readme_diffs.will_be_lost
        result_data["readme_diffs_restored"] = readme_diffs.will_be_restored
        result_data["readme_diffs_created"] = readme_diffs.will_be_created
        result_data["readme_diffs_updated"] = readme_diffs.will_be_updated
        result_data["readme_diffs_preserved"] = readme_diffs.will_be_preserved
        result_data["readme_diff_count_lost"] = len(readme_diffs.will_be_lost)
        result_data["readme_diff_count_restored"] = len(readme_diffs.will_be_restored)
        result_data["readme_diff_count_created"] = len(readme_diffs.will_be_created)
        result_data["readme_diff_count_updated"] = len(readme_diffs.will_be_updated)
        result_data["readme_diff_count_preserved"] = len(readme_diffs.will_be_preserved)
        result_data["readme_diff_count_total"] = readme_diffs.total_count()
    if top_level_diffs is not None:
        result_data["top_level_diffs_lost"] = top_level_diffs.will_be_lost
        result_data["top_level_diffs_restored"] = top_level_diffs.will_be_restored
        result_data["top_level_diffs_created"] = top_level_diffs.will_be_created
        result_data["top_level_diffs_updated"] = top_level_diffs.will_be_updated
        result_data["top_level_diffs_preserved"] = top_level_diffs.will_be_preserved
        result_data["top_level_diff_count_lost"] = len(top_level_diffs.will_be_lost)
        result_data["top_level_diff_count_restored"] = len(top_level_diffs.will_be_restored)
        result_data["top_level_diff_count_created"] = len(top_level_diffs.will_be_created)
        result_data["top_level_diff_count_updated"] = len(top_level_diffs.will_be_updated)
        result_data["top_level_diff_count_preserved"] = len(top_level_diffs.will_be_preserved)
        result_data["top_level_diff_count_total"] = top_level_diffs.total_count()
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
    
    # Compare files BEFORE upgrade operations
    source_hh = source_path / "hh"
    target_hh = target_path / "hh"
    hh_diffs: Optional[FileDifferences] = None
    
    log("Comparing hh/ directories...")
    if source_hh.exists() and target_hh.exists():
        hh_diffs = compare_directories(source_hh, target_hh, preserve_set)
        log(f"Found {hh_diffs.total_count()} files that differ in hh/")
    elif source_hh.exists():
        # Target hh/ doesn't exist yet, all files will be new
        log("Target hh/ does not exist - all files will be new")
        hh_diffs = FileDifferences()
        for file_path in source_hh.rglob('*'):
            if file_path.is_file() and not is_cache_file(file_path):
                rel_path = file_path.relative_to(source_hh)
                # Normalize path
                rel_path_str = str(rel_path).replace('\\', '/')
                hh_diffs.will_be_created.append(rel_path_str)
    else:
        log("Source hh/ does not exist - cannot compare")
    
    # Compare context/
    context_diffs: Optional[FileDifferences] = None
    source_context = source_path / "context"
    target_context = target_path / "context"
    log("Comparing context/ directories...")
    if source_context.exists() and target_context.exists():
        context_diffs = compare_directories(source_context, target_context, preserve_set)
        log(f"Found {context_diffs.total_count()} files that differ in context/")
    elif source_context.exists():
        # Target context/ doesn't exist yet, all files will be new
        log("Target context/ does not exist - all files will be new")
        context_diffs = FileDifferences()
        for file_path in source_context.rglob('*'):
            if file_path.is_file() and not is_cache_file(file_path):
                rel_path = file_path.relative_to(source_context)
                # Normalize path
                rel_path_str = str(rel_path).replace('\\', '/')
                context_diffs.will_be_created.append(rel_path_str)
    else:
        log("Source context/ does not exist - cannot compare")
    
    # Compare README/
    readme_diffs: Optional[FileDifferences] = None
    source_readme = source_path / "README"
    target_readme = target_path / "README"
    log("Comparing README/ directories...")
    if source_readme.exists() and target_readme.exists():
        readme_diffs = compare_directories(source_readme, target_readme, preserve_set)
        log(f"Found {readme_diffs.total_count()} files that differ in README/")
    elif source_readme.exists():
        # Target README/ doesn't exist yet, all files will be new
        log("Target README/ does not exist - all files will be new")
        readme_diffs = FileDifferences()
        for file_path in source_readme.rglob('*'):
            if file_path.is_file() and not is_cache_file(file_path):
                rel_path = file_path.relative_to(source_readme)
                # Normalize path
                rel_path_str = str(rel_path).replace('\\', '/')
                readme_diffs.will_be_created.append(rel_path_str)
    else:
        log("Source README/ does not exist - cannot compare")
    
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
        
        # Check if file is preserved (preserve_set uses paths relative to hh/, so top-level files use just filename)
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
    
    # Create unified backup folder
    try:
        backup_path = create_unified_backup(target_path, gateway)
    except Exception as e:
        warn(f"Failed to create backup folder: {e}")
        report_error("action", f"Failed to create backup folder: {e}")
        trace_out()
        return False
    
    # Move context/ to backup
    if not move_to_backup(target_path, backup_path, "context", gateway):
        log("context/ does not exist, skipping backup")
    
    # Move README/ to backup
    if not move_to_backup(target_path, backup_path, "README", gateway):
        log("README/ does not exist, skipping backup")
    
    # Move top-level files to backup
    top_level_files_backed_up = []
    for item in target_path.iterdir():
        if item.is_file() and item.name != backup_path.name:
            backup_file = backup_path / item.name
            gateway.files.schedule_move(str(item), str(backup_file))
            top_level_files_backed_up.append(item.name)
            log(f"Scheduled backup of top-level file: {item.name}")
    
    # Schedule copy of new hh/
    if not copy_hh(source_path, target_path, gateway):
        trace_out()
        return False
    
    # Schedule copy of context/
    if not copy_context(source_path, target_path, gateway):
        trace_out()
        return False
    
    # Schedule copy of README/
    if not copy_readme(source_path, target_path, gateway):
        trace_out()
        return False
    
    # Schedule copy of top-level files
    top_level_files_copied = copy_top_level_files(source_path, target_path, gateway)
    
    # Schedule restore of preserved files (skip in dry-run mode)
    restored_files = []
    if not dry_run:
        restored_files = restore_preserved(target_path, backup_path, gateway, preserve_set)
    
    # Commit all scheduled file operations
    if not gateway.files.commit():
        warn("Failed to commit file operations")
        report_error("action", "Failed to commit file operations")
        trace_out()
        return False
    
    # Clean up cache files (skip if dry_run)
    if not dry_run:
        target_hh = target_path / "hh"
        if target_hh.exists():
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
    
    # Report results
    result = not is_error()
    if result:
        if dry_run:
            log("Dry run completed successfully")
        else:
            log("Upgrade completed successfully")
        result_data = report_results(target_path, backup_path, restored_files, hh_diffs, context_diffs, readme_diffs, top_level_diffs, top_level_files_list, dry_run)
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Upgrade encountered problems")
    
    trace_out()
    return result

