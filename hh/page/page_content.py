from typing import Dict, Any, List, Optional, Union
import datetime as dt
import json
import re
from copy import deepcopy
from hh.gateway.connection.connection import r_query, u_query, c_query, d_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.maintenance.job_queue import enqueue_maintenance_job
from hh.tp.tp import TextProcessor
from hh.page.page_method_registry import register_page_mixin_methods
from hh.page.page_registry import get_page, get_page_conn

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_page_content_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_mixin_methods
def _register_content_methods():
    return {
        'modify_name': {'mixin_method': '_modify_name', 'decorator': 'write'},
        'modify_text': {'mixin_method': '_modify_text', 'decorator': 'write'},
        'delete_from_database': {'mixin_method': '_delete_from_database', 'decorator': 'write'},
        'delete_page': {'mixin_method': '_delete_page', 'decorator': 'write'},
        'add_page': {'mixin_method': '_add_page', 'decorator': 'write'},
        'get_page_data': {'mixin_method': '_get_page_data', 'decorator': 'read'},
        'flag_page_modification': {'mixin_method': '_flag_page_modification', 'decorator': 'write'},
        'get_allowed_child_classes': {'mixin_method': '_get_allowed_child_classes', 'decorator': 'read'},
    }


class PageContentMixin:

    @staticmethod
    def _parse_metadata_value(metadata: Any) -> Dict[str, Any]:
        if metadata in (None, '', b''):
            return {}
        try:
            if isinstance(metadata, (bytes, bytearray)):
                metadata = metadata.decode('utf-8')
            if isinstance(metadata, str):
                parsed = json.loads(metadata)
            else:
                parsed = metadata
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
        return {}

    def _get_metadata_dict(self) -> Dict[str, Any]:
        """Return the in-memory metadata dict, normalizing raw storage as needed."""
        metadata = getattr(self, 'metadata', None)
        if isinstance(metadata, dict):
            return metadata
        parsed = self._parse_metadata_value(metadata)
        self.metadata = parsed
        return self.metadata

    def _write_metadata_dict(self, metadata: Dict[str, Any]) -> bool:
        """Persist the provided metadata dict to the database."""
        trace_in()
        metadata = metadata or {}
        metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
        success = True
        if not is_error():
            affected = u_query(self.conn, "UPDATE pages SET metadata = %s WHERE id = %s", (metadata_json, self.id))
            if affected == 0:
                log(f"Metadata for page {self.id} already up to date; no rows affected")
        if success:
            self.metadata = metadata
        trace_out()
        return success and not is_error()

    def get_metadata_namespace(
        self,
        namespace: str,
        default: Optional[Dict[str, Any]] = None,
        persist_if_missing: bool = False,
    ) -> Dict[str, Any]:
        metadata = self._get_metadata_dict()
        bucket = metadata.get(namespace)
        if not isinstance(bucket, dict):
            if default is None:
                bucket = {}
            elif isinstance(default, dict):
                bucket = deepcopy(default)
            else:
                bucket = default
            if not isinstance(bucket, dict):
                bucket = {}
            metadata[namespace] = bucket
            if persist_if_missing:
                self._write_metadata_dict(metadata)
        return bucket

    def set_metadata_namespace(self, namespace: str, data: Dict[str, Any]) -> bool:
        metadata = self._get_metadata_dict()
        metadata[namespace] = data if isinstance(data, dict) else {}
        return self._write_metadata_dict(metadata)

    def get_metadata_value(self, key: str, default: Any = None, namespace: Optional[str] = None) -> Any:
        """Retrieve a metadata value from the specified namespace (or root)."""
        trace_in()
        metadata = self._get_metadata_dict()
        container: Any = metadata
        if namespace:
            container = metadata.get(namespace)
            if not isinstance(container, dict):
                container = {}
        if not isinstance(container, dict):
            trace_out()
            return default
        value = container.get(key, default)
        trace_out()
        return value

    def set_metadata_value(self, key: str, value: Any, namespace: Optional[str] = None) -> bool:
        """Set a metadata value inside the specified namespace (or root) and persist it."""
        trace_in()
        metadata = self._get_metadata_dict()
        if namespace:
            bucket = metadata.get(namespace)
            if not isinstance(bucket, dict):
                bucket = {}
                metadata[namespace] = bucket
        else:
            bucket = metadata
        bucket[key] = value
        result = self._write_metadata_dict(metadata)
        trace_out()
        return result
    
    @classmethod
    def add_page_class_information(cls, new_page_id: int, conn: DatabaseConnection):
        """
        Hook called after page creation to add class-specific data.
        This is a classmethod (like PHP's static method) so it can be called on the class
        without needing an instance. Subclasses should override this.
        """
        pass
    

    def delete_page_class_information(self):
        pass


    def _modify_name(self, name: Optional[str] = None) -> bool:
        trace_in()
        # Normalize: convert None or empty string to None for database storage
        name_value = None if (name is None or (isinstance(name, str) and len(name.strip()) == 0)) else name
        current_name = self.name if self.name is not None else None
        log(f"Starting name modification for page {self.id}: '{current_name}' -> '{name_value}'")
        if name_value == current_name:
            log("Name unchanged, no update needed")
            trace_out()
            return True
        old_name = self.name
        log(f"Old name: '{old_name}', new name: '{name_value}'")
        if not is_error():
            # For validation, pass empty string if name_value is None (validation expects string)
            validation_name = name_value if name_value is not None else ""
            log(f"Validating new name '{validation_name}' for page {self.id}")
            parent_page = get_page(page_id=self.parent)
            if not parent_page:
                warn(f"Parent page {self.parent} not found for validation")
                report_error("action", f"Parent page {self.parent} not found")
            elif not parent_page.validate_name(validation_name, self.class_name, exclude_id=self.id):
                warn("Page name validation failed")
                report_error("action", "Page name validation failed")
            else:
                log(f"Name validation passed for '{validation_name}'")
        if not is_error():
            log(f"Updating page {self.id} name in database: '{old_name}' -> '{name_value}'")
            affected = u_query(self.conn, "UPDATE pages SET name = %s WHERE id = %s", (name_value, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} name - no rows affected")
                report_error("action", f"Failed to update page {self.id} name")
            else:
                log(f"Successfully updated page {self.id} name in database")
        if not is_error():
            if self.name == self.link:
                log(f"Page {self.id} has auto-link enabled (name == link), updating link as well")
                link_value = name_value if (self.auto_link_name() and name_value is not None) else None
                log(f"Setting link to: {link_value}")
                affected = u_query(self.conn, "UPDATE pages SET link = %s WHERE id = %s", (link_value, self.id))
                if affected == 0:
                    warn(f"Failed to update page {self.id} link - no rows affected")
                    report_error("action", f"Failed to update page {self.id} link")
                else:
                    self.link = link_value
                    log(f"Successfully updated page {self.id} link to '{link_value}'")
            else:
                log(f"Page {self.id} does not have auto-link enabled, skipping link update")
        if not is_error():
            modification_type = 'name and link' if self.auto_link_name() else 'name'
            log(f"Flagging page modification: {modification_type} changed")
            self.flag_page_modification(f"{modification_type} changed")
        if not is_error() and old_name and name_value:
            try:
                job_id = enqueue_maintenance_job(
                    self.conn,
                    "page_name_update",
                    {
                        "page_id": self.id,
                        "old_name": old_name,
                        "new_name": name_value,
                    },
                )
                log(f"Enqueued maintenance job {job_id} for page {self.id} name change")
            except Exception as exc:  # noqa: BLE001
                warn(f"Failed to enqueue maintenance job for page {self.id}: {exc}")
        if not is_error():
            self.name = name_value
            log(f"Successfully updated page {self.id} name to '{name_value}'")
        trace_out()
        return not is_error()

    @staticmethod
    def _maintenance_replace_name_tokens(text: str, old_name: str, new_name: str) -> str:
        if not text or not old_name or not new_name:
            return text
        replacements = [
            (f"[[{old_name}]]", f"[[{new_name}]]"),
            (f"[[{old_name}][", f"[[{new_name}]["),
            (f"{{{{{old_name}}}}}", f"{{{{{new_name}}}}}"),
            (f"{{{{{old_name}}}{{", f"{{{{{new_name}}}{{"),
        ]
        updated = text
        for pattern, replacement in replacements:
            updated = re.sub(re.escape(pattern), replacement, updated)
        return updated

    def maintenance_process_name_change(
        self,
        *,
        old_name: str,
        new_name: str,
        last_page_id: int = 0,
        batch_limit: int = 25,
    ) -> Dict[str, Any]:
        trace_in()
        result = {"processed": 0, "last_page_id": last_page_id, "done": False}
        if not old_name or not new_name:
            result["done"] = True
            trace_out()
            return result

        limit = max(1, batch_limit)
        rows = r_query(
            self.conn,
            """
            SELECT DISTINCT id
            FROM links
            WHERE resolution_id = %s
              AND link NOT REGEXP '^[0-9]+$'
              AND id > %s
            ORDER BY id
            LIMIT %s
            """,
            (self.id, last_page_id, limit),
        )

        if not rows:
            result["done"] = True
            trace_out()
            return result

        for row in rows:
            ref_page_id = row["id"]
            ref_page = get_page_conn(self.conn, ref_page_id)
            if not ref_page:
                warn(f"Referenced page {ref_page_id} not found during rename maintenance")
                result["last_page_id"] = ref_page_id
                continue

            existing_text = ref_page.text or ""
            updated_text = self._maintenance_replace_name_tokens(existing_text, old_name, new_name)
            if updated_text != existing_text:
                if not ref_page.modify_text(updated_text):
                    raise RuntimeError(f"Failed to update text for referenced page {ref_page_id}")

            affected = u_query(
                self.conn,
                """
                UPDATE links
                SET link = %s
                WHERE id = %s
                  AND resolution_id = %s
                  AND link NOT REGEXP '^[0-9]+$'
                """,
                (new_name, ref_page_id, self.id),
            )
            if affected == 0:
                warn(f"Links table update affected 0 rows for page {ref_page_id}")

            result["processed"] += 1
            result["last_page_id"] = ref_page_id

        trace_out()
        return result


    def _modify_text(self, text: str) -> bool:
        trace_in()
        # Check if text is actually changing
        if text == self.text:
            log(f"Text modification skipped for page {self.id}: content unchanged (length: {len(text)})")
            trace_out()
            return True
        # Validate text with TextProcessor
        processor = TextProcessor()
        preprocessed = processor.preprocess(text)
        if preprocessed is None:
            log(f"Text modification failed for page {self.id}: TextProcessor validation failed - parse errors detected in text (length: {len(text)})")
            trace_out()
            return False
        if not is_error():
            # Text validation passed, proceed with update
            text_value = None if text == "" else text
            affected = u_query(self.conn, "UPDATE pages SET text = %s WHERE id = %s", (text_value, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} text - no rows affected")
                report_error("action", f"Failed to update page {self.id} text")
        if not is_error():
            self.flag_page_modification("text changed")
        if not is_error():
            # Update links table with parsed link information (like PHP version)
            if not processor.update_links_table(self.conn, self.id):
                log(f"Text modification failed for page {self.id}: database update succeeded but links table update failed")
                warn("Failed to update links table")
                report_error("action", "Failed to update links table")
                trace_out()
                return False
        if not is_error():
            debug(f"Triggering cache update for page {self.id} after text change")
            self.refresh_cached_page(text_value, preprocessed)
        if not is_error():
            # Update object property to match what was stored in database
            self.text = None if text == "" else text
            log(f"Text modification completed for page {self.id}: updated text (length: {len(text)}), validated with TextProcessor, updated links table")
        trace_out()
        return not is_error()


    def _delete_from_database(self) -> bool:
        trace_in()
        log(f"Deleting page {self.id} from database")
        success = False
        if not is_error():
            affected = d_query(self.conn, "DELETE FROM pages WHERE id = %s", [self.id])
            if affected > 0:
                success = True
                log(f"Successfully deleted page {self.id} from database")
            else:
                warn(f"Failed to delete page {self.id} - no rows affected")
                report_error("action", f"Failed to delete page {self.id}")
        else:
            log(f"Failed to delete page {self.id} from database due to errors")
        trace_out()
        return success
    

    def _delete_page(self) -> bool:
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available")
            report_error("action", "No gateway available")
        if not is_error():
            confirm = gateway.get_arg('confirm')
            if not confirm:
                warn("Confirmation required for page deletion")
                report_error("action", "Confirmation required for page deletion")
        if not is_error():
            child_ids = self.get_child_page_ids()
        if not is_error():
            for child_id in child_ids:
                if not is_error():
                    child_page = get_page_conn(self.conn, child_id)
                    if child_page:
                        child_page.delete_page()  # Recursive call - uses same connection/transaction
                    else:
                        warn(f"Failed to load child page {child_id}")
                        report_error("action", f"Failed to load child page {child_id}")
        if not is_error():
            # Delete all image_groups entries and clean up unused images before deleting page
            if hasattr(self, '_delete_all_image_groups'):
                if not self._delete_all_image_groups():
                    warn(f"Failed to delete image_groups for page {self.id}")
                    report_error("action", f"Failed to delete image_groups for page {self.id}")
        if not is_error():
            # Call hook to clean up class-specific data before deleting
            self.delete_page_class_information()
        if not is_error():
            success = self._delete_from_database()
            if not success:
                warn(f"Failed to delete page {self.id}")
                report_error("action", f"Failed to delete page {self.id}")
        trace_out()
        return not is_error()

    def _add_page(self, page_class: str = 'page', name: Optional[str] = None) -> int:
        trace_in()
        # Get current database user
        user_results = r_query(self.conn, "SELECT USER() as db_user")
        db_user = user_results[0]['db_user'] if user_results else 'unknown'
        
        # Look up the page class to check its configuration
        from hh.page.page_class_registry import get_page_class
        NewPageClass = get_page_class(page_class)
        if not NewPageClass:
            warn(f"Page class '{page_class}' not found")
            report_error("action", f"Page class '{page_class}' not found")
            trace_out()
            return None
        
        # Check if this parent can contain the new page class
        if not is_error():
            if not self.allow_class_inside(page_class):
                warn(f"Page {self.id} (class={self.class_name}) cannot contain pages with class={page_class}")
                report_error("action", f"Page {self.id} cannot contain pages with class '{page_class}'")
        
        # Check if new page class can be inside this parent (static method on new page's class)
        if not is_error():
            if not NewPageClass.allow_inside_of(self.class_name):
                warn(f"Page class '{page_class}' cannot be inside page class '{self.class_name}'")
                report_error("action", f"Page class '{page_class}' cannot be inside page class '{self.class_name}'")
        
        # Check if null names are allowed for this class
        if not is_error():
            allow_null = NewPageClass.allow_null_names()
            if not allow_null and (not name or len(name.strip()) == 0):
                warn(f"Page class '{page_class}' does not allow null names")
                report_error("action", f"Page class '{page_class}' requires a name")
        
        # Validate name if provided
        if not is_error() and name:
            if not self.validate_name(name, page_class):
                warn("Page name validation failed")
                report_error("action", "Page name validation failed")
        
        # Determine link value based on auto_link_name setting
        new_page_id = None
        if not is_error():
            # Normalize: convert empty string to None for database storage (like _modify_name does)
            name_value = None if (name is None or (isinstance(name, str) and len(name.strip()) == 0)) else name
            auto_link = NewPageClass.auto_link_name()
            # Set link_value: if auto_link is True and name_value is provided, use name_value as link
            # Otherwise, set to None
            link_value = name_value if (auto_link and name_value is not None) else None
            
            try:
                now = dt.datetime.now()
                new_page_id = c_query(self.conn, """
                    INSERT INTO pages (parent, name, link, class, last_modified, username, visibility, displayStyle)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, 1)
                """, (self.id, name_value, link_value, page_class, now, db_user))
                log(f"Created new page: id={new_page_id}, name='{name_value}', parent={self.id}, class='{page_class}'")
            except Exception as e:
                warn(f"Failed to create page: {str(e)}")
                report_error("backend", f"Failed to create page: {str(e)}")
        if not is_error() and new_page_id:
            # Call hook to initialize class-specific data
            # Get the page class for the new page and call its static method
            # This matches PHP pattern: call_user_func(array($classTranslationArray[$class]['upper'], 'addPageClassInformation'), ...)
            from hh.page.page_class_registry import get_page_class
            NewPageClass = get_page_class(page_class)
            if not NewPageClass:
                warn(f"Page class '{page_class}' not found")
                report_error("action", f"Page class '{page_class}' not found")
            else:
                # Call the classmethod on the new page's class
                NewPageClass.add_page_class_information(new_page_id, self.conn)
        if new_page_id:
            log("Page creation completed successfully")
        else:
            log("Page creation encountered problems")
        trace_out()
        return new_page_id

    def _get_allowed_child_classes(self) -> List[Dict[str, Any]]:
        """Get list of page classes that are allowed as children of this page."""
        trace_in()
        from hh.page.page_class_registry import get_all_page_classes, get_page_class
        
        allowed_classes = []
        
        # Get all registered page classes
        all_classes = get_all_page_classes()
        log(f"Checking {len(all_classes)} page classes for compatibility with parent page {self.id} (class={self.class_name})")
        
        # Check each class
        for class_name, PageClass in all_classes.items():
            if PageClass is None:
                continue
            
            # Check both conditions (same as _add_page does)
            # 1. Parent can contain this class
            parent_allows = self.allow_class_inside(class_name)
            # 2. Child class can be inside parent
            child_allows = PageClass.allow_inside_of(self.class_name)
            
            if parent_allows and child_allows:
                # Both checks passed - this class is allowed
                allow_null = PageClass.allow_null_names()
                allow_duplicate = PageClass.allow_duplicate_names()
                auto_link = PageClass.auto_link_name()
                allowed_classes.append({
                    'class_name': class_name,
                    'allow_null_names': allow_null,
                    'allow_duplicate_names': allow_duplicate,
                    'auto_link_name': auto_link
                })
                log(f"Class '{class_name}' is allowed (allow_null_names={allow_null}, allow_duplicate_names={allow_duplicate}, auto_link_name={auto_link})")
            else:
                log(f"Class '{class_name}' is not allowed (parent_allows={parent_allows}, child_allows={child_allows})")
        
        log(f"Found {len(allowed_classes)} allowed child classes for page {self.id}")
        trace_out()
        return allowed_classes

    def _get_page_data(self) -> Dict[str, Any]:
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "link": self.link,
            "parent": self.parent,
            "class": self.class_name,
            "visibility": self.visibility,
            "text": self.text,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "username": self.username,
            "comments": self.comments
        }
        # Add breadcrumb path if available
        if hasattr(self, '_get_path'):
            path_data = self._get_path()
            if path_data:
                data['path'] = path_data
        trace_out()
        return data
    
    def get_child_page_data(self) -> Dict[str, Any]:
        """Return simplified data for child pages in tables: id, name, parent, class."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "parent": self.parent,
            "class": self.class_name
        }
        trace_out()
        return data
    
    
    def _flag_page_modification(self, comments: str) -> bool:
        """Standardized method to update page modification audit trail"""
        trace_in()
        now = dt.datetime.now()
        if not is_error():
            user_results = r_query(self.conn, "SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            affected = u_query(self.conn, """
                UPDATE pages SET last_modified = %s, username = %s, comments = %s WHERE id = %s
            """, (now, db_user, comments, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} modification flags - no rows affected")
                report_error("action", f"Failed to update page {self.id} modification flags")
        if not is_error():
            # Update object properties to match database
            self.last_modified = now
            self.username = db_user
            self.comments = comments
            log(f"Updated page {self.id} modification flags: {comments}")
            self.clear_cached_payload_state()
        trace_out()
        return not is_error()
