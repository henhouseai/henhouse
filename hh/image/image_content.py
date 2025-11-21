from typing import Dict, Any, Optional
import datetime as dt
from hh.gateway.connection.connection import r_query, u_query, c_query, d_query, schedule_file_move
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_method_registry import register_image_mixin_methods
from hh.image.image_registry import invalidate_image_cache_entry

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_image_content_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_image_mixin_methods
def _register_content_methods():
    return {
        'modify_caption': {'mixin_method': '_modify_caption', 'decorator': 'write'},
        'modify_visibility': {'mixin_method': '_modify_visibility', 'decorator': 'write'},
        'update_view_count': {'mixin_method': '_update_view_count', 'decorator': 'write'},
        'delete_from_database': {'mixin_method': '_delete_from_database', 'decorator': 'write'},
        'get_image_data': {'mixin_method': '_get_image_data', 'decorator': 'read'},
        'flag_image_modification': {'mixin_method': '_flag_image_modification', 'decorator': 'write'},
    }

class ImageContentMixin:
    
    def _modify_caption(self, caption: str) -> bool:
        trace_in()
        log(f"Modifying caption for image {self.id}: '{self.caption}' -> '{caption}'")
        if caption == self.caption:
            log("Caption unchanged, no update needed")
            trace_out()
            return True
        if not is_error():
            log(f"Validating new caption '{caption}' for image {self.id}")
            if not self.validate_caption(caption):
                warn("Caption validation failed")
                report_error("action", "Caption validation failed")
            else:
                log(f"Caption validation passed for '{caption}'")
        if not is_error():
            log(f"Updating image {self.id} caption in database: '{self.caption}' -> '{caption}'")
            affected = u_query(self.conn, "UPDATE images SET caption = %s WHERE id = %s", (caption, self.id))
            if affected == 0:
                warn(f"Failed to update image {self.id} caption - no rows affected")
                report_error("action", f"Failed to update image {self.id} caption")
            else:
                log(f"Successfully updated image {self.id} caption in database")
        if not is_error():
            self.caption = caption
            log(f"Successfully updated image {self.id} caption to '{caption}'")
            self.clear_cached_image_state()
            invalidate_image_cache_entry(self.id)
            self.flag_image_modification("caption updated")
        trace_out()
        return not is_error()


    def _modify_visibility(self, visibility: int) -> bool:
        trace_in()
        log(f"Modifying visibility for image {self.id}: {self.visibility} -> {visibility}")
        if not is_error():
            affected = u_query(self.conn, "UPDATE images SET visibility = %s WHERE id = %s", (visibility, self.id))
            if affected == 0:
                warn(f"Failed to update image {self.id} visibility - no rows affected")
                report_error("action", f"Failed to update image {self.id} visibility")
            else:
                self.visibility = visibility
                log(f"Successfully updated visibility for image {self.id}")
                self.clear_cached_image_state()
                invalidate_image_cache_entry(self.id)
                self.flag_image_modification("visibility updated")
        trace_out()
        return not is_error()


    def _update_view_count(self, increment: int = 1) -> bool:
        trace_in()
        log(f"Updating view count for image {self.id}: +{increment}")
        
        if not is_error():
            affected = u_query(self.conn, "UPDATE images SET viewCount = viewCount + %s WHERE id = %s", 
                              (increment, self.id))
            if affected == 0:
                warn(f"Failed to update image {self.id} view count - no rows affected")
                report_error("action", f"Failed to update image {self.id} view count")
            else:
                self.view_count = (self.view_count or 0) + increment
                log(f"Successfully updated view count for image {self.id}")
                self.clear_cached_image_state()
                invalidate_image_cache_entry(self.id)
        
        trace_out()
        return not is_error()


    def _flag_image_modification(self, comments: str) -> bool:
        trace_in()
        note = comments or ""
        now = dt.datetime.now()
        if not is_error():
            user_results = r_query(self.conn, "SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            affected = u_query(
                self.conn,
                """
                UPDATE images
                SET last_modified = %s,
                    username = %s,
                    comments = %s
                WHERE id = %s
                """,
                (now, db_user, note, self.id),
            )
            if affected == 0:
                warn(f"Failed to flag modification for image {self.id} - no rows affected")
                report_error("action", f"Failed to flag modification for image {self.id}")
        if not is_error():
            self.last_modified = now
            self.username = db_user
            self.comments = note
            self.clear_cached_image_state()
            invalidate_image_cache_entry(self.id)
        trace_out()
        return not is_error()


    def _delete_from_database(self) -> bool:
        trace_in()
        log(f"Deleting image {self.id} from database")
        if not is_error():
            # Check if image is still used by any pages
            usage_count = self.get_usage_count()
            if usage_count > 0:
                warn(f"Cannot delete image {self.id}: still used by {usage_count} pages")
                report_error("action", f"Cannot delete image {self.id}: still used by {usage_count} pages")
                trace_out()
                return False
            # Soft delete: move files to deleted folder before removing from database
            self._soft_delete_files()
            # Delete image instances first
            d_query(self.conn, "DELETE FROM image_instances WHERE image_id = %s", [self.id])
            d_query(self.conn, "DELETE FROM images WHERE id = %s", [self.id])
            log(f"Successfully deleted image {self.id}")
            invalidate_image_cache_entry(self.id)
        trace_out()
        return not is_error()


    def _get_image_data(self) -> Dict[str, Any]:
        trace_in()
        # Get instances data to compute derived fields
        instances = self.get_instances()
        
        # Compute derived fields from instances
        max_width = 0
        max_height = 0
        max_filesize = 0
        aspect_ratio = "N/A"
        file_path = "N/A"
        
        if instances:
            max_width = max(inst.get('width', 0) for inst in instances)
            max_height = max(inst.get('height', 0) for inst in instances)
            max_filesize = max(inst.get('filesize', 0) for inst in instances)
            if max_height > 0:
                aspect_ratio = f"{max_width/max_height:.3f}"
            # Get folder path from first instance
            if instances[0].get('src'):
                src_path = instances[0]['src']
                last_slash = src_path.rfind('/')
                if last_slash != -1:
                    file_path = src_path[:last_slash + 1]
                else:
                    file_path = src_path
        
        data = {
            "id": self.id,
            "caption": self.caption,
            "username": self.username,
            "uploaded": self.uploaded,
            "last_modified": self.last_modified,
            "comments": self.comments,
            "visibility": self.visibility,
            "view_count": self.view_count,
            "instances": self.instances,
            "max_width": max_width,
            "max_height": max_height,
            "max_filesize": max_filesize,
            "aspect_ratio": aspect_ratio,
            "file_path": file_path,
            "num_instances": len(instances)
        }
        trace_out()
        return data


    def _soft_delete_files(self) -> bool:
        trace_in()
        try:
            # Load instances if not already loaded (this populates self.instances)
            self._get_instances()
            # Get project context for base path
            from hh.deploy.utils import detect_project_context
            from pathlib import Path
            project_name, _ = detect_project_context()
            base_path = Path(f"/srv/images/{project_name}")
            deleted_path = base_path / "deleted"
            # Ensure deleted directory exists (will be created when file operations execute)
            deleted_path.mkdir(parents=True, exist_ok=True)
            # Process each instance file
            for instance in self.instances:
                src_path = instance.get('src', '')
                if not src_path:
                    continue
                # Full path to the current file
                current_file = base_path / src_path
                if not current_file.exists():
                    log(f"File not found, skipping: {current_file}")
                    continue
                # Check if any other images still use this file
                if self._is_file_shared(src_path):
                    log(f"File is shared by other images, keeping: {src_path}")
                    continue
                # Schedule move file to deleted folder (buffered, will execute after DB commit)
                deleted_file = deleted_path / current_file.name
                schedule_file_move(self.conn, str(current_file), str(deleted_file))
                log(f"Scheduled file move to deleted folder: {src_path} -> deleted/{current_file.name}")
            trace_out()
            return True
        except Exception as e:
            warn(f"Failed to schedule soft delete files: {str(e)}")
            report_error("file_operation", f"Failed to schedule soft delete: {str(e)}")
            trace_out()
            return False


    def _is_file_shared(self, src_path: str) -> bool:
        try:
            query = "SELECT COUNT(*) as count FROM image_instances WHERE src = %s AND image_id != %s"
            results = r_query(self.conn, query, [src_path, self.id])
            if results:
                count = results[0]['count']
                return count > 0
            return False
        except Exception as e:
            warn(f"Failed to check if file is shared: {str(e)}")
            return False
