import shutil
import uuid
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
    """Gateway-owned file system operation manager with rollback support."""
    
    def __init__(self):
        trace_in()
        self._operations: List[Dict[str, Any]] = []
        log("FileSystem initialized")
        trace_out()
    
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
        """Execute all scheduled file operations. Returns True if all succeed, False otherwise."""
        trace_in()
        log("FileSystem commit starting...")
        
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
    
    def clear(self) -> None:
        """Clear all file operations (called after successful commit or rollback)."""
        self._operations.clear()
        log("File operations cleared")

