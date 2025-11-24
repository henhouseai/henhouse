import shutil
import uuid
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

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

class FileSystem:
    """Gateway-owned file system operation manager with rollback support.
    Provides abstraction layer for filesystem operations with OS-specific handling
    and graceful error handling for remote file scenarios."""
    
    def __init__(self, dry_run: bool = False):
        trace_in()
        self._operations: List[Dict[str, Any]] = []
        self._os_type = self._detect_os()
        self._remote_file_handler = None  # Placeholder for future remote file handling
        self._dry_run: bool = dry_run
        log(f"FileSystem initialized (OS: {self._os_type}, dry_run={dry_run})")
        trace_out()
    
    def _detect_os(self) -> str:
        """Detect the operating system. Returns 'windows', 'macos', 'linux', or 'unknown'."""
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            # Try to detect Ubuntu specifically
            try:
                with open('/etc/os-release', 'r') as f:
                    if 'ubuntu' in f.read().lower():
                        return 'ubuntu'
            except Exception:
                pass
            return 'linux'
        else:
            return 'unknown'
    
    def schedule_move(self, from_path: str, to_path: str) -> None:
        """Schedule a file move operation to be executed on commit."""
        trace_in()
        operation = {
            'type': 'move',
            'from_path': from_path,
            'to_path': to_path,
            'status': 'scheduled',
            'temp_filename': None
        }
        self._operations.append(operation)
        log(f"Scheduled file move: {from_path} -> {to_path}")
        trace_out()
    
    def schedule_delete(self, file_path: str) -> None:
        """Schedule a file delete operation (soft delete to /tmp) to be executed on commit."""
        trace_in()
        file_path_obj = Path(file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        temp_filename = f"henhouse_deleted_{timestamp}_{unique_id}_{file_path_obj.name}"
        temp_path = f"/tmp/{temp_filename}"
        operation = {
            'type': 'delete',
            'from_path': file_path,
            'to_path': temp_path,
            'status': 'scheduled',
            'temp_filename': temp_filename
        }
        self._operations.append(operation)
        log(f"Scheduled file delete: {file_path} -> {temp_path}")
        trace_out()
    
    def commit(self) -> bool:
        """Execute all scheduled file operations. Returns True if all succeed, False otherwise. If dry_run is enabled, skips execution."""
        trace_in()
        log("FileSystem commit starting...")
        
        if self._dry_run:
            scheduled_count = sum(1 for op in self._operations if op.get('status') == 'scheduled')
            log(f"Dry run mode enabled - skipping {scheduled_count} scheduled file operations")
            trace_out()
            return True
        
        if not self._operations:
            log("No file operations to execute")
            trace_out()
            return True
        
        scheduled_count = sum(1 for op in self._operations if op.get('status') == 'scheduled')
        log(f"Executing {scheduled_count} scheduled file operations (out of {len(self._operations)} total)")
        
        completed_count = 0
        for operation in self._operations:
            if operation['status'] != 'scheduled':
                log(f"Skipping operation {operation['type']} (status: {operation['status']})")
                continue
            
            log(f"Processing {operation['type']} operation: {operation['from_path']} -> {operation['to_path']}")
            
            try:
                from_path = Path(operation['from_path'])
                to_path = Path(operation['to_path'])
                
                if not from_path.exists():
                    warn(f"Source file does not exist: {from_path}")
                    report_error("file_operation", f"Source file does not exist: {from_path}")
                    operation['status'] = 'failed'
                    trace_out()
                    return False
                
                if operation['type'] == 'move':
                    to_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(from_path), str(to_path))
                    log(f"Moved file: {from_path} -> {to_path}")
                    operation['status'] = 'completed'
                    completed_count += 1
                    
                elif operation['type'] == 'delete':
                    to_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(from_path), str(to_path))
                    log(f"Moved file to temp for deletion: {from_path} -> {to_path}")
                    operation['status'] = 'completed'
                    completed_count += 1
                    
            except Exception as e:
                warn(f"Failed to execute file operation {operation['type']}: {from_path} -> {to_path}: {str(e)}")
                report_error("file_operation", f"Failed to {operation['type']} file: {str(e)}")
                operation['status'] = 'failed'
                trace_out()
                return False
        
        log(f"All {completed_count} file operations executed successfully")
        trace_out()
        return True
    
    def rollback(self) -> bool:
        """Rollback all completed file operations. Returns True if all rollbacks succeed."""
        trace_in()
        if not self._operations:
            log("No file operations to rollback")
            trace_out()
            return True
        
        log(f"Rolling back {len(self._operations)} file operations")
        
        completed_count = sum(1 for op in self._operations if op.get('status') == 'completed')
        log(f"Found {completed_count} completed operations to rollback")
        
        if completed_count == 0:
            log("No completed operations to rollback")
            trace_out()
            return True
        
        rolled_back_count = 0
        for operation in reversed(self._operations):
            if operation['status'] != 'completed':
                continue
            
            log(f"Rolling back operation: {operation['type']} from {operation['from_path']} to {operation['to_path']}")
            
            try:
                from_path = Path(operation['from_path'])
                to_path = Path(operation['to_path'])
                
                if operation['type'] == 'move':
                    if to_path.exists():
                        from_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(to_path), str(from_path))
                        log(f"Rolled back move: {to_path} -> {from_path}")
                        operation['status'] = 'rolled_back'
                        rolled_back_count += 1
                    else:
                        warn(f"Destination file does not exist for rollback: {to_path}")
                        report_error("file_operation", f"Destination file does not exist for rollback: {to_path}")
                        operation['status'] = 'rollback_failed'
                        trace_out()
                        return False
                    
                elif operation['type'] == 'delete':
                    if to_path.exists():
                        from_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(to_path), str(from_path))
                        log(f"Rolled back delete: {to_path} -> {from_path}")
                        operation['status'] = 'rolled_back'
                        rolled_back_count += 1
                    else:
                        warn(f"Temp file does not exist for rollback: {to_path}")
                        report_error("file_operation", f"Temp file does not exist for rollback: {to_path}")
                        operation['status'] = 'rollback_failed'
                        trace_out()
                        return False
                    
            except Exception as e:
                warn(f"Failed to rollback file operation {operation['type']}: {str(e)}")
                report_error("file_operation", f"Failed to rollback {operation['type']}: {str(e)}")
                operation['status'] = 'rollback_failed'
                trace_out()
                return False
        
        log(f"All {rolled_back_count} file operations rolled back successfully")
        trace_out()
        return True
    
    def has_operations(self) -> bool:
        """Check if there are any scheduled file operations."""
        return len(self._operations) > 0
    
    # ===== File Existence and Metadata =====
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists. Returns False if file not found (graceful).
        Supports future remote file checking via _remote_file_handler hook."""
        trace_in()
        try:
            # Future: Check remote file handler first if configured
            if self._remote_file_handler:
                result = self._remote_file_handler.check_file_exists(path)
                if result is not None:
                    trace_out()
                    return result
            
            # Local file check
            exists = Path(path).exists() and Path(path).is_file()
            if not exists:
                debug(f"File does not exist (local): {path}")
            trace_out()
            return exists
        except Exception as e:
            warn(f"Error checking file existence: {path}: {e}")
            trace_out()
            return False  # Graceful failure
    
    def directory_exists(self, path: str) -> bool:
        """Check if a directory exists. Returns False if directory not found (graceful)."""
        trace_in()
        try:
            exists = Path(path).exists() and Path(path).is_dir()
            if not exists:
                debug(f"Directory does not exist: {path}")
            trace_out()
            return exists
        except Exception as e:
            warn(f"Error checking directory existence: {path}: {e}")
            trace_out()
            return False  # Graceful failure
    
    def get_file_size(self, path: str) -> Optional[int]:
        """Get file size in bytes. Returns None if file not found or error (graceful)."""
        trace_in()
        try:
            if not self.file_exists(path):
                trace_out()
                return None
            size = Path(path).stat().st_size
            trace_out()
            return size
        except Exception as e:
            warn(f"Error getting file size: {path}: {e}")
            trace_out()
            return None
    
    # ===== Directory Operations =====
    
    def create_directory(self, path: str, parents: bool = True, mode: Optional[int] = None) -> bool:
        """Create a directory. Returns True if successful, False otherwise.
        On Linux/Ubuntu, sets permissions if mode is provided."""
        trace_in()
        try:
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                debug(f"Directory already exists: {path}")
                trace_out()
                return True
            
            path_obj.mkdir(parents=parents, exist_ok=True)
            
            # Set permissions on Unix-like systems
            if mode is not None and self._os_type in ('linux', 'ubuntu', 'macos'):
                try:
                    os.chmod(path, mode)
                    debug(f"Set directory permissions: {path} -> {oct(mode)}")
                except Exception as e:
                    warn(f"Failed to set directory permissions: {path}: {e}")
            
            log(f"Created directory: {path}")
            trace_out()
            return True
        except Exception as e:
            warn(f"Failed to create directory: {path}: {e}")
            report_error("file_operation", f"Failed to create directory: {path}")
            trace_out()
            return False
    
    # ===== File Reading =====
    
    def read_file(self, path: str) -> Optional[bytes]:
        """Read a file as bytes. Returns None if file not found or error (graceful).
        Supports future remote file reading via _remote_file_handler hook."""
        trace_in()
        try:
            # Future: Check remote file handler first if configured
            if self._remote_file_handler:
                result = self._remote_file_handler.read_file(path)
                if result is not None:
                    trace_out()
                    return result
            
            # Local file read
            if not self.file_exists(path):
                warn(f"File not found for reading: {path}")
                trace_out()
                return None
            
            with open(path, 'rb') as f:
                content = f.read()
            log(f"Read file: {path} ({len(content)} bytes)")
            trace_out()
            return content
        except Exception as e:
            warn(f"Error reading file: {path}: {e}")
            report_error("file_operation", f"Failed to read file: {path}")
            trace_out()
            return None
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> Optional[str]:
        """Read a file as text. Returns None if file not found or error (graceful)."""
        trace_in()
        try:
            content = self.read_file(path)
            if content is None:
                trace_out()
                return None
            
            text = content.decode(encoding)
            log(f"Read file as text: {path} ({len(text)} characters)")
            trace_out()
            return text
        except UnicodeDecodeError as e:
            warn(f"Error decoding file: {path}: {e}")
            report_error("file_operation", f"Failed to decode file: {path}")
            trace_out()
            return None
        except Exception as e:
            warn(f"Error reading file as text: {path}: {e}")
            trace_out()
            return None
    
    # ===== File Writing (Immediate, not scheduled) =====
    
    def write_file(self, path: str, content: bytes) -> bool:
        """Write bytes to a file immediately. Returns True if successful, False otherwise.
        Creates parent directories if needed."""
        trace_in()
        try:
            path_obj = Path(path)
            # Create parent directory if it doesn't exist
            if path_obj.parent and not path_obj.parent.exists():
                if not self.create_directory(str(path_obj.parent)):
                    trace_out()
                    return False
            
            with open(path, 'wb') as f:
                f.write(content)
            log(f"Wrote file: {path} ({len(content)} bytes)")
            trace_out()
            return True
        except Exception as e:
            warn(f"Error writing file: {path}: {e}")
            report_error("file_operation", f"Failed to write file: {path}")
            trace_out()
            return False
    
    def write_file_text(self, path: str, content: str, encoding: str = 'utf-8') -> bool:
        """Write text to a file immediately. Returns True if successful, False otherwise.
        Creates parent directories if needed."""
        trace_in()
        try:
            content_bytes = content.encode(encoding)
            result = self.write_file(path, content_bytes)
            trace_out()
            return result
        except Exception as e:
            warn(f"Error encoding text for file: {path}: {e}")
            report_error("file_operation", f"Failed to encode text for file: {path}")
            trace_out()
            return False
    
    # ===== Path Utilities =====
    
    def join_path(self, *parts: str) -> str:
        """Join path parts using OS-appropriate separator."""
        if self._os_type == 'windows':
            return str(Path(*parts))
        else:
            # Unix-like systems
            return str(Path(*parts))
    
    def normalize_path(self, path: str) -> str:
        """Normalize a path (resolve .. and . components)."""
        try:
            return str(Path(path).resolve())
        except Exception as e:
            warn(f"Error normalizing path: {path}: {e}")
            return path
    
    def get_parent_directory(self, path: str) -> str:
        """Get the parent directory of a path."""
        try:
            return str(Path(path).parent)
        except Exception as e:
            warn(f"Error getting parent directory: {path}: {e}")
            return ""
    
    def get_filename(self, path: str) -> str:
        """Get the filename from a path."""
        try:
            return Path(path).name
        except Exception as e:
            warn(f"Error getting filename: {path}: {e}")
            return ""

