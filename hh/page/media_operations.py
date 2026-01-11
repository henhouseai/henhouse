"""
Media Operations for Page Class

This module contains all media-related operations that were extracted from the Page class
to reduce its size and improve maintainability.

Functions in this module operate on a Page instance passed as the first parameter.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page

if TYPE_CHECKING:
    from hh.page.page import Page

trace_in = get_trace_in()
trace_out = get_trace_out()
log = get_log()
debug = get_debug()
warn = get_warn()


# Static helper methods (originally @staticmethod in Page class)

def get_media_table_name(media_type: str) -> str:
    """Get table name for media type (e.g., 'image' -> 'image_groups')."""
    return f"{media_type}_groups"


def get_media_id_field(media_type: str) -> str:
    """Get ID field name for media type (e.g., 'image' -> 'image_id')."""
    return f"{media_type}_id"


def get_media_rank_field(media_type: str) -> str:
    """Get rank field name for media type (e.g., 'image' -> 'image_rank')."""
    return f"{media_type}_rank"


def validate_media_type(media_type: str) -> str:
    """Validate media type and return normalized version (defaults to 'file')."""
    if not media_type:
        return "file"
    media_type = media_type.lower()
    # Import here to avoid circular import
    from hh.page.page import Page
    if media_type not in Page.MEDIA_TYPES:
        warn(f"Invalid media type: {media_type}. Must be one of {Page.MEDIA_TYPES}")
        report_error("action", f"Invalid media type: {media_type}")
        return "file"  # Default fallback
    return media_type


# Instance helper methods (originally instance methods in Page class)

def get_media_data_method(page: 'Page', media_type: str):
    """Get the data retrieval method for media type."""
    method_map = {
        "image": page.get_images_data,
        "audio": page.get_audio_data if hasattr(page, 'get_audio_data') else None,
        "video": page.get_video_data if hasattr(page, 'get_video_data') else None,
        "file": page.get_files_data,
    }
    return method_map.get(media_type)


def get_add_to_group_method(page: 'Page', media_type: str):
    """Get the add-to-group method for media type."""
    method_map = {
        "image": page._add_image_to_group,
        "audio": page._add_audio_to_group if hasattr(page, '_add_audio_to_group') else None,
        "video": page._add_video_to_group if hasattr(page, '_add_video_to_group') else None,
        "file": page._add_file_to_group,
    }
    return method_map.get(media_type)


def get_reorder_method(page: 'Page', media_type: str):
    """Get the reorder method for media type."""
    method_map = {
        "image": page.reorder_images,
        "audio": page.reorder_audio if hasattr(page, 'reorder_audio') else None,
        "video": page.reorder_video if hasattr(page, 'reorder_video') else None,
        "file": page.reorder_files,
    }
    return method_map.get(media_type)


def get_flag_related_method(page: 'Page', media_type: str):
    """Get the flag-related method for media type (if exists)."""
    method_map = {
        "image": page._flag_related_image,
        "file": page._flag_related_file,
    }
    return method_map.get(media_type)


def get_usage_count_method(page: 'Page', media_type: str):
    """Get the usage count method for media type (if exists)."""
    if media_type == "file":
        return page._get_file_usage_count
    elif media_type == "image":
        # Images have get_usage_count on the Image object itself
        return None
    return None


# Main media operations

def copy_media_items(page: 'Page', media_type: str, item_ids: List[int], target_rank: Optional[int] = None) -> bool:
    """
    Generalized method to copy media items (images, audio, video, files) to this page.

    Args:
        page: The Page instance to operate on
        media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
        item_ids: List of item IDs to copy
        target_rank: Optional target rank to insert at (1-based)

    Returns:
        bool: True if successful, False otherwise
    """
    trace_in()
    media_type = validate_media_type(media_type)
    if is_error():
        trace_out()
        return False

    log(f"Copying {len(item_ids)} {media_type} items to page {page.id}")

    # Get helper methods
    get_data_method = get_media_data_method(page, media_type)
    add_to_group_method = get_add_to_group_method(page, media_type)

    if not get_data_method or not add_to_group_method:
        warn(f"Required methods not found for media type {media_type}")
        report_error("action", f"Media type {media_type} not fully supported")
        trace_out()
        return False

    # Record original count before copying
    original_count = len(get_data_method())

    copied_count = 0
    for item_id in item_ids:
        if not is_error():
            if add_to_group_method(item_id):
                copied_count += 1
                log(f"Successfully copied {media_type} {item_id} to page {page.id}")
                # Flag related item if method exists
                flag_method = get_flag_related_method(page, media_type)
                if flag_method:
                    flag_method(item_id, f"copied to page {page.id}")
            else:
                warn(f"Failed to copy {media_type} {item_id} to page {page.id}")

    log(f"Successfully copied {copied_count}/{len(item_ids)} {media_type} items to page {page.id}")

    # Set ranks if target_rank is specified
    if not is_error() and target_rank is not None and copied_count > 0:
        log(f"Setting ranks starting from {target_rank}")
        for i, item_id in enumerate(item_ids[:copied_count]):
            target_rank_for_item = target_rank + i
            # The copied items were added at the end, so their old ranks are original_count + i + 1
            old_rank = original_count + i + 1

            log(f"Setting {media_type} {item_id} from rank {old_rank} to rank {target_rank_for_item}")
            success = set_media_rank(page, media_type, item_id, old_rank, target_rank_for_item)
            if not success:
                warn(f"Failed to set {media_type} {item_id} rank to {target_rank_for_item}")
                report_error("action", f"Failed to set {media_type} {item_id} rank to {target_rank_for_item}")

    if not is_error() and copied_count > 0:
        # Rebuild hot cache immediately with the copied items
        get_data_method(rebuild=True)
        page.flag_page_modification(f"{media_type}s updated")

    trace_out()
    return not is_error()


def move_media_items(page: 'Page', media_type: str, item_instances: List[Dict[str, int]], target_rank: Optional[int] = None) -> bool:
    """
    Generalized method to move media items (images, audio, video, files) from source pages to this page.

    Args:
        page: The Page instance to operate on
        media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
        item_instances: List of dicts with keys: {media_type}_id, source_page_id, source_rank
        target_rank: Optional target rank to insert at (1-based)

    Returns:
        bool: True if successful, False otherwise
    """
    trace_in()
    media_type = validate_media_type(media_type)
    if is_error():
        trace_out()
        return False

    if not item_instances:
        trace_out()
        return True

    log(f"Moving {len(item_instances)} {media_type} instances to page {page.id}")

    # Get helper methods and field names
    get_data_method = get_media_data_method(page, media_type)
    add_to_group_method = get_add_to_group_method(page, media_type)
    reorder_method = get_reorder_method(page, media_type)
    table_name = get_media_table_name(media_type)
    id_field = get_media_id_field(media_type)
    rank_field = get_media_rank_field(media_type)

    if not get_data_method or not add_to_group_method or not reorder_method:
        warn(f"Required methods not found for media type {media_type}")
        report_error("action", f"Media type {media_type} not fully supported")
        trace_out()
        return False

    # Record original count before moving
    original_count = len(get_data_method())

    moved_count = 0
    source_pages_affected = set()
    for instance in item_instances:
        if is_error():
            break

        item_id = instance[id_field]
        source_page_id = instance["source_page_id"]
        source_rank = instance["source_rank"]

        if not is_error():
            # Verify the specific instance exists
            results = page.gateway.conn.read(f"""
                SELECT COUNT(*) as count FROM {table_name}
                WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
            """, (source_page_id, item_id, source_rank))
            if not results or results[0]['count'] == 0:
                warn(f"{media_type.capitalize()} {item_id} (rank {source_rank}) not found in source page {source_page_id}")
                continue

            # Remove this specific instance from source page
            affected = page.gateway.conn.delete(f"""
                DELETE FROM {table_name}
                WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
            """, (source_page_id, item_id, source_rank))
            if affected == 0:
                warn(f"Failed to remove {media_type} {item_id} (rank {source_rank}) from source page {source_page_id}")
                continue

            # Flag related item if method exists
            flag_method = get_flag_related_method(page, media_type)
            if flag_method:
                flag_method(item_id, f"removed from page {source_page_id}")

            # Add to this page
            if add_to_group_method(item_id):
                moved_count += 1
                source_pages_affected.add(source_page_id)
                log(f"Successfully moved {media_type} {item_id} (rank {source_rank}) from page {source_page_id} to page {page.id}")
                if flag_method:
                    flag_method(item_id, f"moved to page {page.id}")
            else:
                warn(f"Failed to move {media_type} {item_id} (rank {source_rank}) to page {page.id}")

    # Reorder remaining items in all affected source pages
    if not is_error() and moved_count > 0:
        for source_page_id in source_pages_affected:
            source_page = get_page(page_id=source_page_id)
            if source_page:
                source_reorder_method = get_reorder_method(source_page, media_type)
                if source_reorder_method:
                    if not source_reorder_method():
                        warn(f"Failed to reorder {media_type}s in source page {source_page_id}")
                        report_error("action", f"Failed to reorder {media_type}s in source page {source_page_id}")
                    # Rebuild source page hot cache immediately
                    source_get_data_method = get_media_data_method(source_page, media_type)
                    if source_get_data_method:
                        source_get_data_method(rebuild=True)
            else:
                warn(f"Source page {source_page_id} not found for reordering")

    # Set ranks for moved items if target_rank is specified
    if not is_error() and target_rank is not None and moved_count > 0:
        log(f"Setting ranks for moved items starting from {target_rank}")
        # The moved items were added at the end, so their current ranks start from original_count + 1
        for i, instance in enumerate(item_instances[:moved_count]):
            item_id = instance[id_field]
            old_rank = original_count + i + 1
            new_rank = target_rank + i

            log(f"Setting moved {media_type} {item_id} from rank {old_rank} to rank {new_rank}")
            success = set_media_rank(page, media_type, item_id, old_rank, new_rank)
            if not success:
                warn(f"Failed to set moved {media_type} {item_id} rank to {new_rank}")
                report_error("action", f"Failed to set moved {media_type} {item_id} rank to {new_rank}")

    if not is_error() and moved_count > 0:
        # Rebuild hot cache immediately with the moved items
        get_data_method(rebuild=True)
        page.flag_page_modification(f"{media_type}s updated")

    trace_out()
    return not is_error()


def set_media_rank(page: 'Page', media_type: str, item_id: int, current_rank: int, new_rank: int) -> bool:
    """
    Generalized method to set the rank of a media item (image, audio, video, file) within this page.
    Uses hybrid approach: efficient delete-and-reflow for single moves, then verifies sequential ranks.

    Args:
        page: The Page instance to operate on
        media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
        item_id: ID of the item to reorder
        current_rank: Current rank of the item (1-based)
        new_rank: Desired new rank of the item (1-based)

    Returns:
        bool: True if successful, False otherwise
    """
    trace_in()
    media_type = validate_media_type(media_type)
    if is_error():
        trace_out()
        return False

    log(f"Setting {media_type} {item_id} rank from {current_rank} to {new_rank} in page {page.id}")

    # Validate new_rank is positive integer
    if new_rank <= 0:
        warn(f"Invalid {media_type} rank: {new_rank} (must be positive)")
        report_error("action", f"Invalid {media_type} rank: {new_rank} (must be positive)")
        trace_out()
        return False

    # Check if no update needed
    if new_rank == current_rank:
        log(f"{media_type.capitalize()} rank unchanged, no update needed")
        trace_out()
        return True

    # Get helper methods and field names
    get_data_method = get_media_data_method(page, media_type)
    reorder_method = get_reorder_method(page, media_type)
    table_name = get_media_table_name(media_type)
    id_field = get_media_id_field(media_type)
    rank_field = get_media_rank_field(media_type)

    if not get_data_method or not reorder_method:
        warn(f"Required methods not found for media type {media_type}")
        report_error("action", f"Media type {media_type} not fully supported")
        trace_out()
        return False

    if not is_error():
        # Step 1: Delete the target row
        affected = page.gateway.conn.delete(f"""
            DELETE FROM {table_name}
            WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
        """, (page.id, item_id, current_rank))
        if affected == 0:
            warn(f"Failed to delete {media_type} {item_id} at rank {current_rank}")
            report_error("action", f"Failed to delete {media_type} {item_id} at rank {current_rank}")
            trace_out()
            return False

        # Step 2: Determine direction and reflow other items
        if new_rank < current_rank:
            # Moving up: scoot items DOWN (increase ranks) from current_rank-1 to new_rank (backwards)
            log(f"Moving up: scooting items down from rank {current_rank-1} to {new_rank}")
            for rank in range(current_rank - 1, new_rank - 1, -1):
                # Get the item_id at this rank
                results = page.gateway.conn.read(f"""
                    SELECT {id_field} FROM {table_name}
                    WHERE page_id = %s AND {rank_field} = %s
                """, (page.id, rank))
                if results:
                    other_item_id = results[0][id_field]
                    affected = page.gateway.conn.update(f"""
                        UPDATE {table_name}
                        SET {rank_field} = {rank_field} + 1
                        WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                    """, (page.id, other_item_id, rank))
                    if affected == 0:
                        warn(f"Failed to scoot down rank {rank}")
                        report_error("action", f"Failed to scoot down rank {rank}")
        else:
            # Moving down: scoot items UP (decrease ranks) from current_rank+1 to new_rank (forwards)
            log(f"Moving down: scooting items up from {current_rank+1} to {new_rank}")
            for rank in range(current_rank + 1, new_rank + 1):
                # Get the item_id at this rank
                results = page.gateway.conn.read(f"""
                    SELECT {id_field} FROM {table_name}
                    WHERE page_id = %s AND {rank_field} = %s
                """, (page.id, rank))
                if results:
                    other_item_id = results[0][id_field]
                    affected = page.gateway.conn.update(f"""
                        UPDATE {table_name}
                        SET {rank_field} = {rank_field} - 1
                        WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                    """, (page.id, other_item_id, rank))
                    if affected == 0:
                        warn(f"Failed to scoot up rank {rank}")
                        report_error("action", f"Failed to scoot up rank {rank}")

        # Step 3: Insert new row with desired rank
        if not is_error():
            new_id = page.gateway.conn.create(f"""
                INSERT INTO {table_name} (page_id, {id_field}, {rank_field})
                VALUES (%s, %s, %s)
            """, (page.id, item_id, new_rank))
            if new_id is None:
                warn(f"Failed to insert {media_type} {item_id} at rank {new_rank}")
                report_error("action", f"Failed to insert {media_type} {item_id} at rank {new_rank}")

        # Step 4: Verify and fix any gaps (ensure sequential ranks 1, 2, 3...)
        if not is_error():
            log(f"Verifying sequential ranks for {media_type}s in page {page.id}")
            # Get all items ordered by current rank
            results = page.gateway.conn.read(f"""
                SELECT {id_field}, {rank_field} FROM {table_name}
                WHERE page_id = %s
                ORDER BY {rank_field}
            """, [page.id])

            if results:
                # Check if ranks are sequential (1, 2, 3...)
                needs_reflow = False
                for i, row in enumerate(results, start=1):
                    if row[rank_field] != i:
                        needs_reflow = True
                        break

                # If gaps found, reflow everything to ensure sequential ranks
                if needs_reflow:
                    log(f"Gaps detected in {media_type} ranks, reflowing to ensure sequential order")
                    for i, row in enumerate(results, start=1):
                        current_db_rank = row[rank_field]
                        if current_db_rank != i:
                            affected = page.gateway.conn.update(f"""
                                UPDATE {table_name}
                                SET {rank_field} = %s
                                WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                            """, (i, page.id, row[id_field], current_db_rank))
                            if affected == 0:
                                warn(f"Failed to reflow {media_type} {row[id_field]} to rank {i}")
                                report_error("action", f"Failed to reflow {media_type} {row[id_field]}")
                    log(f"Successfully reflowed {len(results)} {media_type}s to sequential ranks")
                else:
                    log(f"All {len(results)} {media_type}s already have sequential ranks")

        if not is_error():
            log(f"Successfully reordered {media_type} {item_id} to rank {new_rank} in page {page.id}")
            # Rebuild hot cache immediately with updated ranks
            get_data_method(rebuild=True)

    if not is_error():
        page.flag_page_modification(f"{media_type}s updated")

    trace_out()
    return not is_error()


def remove_media_item(page: 'Page', media_type: str, item_id: int, item_rank: int) -> bool:
    """
    Generalized method to remove a media item (image, audio, video, file) from this page.

    Args:
        page: The Page instance to operate on
        media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
        item_id: ID of the item to remove
        item_rank: Rank of the item to remove (1-based)

    Returns:
        bool: True if successful, False otherwise
    """
    trace_in()
    media_type = validate_media_type(media_type)
    if is_error():
        trace_out()
        return False

    log(f"Removing {media_type} {item_id} (rank {item_rank}) from page {page.id}")

    # Get helper methods and field names
    get_data_method = get_media_data_method(page, media_type)
    reorder_method = get_reorder_method(page, media_type)
    table_name = get_media_table_name(media_type)
    id_field = get_media_id_field(media_type)
    rank_field = get_media_rank_field(media_type)

    if not get_data_method or not reorder_method:
        warn(f"Required methods not found for media type {media_type}")
        report_error("action", f"Media type {media_type} not fully supported")
        trace_out()
        return False

    if not is_error():
        # Remove from groups table
        affected = page.gateway.conn.delete(f"""
            DELETE FROM {table_name}
            WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
        """, (page.id, item_id, item_rank))
        if affected == 0:
            warn(f"Failed to remove {media_type} {item_id} (rank {item_rank}) from page {page.id}")
            report_error("action", f"Failed to remove {media_type} {item_id} (rank {item_rank})")

        # Reorder remaining items in this page
        if not is_error() and not reorder_method():
            warn(f"Failed to reorder {media_type}s after removing {media_type} {item_id}")
            report_error("action", f"Failed to reorder {media_type}s after removal")

        # Rebuild hot cache immediately without the removed item
        get_data_method(rebuild=True)

    # Check if item should be deleted (no longer used by any pages)
    if not is_error():
        # Get usage count method if it exists
        usage_count_method = get_usage_count_method(page, media_type)
        if usage_count_method:
            usage_count = usage_count_method(item_id)
            if usage_count == 0:
                log(f"{media_type.capitalize()} {item_id} no longer used by any pages, deleting from database")
                # Import and delete the item object
                if media_type == "image":
                    from hh.image.image_registry import get_image
                    image_obj = get_image(item_id)
                    if image_obj and hasattr(image_obj, 'delete_from_database'):
                        if not image_obj.delete_from_database():
                            warn(f"Failed to delete unused {media_type} {item_id}")
                            report_error("action", f"Failed to delete unused {media_type} {item_id}")
                elif media_type == "file":
                    from hh.file.file_registry import get_file
                    file_obj = get_file(file_id=item_id)
                    if file_obj and hasattr(file_obj, 'delete_from_database'):
                        file_obj.delete_from_database()
                # Audio/video deletion would go here when implemented
            else:
                log(f"{media_type.capitalize()} {item_id} still used by {usage_count} pages, keeping in database")
        else:
            # For types without usage count method, try to load and delete if possible
            if media_type == "image":
                from hh.image.image_registry import get_image
                image_obj = get_image(item_id)
                if image_obj:
                    usage_count = image_obj.get_usage_count() if hasattr(image_obj, 'get_usage_count') else 1
                    if usage_count == 0 and hasattr(image_obj, 'delete_from_database'):
                        if not image_obj.delete_from_database():
                            warn(f"Failed to delete unused {media_type} {item_id}")
                            report_error("action", f"Failed to delete unused {media_type} {item_id}")

    if not is_error():
        log(f"Successfully removed {media_type} {item_id} (rank {item_rank}) from page {page.id}")
        page.flag_page_modification(f"{media_type}s updated")
        # Flag related item if method exists
        flag_method = get_flag_related_method(page, media_type)
        if flag_method:
            flag_method(item_id, f"removed from page {page.id}")

    trace_out()
    return not is_error()