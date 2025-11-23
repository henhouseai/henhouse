from typing import Dict, Any, List, Optional
from pathlib import Path
from hh.gateway.connection.connection import r_query, u_query, c_query, d_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_registry import get_image # Needed for image operations
from hh.image.image import Image # Needed for image operations
from hh.page.page_registry import get_page, get_page_conn # Needed for page operations
from hh.page.page_method_registry import register_page_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_page_images_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_mixin_methods
def _register_images_methods():
    return {
        'get_images_data': {'mixin_method': '_get_images_data', 'decorator': 'read'},
        'add_image': {'mixin_method': '_add_image', 'decorator': 'write'},
        'copy_images': {'mixin_method': '_copy_images', 'decorator': 'write'},
        'move_images': {'mixin_method': '_move_images', 'decorator': 'write'},
        'set_image_rank': {'mixin_method': '_set_image_rank', 'decorator': 'write'},
        'remove_image': {'mixin_method': '_remove_image', 'decorator': 'write'},
        'reorder_images': {'mixin_method': '_reorder_images', 'decorator': 'write'},
    }


class PageImagesMixin:

    def _get_images_data(self) -> List[Dict[str, Any]]:
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'images') and self.images:
            debug(f"Page {self.id}: returning cached images")
            trace_out()
            return self.images
        # Field is empty, need to hydrate from database
        images_data = []
        if not is_error():
            try:
                results = r_query(self.conn, """
                    SELECT i.id, ig.image_rank 
                    FROM image_groups ig 
                    JOIN images i ON ig.image_id = i.id 
                    WHERE ig.page_id = %s 
                    ORDER BY ig.image_rank
                """, [self.id])
                for row in results:
                    image_id = row['id']
                    image_rank = row['image_rank']
                    image = get_image(image_id)
                    if image:
                        # Ensure instances are fully loaded before getting image_data
                        image.get_instances()
                        image_data = image.get_image_data()
                        image_data['image_rank'] = image_rank  # Add rank from image_groups
                        images_data.append(image_data)
                        log(f"Loaded image {image_id} (rank {image_rank}): {image_data.get('caption', 'untitled')}")
                    else:
                        warn(f"Failed to load image {image_id}")
                log(f"Loaded {len(images_data)} images for page {self.id}")
            except Exception as e:
                warn(f"Failed to load images for page {self.id}: {str(e)}")
                report_error("backend", f"Failed to load images: {str(e)}")
        self.images = images_data
        # Only flag cache refresh if we actually found images (data changed)
        # If we just confirmed there are no images (empty array), no need to refresh
        if images_data:
            self._flag_cache_refresh()
        trace_out()
        return images_data


    def _add_image(self, file_path: str, caption: Optional[str] = None) -> int:
        trace_in()
        log(f"Adding image to page {self.id}: {file_path}")
        # Use filename as default caption if no caption provided
        if not caption:
            caption = Path(file_path).stem  # Get filename without extension
            log(f"Using filename as caption: {caption}")
        # Create the image record in a separate write transaction
        image_id = self._create_image_record(caption=caption)
        # Add image to this page's image group
        if not is_error() and image_id:
            if not self._add_image_to_group(image_id):
                warn(f"Failed to add image {image_id} to page group")
                report_error("action", f"Failed to add image {image_id} to page group")
        # Process the image file
        if not is_error() and image_id:
            image = get_image(image_id)
            if not image:
                warn(f"Image {image_id} not found")
                report_error("action", f"Image {image_id} not found")
        if not is_error() and image_id:
            if not image.process_upload(uploaded_file_path=file_path, filename=f"image_{image_id}"):
                warn(f"Failed to process image {image_id}")
                report_error("action", f"Failed to process image {image_id}")
            else:
                image.flag_image_modification("image uploaded")
        if image_id:
            log(f"Image creation completed successfully")
        else:
            log("Image creation encountered problems")
        if image_id and not is_error():
            self._flag_page_modification("images updated")
        trace_out()
        return image_id


    def _create_image_record(self, caption: Optional[str] = None) -> int:
        trace_in()
        # Insert image record (no parent or rank - those are in image_groups)
        image_id = None
        if not is_error():
            user_results = r_query(self.conn, "SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            image_id = c_query(self.conn, """
                INSERT INTO images (caption, username, uploaded, last_modified, comments, visibility, viewCount)
                VALUES (%s, %s, NOW(), NOW(), %s, 1, 0)
            """, (caption, db_user, "image created"))
            log(f"Created image record {image_id}")
        trace_out()
        return image_id


    def _add_image_to_group(self, image_id: int, rank: Optional[int] = None) -> bool:
        trace_in()
        log(f"Adding image {image_id} to page {self.id} image group")
        if not is_error():
            # Get next rank if not provided
            if rank is None:
                results = r_query(self.conn, "SELECT COALESCE(MAX(image_rank), 0) + 1 as next_rank FROM image_groups WHERE page_id = %s", [self.id])
                rank = results[0]['next_rank'] if results else 1
            # Insert into image_groups
            new_id = c_query(self.conn, """
                INSERT INTO image_groups (page_id, image_id, image_rank)
                VALUES (%s, %s, %s)
            """, (self.id, image_id, rank))
            if new_id is not None:
                log(f"Successfully added image {image_id} to page {self.id} with rank {rank}")
                self._flag_related_image(image_id, f"added to page {self.id}")
            else:
                warn(f"Failed to add image {image_id} to page {self.id}")
                report_error("action", f"Failed to add image {image_id} to page {self.id}")
        trace_out()
        return not is_error()


    def _remove_image_from_group(self, image_id: int) -> bool:
        trace_in()
        log(f"Removing image {image_id} from page {self.id} image group")
        if not is_error():
            affected = d_query(self.conn, "DELETE FROM image_groups WHERE page_id = %s AND image_id = %s", (self.id, image_id))
            if affected == 0:
                warn(f"Failed to remove image {image_id} from page {self.id}")
                report_error("action", f"Failed to remove image {image_id} from page {self.id}")
            # Reorder remaining images
            if not is_error() and not self._reorder_images():
                warn(f"Failed to reorder images after removing image {image_id}")
                report_error("action", f"Failed to reorder images after removal")
            if not is_error():
                log(f"Successfully removed image {image_id} from page {self.id}")
                self._flag_related_image(image_id, f"removed from page {self.id}")
        trace_out()
        return not is_error()


    def _reorder_images(self) -> bool:
        trace_in()
        log(f"Reordering images in page {self.id}")
        try:
            results = r_query(self.conn, """
                SELECT image_id, image_rank FROM image_groups 
                WHERE page_id = %s 
                ORDER BY image_rank
            """, [self.id])
            for i, img in enumerate(results, 1):
                current_rank = img['image_rank']
                new_rank = i
                # Only update if the rank actually needs to change
                if current_rank != new_rank:
                    affected = u_query(self.conn, """
                        UPDATE image_groups SET image_rank = %s 
                        WHERE page_id = %s AND image_id = %s AND image_rank = %s
                    """, (new_rank, self.id, img['image_id'], current_rank))
                    if affected == 0:
                        warn(f"Failed to reorder image {img['image_id']} to rank {new_rank}")
                        report_error("action", f"Failed to reorder image {img['image_id']}")
                else:
                    log(f"Image {img['image_id']} already at correct rank {current_rank}, skipping update")
            log(f"Successfully reordered {len(results)} images in page {self.id}")
        except Exception as e:
            warn(f"Failed to reorder images in page {self.id}: {str(e)}")
            report_error("action", f"Failed to reorder images: {str(e)}")
        if not is_error():
            self._flag_page_modification("images updated")
        trace_out()
        return not is_error()


    def _copy_images(self, image_ids: List[int], target_rank: Optional[int] = None) -> bool:
        trace_in()
        log(f"Copying {len(image_ids)} images to page {self.id}")
        
        # Record original count before copying
        original_count = len(self._get_images_data())
        
        copied_count = 0
        for image_id in image_ids:
            if not is_error():
                # Add image to this page's group (one copy per image)
                if self._add_image_to_group(image_id):
                    copied_count += 1
                    log(f"Successfully copied image {image_id} to page {self.id}")
                else:
                    warn(f"Failed to copy image {image_id} to page {self.id}")
        log(f"Successfully copied {copied_count}/{len(image_ids)} images to page {self.id}")
        
        # Set ranks if target_rank is specified
        if not is_error() and target_rank is not None:
            log(f"Setting ranks starting from {target_rank}")
            
            for i, image_id in enumerate(image_ids):
                target_rank_for_image = target_rank + i
                # The copied images were added at the end, so their old ranks are original_count + i + 1
                old_rank = original_count + i + 1
                
                log(f"Setting image {image_id} from rank {old_rank} to rank {target_rank_for_image}")
                success = self._set_image_rank(image_id, old_rank, target_rank_for_image)
                if not success:
                    warn(f"Failed to set image {image_id} rank to {target_rank_for_image}")
                    report_error("action", f"Failed to set image {image_id} rank to {target_rank_for_image}")
        
        if not is_error() and copied_count > 0:
            self._flag_page_modification("images updated")
        trace_out()
        return not is_error()


    def _move_images(self, image_instances: List[Dict[str, int]], target_rank: Optional[int] = None) -> bool:
        trace_in()
        log(f"Moving {len(image_instances)} specific image instances to page {self.id}")
        
        # Record original count before moving
        original_count = len(self._get_images_data())
        
        moved_count = 0
        source_pages_affected = set()
        for instance in image_instances:
            image_id = instance['image_id']
            source_page_id = instance['source_page_id']
            source_rank = instance['source_rank']
            if not is_error():
                # Verify the specific instance exists
                results = r_query(self.conn, """
                    SELECT COUNT(*) as count FROM image_groups 
                    WHERE page_id = %s AND image_id = %s AND image_rank = %s
                """, (source_page_id, image_id, source_rank))
                if not results or results[0]['count'] == 0:
                    warn(f"Image {image_id} (rank {source_rank}) not found in source page {source_page_id}")
                    continue
                # Remove this specific instance from source page
                affected = d_query(self.conn, """
                    DELETE FROM image_groups 
                    WHERE page_id = %s AND image_id = %s AND image_rank = %s
                """, (source_page_id, image_id, source_rank))
                if affected == 0:
                    warn(f"Failed to remove image {image_id} (rank {source_rank}) from source page {source_page_id}")
                    continue
                self._flag_related_image(image_id, f"removed from page {source_page_id}")
                # Add to this page
                if self._add_image_to_group(image_id):
                    moved_count += 1
                    source_pages_affected.add(source_page_id)
                    log(f"Successfully moved image {image_id} (rank {source_rank}) from page {source_page_id} to page {self.id}")
                else:
                    warn(f"Failed to move image {image_id} (rank {source_rank}) to page {self.id}")
        # Reorder remaining images in all affected source pages using the same connection
        if not is_error() and moved_count > 0:
            for source_page_id in source_pages_affected:
                source_page = get_page_conn(self.conn, page_id=source_page_id)
                if source_page:
                    if not source_page.reorder_images():
                        warn(f"Failed to reorder images in source page {source_page_id}")
                        report_error("action", f"Failed to reorder images in source page {source_page_id}")
                else:
                    warn(f"Failed to load source page {source_page_id} for reordering")
                    report_error("action", f"Failed to load source page {source_page_id}")
        
        # Set ranks if target_rank is specified
        if not is_error() and target_rank is not None and moved_count > 0:
            log(f"Setting ranks starting from {target_rank}")
            
            for i, instance in enumerate(image_instances):
                image_id = instance['image_id']
                target_rank_for_image = target_rank + i
                # We know exactly where we placed this image
                old_rank = original_count + i + 1
                
                log(f"Setting image {image_id} from rank {old_rank} to rank {target_rank_for_image}")
                success = self._set_image_rank(image_id, old_rank, target_rank_for_image)
                if not success:
                    warn(f"Failed to set image {image_id} rank to {target_rank_for_image}")
                    report_error("action", f"Failed to set image {image_id} rank to {target_rank_for_image}")
        
        log(f"Successfully moved {moved_count} image instances to page {self.id}")
        if not is_error() and moved_count > 0:
            self._flag_page_modification("images updated")
        trace_out()
        return not is_error()


    def _set_image_rank(self, image_id: int, current_rank: int, new_rank: int) -> bool:
        trace_in()
        log(f"Setting image {image_id} rank from {current_rank} to {new_rank} in page {self.id}")
        # Validate new_rank is positive integer
        if new_rank <= 0:
            warn(f"Invalid image rank: {new_rank} (must be positive)")
            report_error("action", f"Invalid image rank: {new_rank} (must be positive)")
            trace_out()
            return False
        # Check if no update needed
        if new_rank == current_rank:
            log("Image rank unchanged, no update needed")
            trace_out()
            return True
            
        if not is_error():
            # Step 1: Delete the target row
            affected = d_query(self.conn, """
                DELETE FROM image_groups 
                WHERE page_id = %s AND image_id = %s AND image_rank = %s
            """, (self.id, image_id, current_rank))
            if affected == 0:
                warn(f"Failed to delete image {image_id} at rank {current_rank}")
                report_error("action", f"Failed to delete image {image_id} at rank {current_rank}")
                trace_out()
                return False
            
            # Step 2: Determine direction and reflow other images
            if new_rank < current_rank:
                # Moving up: scoot items DOWN (increase ranks) from current_rank-1 to new_rank (backwards)
                log(f"Moving up: scooting items down from rank {current_rank-1} to {new_rank}")
                for rank in range(current_rank - 1, new_rank - 1, -1):
                    # Get the image_id at this rank
                    results = r_query(self.conn, """
                        SELECT image_id FROM image_groups 
                        WHERE page_id = %s AND image_rank = %s
                    """, (self.id, rank))
                    if results:
                        img_id = results[0]['image_id']
                        affected = u_query(self.conn, """
                            UPDATE image_groups 
                            SET image_rank = image_rank + 1 
                            WHERE page_id = %s AND image_id = %s AND image_rank = %s
                        """, (self.id, img_id, rank))
                        if affected == 0:
                            warn(f"Failed to scoot down rank {rank}")
                            report_error("action", f"Failed to scoot down rank {rank}")
            else:
                # Moving down: scoot items UP (decrease ranks) from current_rank+1 to new_rank (forwards)
                log(f"Moving down: scooting items up from rank {current_rank+1} to {new_rank}")
                for rank in range(current_rank + 1, new_rank + 1):
                    # Get the image_id at this rank
                    results = r_query(self.conn, """
                        SELECT image_id FROM image_groups 
                        WHERE page_id = %s AND image_rank = %s
                    """, (self.id, rank))
                    if results:
                        img_id = results[0]['image_id']
                        affected = u_query(self.conn, """
                            UPDATE image_groups 
                            SET image_rank = image_rank - 1 
                            WHERE page_id = %s AND image_id = %s AND image_rank = %s
                        """, (self.id, img_id, rank))
                        if affected == 0:
                            warn(f"Failed to scoot up rank {rank}")
                            report_error("action", f"Failed to scoot up rank {rank}")
            
            # Step 3: Insert new row with desired rank
            if not is_error():
                affected = u_query(self.conn, """
                    INSERT INTO image_groups (page_id, image_id, image_rank) 
                    VALUES (%s, %s, %s)
                """, (self.id, image_id, new_rank))
                if affected == 0:
                    warn(f"Failed to insert image {image_id} at rank {new_rank}")
                    report_error("action", f"Failed to insert image {image_id} at rank {new_rank}")
            
            if not is_error():
                log(f"Successfully reordered image {image_id} to rank {new_rank} in page {self.id}")
        
        if not is_error():
            self._flag_page_modification("images updated")
        trace_out()
        return not is_error()


    def _remove_image(self, image_id: int, image_rank: int) -> bool:
        trace_in()
        log(f"Removing image {image_id} (rank {image_rank}) from page {self.id}")
        if not is_error():
            # Remove from image_groups table
            affected = d_query(self.conn, """
                DELETE FROM image_groups 
                WHERE page_id = %s AND image_id = %s AND image_rank = %s
            """, (self.id, image_id, image_rank))
            if affected == 0:
                warn(f"Failed to remove image {image_id} (rank {image_rank}) from page {self.id}")
                report_error("action", f"Failed to remove image {image_id} (rank {image_rank})")
            # Reorder remaining images in this page
            if not is_error() and not self._reorder_images():
                warn(f"Failed to reorder images after removing image {image_id}")
                report_error("action", f"Failed to reorder images after removal")
        # Check if image should be deleted (no longer used by any pages)
        if not is_error():
            image = get_image(image_id)
            if image:
                usage_count = image.get_usage_count()
                if usage_count == 0:
                    log(f"Image {image_id} no longer used by any pages, deleting from database")
                    if not image.delete_from_database():
                        warn(f"Failed to delete unused image {image_id}")
                        report_error("action", f"Failed to delete unused image {image_id}")
                else:
                    log(f"Image {image_id} still used by {usage_count} pages, keeping in database")
            else:
                warn(f"Failed to load image {image_id} for usage check")
                report_error("action", f"Failed to load image {image_id}")
        if not is_error():
            log(f"Successfully removed image {image_id} (rank {image_rank}) from page {self.id}")
            self._flag_page_modification("images updated")
            self._flag_related_image(image_id, f"removed from page {self.id}")
        trace_out()
        return not is_error()


    def _delete_all_image_groups(self) -> bool:
        trace_in()
        log(f"Deleting all image_groups entries for page {self.id}")
        if not is_error():
            # Get all unique image_ids from this page's image_groups before deleting
            results = r_query(self.conn, "SELECT DISTINCT image_id FROM image_groups WHERE page_id = %s", [self.id])
            image_ids = [row['image_id'] for row in results] if results else []
            log(f"Found {len(image_ids)} unique images in page {self.id} image_groups")
        
        if not is_error():
            # Delete all image_groups entries for this page
            affected = d_query(self.conn, "DELETE FROM image_groups WHERE page_id = %s", [self.id])
            log(f"Deleted {affected} image_groups entries for page {self.id}")
        
        # Check each image to see if it should be deleted (no longer used by any pages)
        if not is_error() and image_ids:
            for image_id in image_ids:
                if not is_error():
                    image = get_image(image_id)
                    if image:
                        usage_count = image.get_usage_count()
                        if usage_count == 0:
                            log(f"Image {image_id} no longer used by any pages, deleting from database")
                            if not image.delete_from_database():
                                warn(f"Failed to delete unused image {image_id}")
                                report_error("action", f"Failed to delete unused image {image_id}")
                        else:
                            log(f"Image {image_id} still used by {usage_count} pages, keeping in database")
                    else:
                        warn(f"Failed to load image {image_id} for usage check")
                        report_error("action", f"Failed to load image {image_id}")
        if not is_error():
            self._flag_page_modification("images updated")
        trace_out()
        return not is_error()


    def _flag_related_image(self, image_id: int, comment: str) -> None:
        if is_error() or not image_id:
            return
        image = get_image(image_id)
        if not image:
            warn(f"Failed to load image {image_id} for modification flag")
            return
        image.flag_image_modification(comment)