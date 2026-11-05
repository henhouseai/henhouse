"""
Data Operations for Page Class

This module contains all data retrieval operations that were extracted from the Page class
to reduce its size and improve maintainability.

Functions in this module operate on a Page instance passed as the first parameter.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn
from hh.gateway.error.error_store import is_error
from hh.deploy.deploy_utils import is_module_active
from hh_page.page_registry import get_page as get_page_from_registry
from hh.tp.tp import TextProcessor

if TYPE_CHECKING:
    from hh_page.page import Page

trace_in = get_trace_in()
trace_out = get_trace_out()
log = get_log()
debug = get_debug()
warn = get_warn()


def get_page_data(page: 'Page') -> Dict[str, Any]:
    """Get basic page data as a dictionary."""
    trace_in()
    data: Dict[str, Any] = {
        "id": page.id,
        "name": page.name,
        "link": page.link,
        "parent": page.parent,
        "class": page.class_name,
        "visibility": page.visibility,
        "text": page.text,
        "last_modified": page.last_modified.isoformat() if page.last_modified else None,
        "username": page.username,
        "comments": page.comments
    }
    # Add breadcrumb path if available
    path_data = get_path(page)
    if path_data:
        data['path'] = path_data
    trace_out()
    return data


def assemble_page_data(page: 'Page') -> Dict[str, Any]:
    """Assemble a minimal JSON-friendly payload for AJAX consumption."""
    trace_in()
    page_data = page.get_page_data()
    images_data = get_images_data(page)
    files_data = get_files_data(page)
    audios_data = get_audios_data(page)
    videos_data = get_videos_data(page)
    children_by_class = page._get_children_by_class()
    upper_content = page._add_upper_content()
    lower_content = page._add_lower_content()
    metadata = page._get_metadata_dict()

    # Add path data if available
    if 'path' not in page_data:
        path_data = get_path(page)
        if path_data:
            page_data['path'] = path_data

    result: Dict[str, Any] = {
        'page': page_data,
        'images': images_data,
        'files': files_data,
        'audio': audios_data,
        'video': videos_data,
        'children_by_class': children_by_class,
        'upper_content': upper_content,
        'lower_content': lower_content,
        'metadata': metadata,
    }

    trace_out()
    return result


def get_prepared_text(page: 'Page') -> Optional[List[Dict[str, Any]]]:
    """
    Get the prepared text for this page. Checks cached prepared_text first, then processes if needed.
    """
    trace_in()
    # Check if field is already populated
    if hasattr(page, 'prepared_text') and page.prepared_text is not None:
        trace_out()
        return page.prepared_text
    # Field is empty, need to process text
    processor = TextProcessor()
    prepared = processor.preprocess(page.text or "")
    if prepared is not None:
        page.prepared_text = prepared
        # Only flag cache refresh if we actually processed text content
        # If we just confirmed there's no text (empty list), no need to refresh
        if prepared:
            page._flag_cache_refresh()
    trace_out()
    return prepared


def get_files_data(page: 'Page', rebuild: bool = False) -> List[Dict[str, Any]]:
    """Get files data for this page, with optional rebuild."""
    trace_in()
    # If rebuild flag is set, clear the cache to force a rebuild
    if rebuild:
        page.files = []
    # Check if field is already populated
    if hasattr(page, 'files') and page.files:
        trace_out()
        return page.files
    # Field is empty, need to hydrate from database
    files: List[Dict[str, Any]] = []
    if not is_error() and is_module_active('hh_file'):
        rows = page.gateway.conn.read(
            """
            SELECT fg.file_rank,
                   f.id,
                   f.file_name,
                   f.file_path,
                   f.description,
                   f.mime_type,
                   f.size_bytes,
                   f.username,
                   f.uploaded,
                   f.last_modified,
                   f.comments,
                   f.visibility
            FROM file_groups fg
            JOIN files f ON f.id = fg.file_id
            WHERE fg.page_id = %s
            ORDER BY fg.file_rank
            """,
            [page.id],
        )
        for row in rows:
            files.append(
                {
                    "id": row["id"],
                    "file_rank": row["file_rank"],
                    "file_name": row["file_name"],
                    "file_path": row["file_path"],
                    "description": row["description"],
                    "mime_type": row["mime_type"],
                    "size_bytes": row["size_bytes"],
                    "username": row["username"],
                    "uploaded": row["uploaded"],
                    "last_modified": row["last_modified"],
                    "comments": row["comments"],
                    "visibility": row["visibility"],
                }
            )
    page.files = files
    # Only flag cache refresh if we actually found files (data changed)
    # If we just confirmed there are no files (empty array), no need to refresh
    if files:
        page._flag_cache_refresh()
    trace_out()
    return files


def get_images_data(page: 'Page', rebuild: bool = False) -> List[Dict[str, Any]]:
    """Get images data for this page, with optional rebuild."""
    trace_in()
    # If rebuild flag is set, clear the cache to force a rebuild
    if rebuild:
        page.images = []
    # Check if field is already populated
    if hasattr(page, 'images') and page.images:
        log(f"Page {page.id}: returning cached images")
        trace_out()
        return page.images
    # Field is empty, need to hydrate from database
    images_data = []
    if not is_error() and is_module_active('hh_image'):
        try:
            from hh_image.image_registry import get_image
            results = page.gateway.conn.read("""
                SELECT i.id, ig.image_rank
                FROM image_groups ig
                JOIN images i ON ig.image_id = i.id
                WHERE ig.page_id = %s
                ORDER BY ig.image_rank
            """, [page.id])
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
            log(f"Loaded {len(images_data)} images for page {page.id}")
        except Exception as e:
            warn(f"Failed to load images for page {page.id}: {str(e)}")
            from hh.gateway.error.error_store import report_error
            report_error("backend", f"Failed to load images: {str(e)}")
    page.images = images_data
    # Only flag cache refresh if we actually found images (data changed)
    if images_data:  # Only flag if actual images were loaded
        page._flag_cache_refresh()
    trace_out()
    return images_data


def get_audios_data(page: 'Page', rebuild: bool = False) -> List[Dict[str, Any]]:
    """Get audios data for this page, with optional rebuild."""
    trace_in()
    # If rebuild flag is set, clear the cache to force a rebuild
    if rebuild:
        page.audios = []
    # Check if field is already populated
    if hasattr(page, 'audios') and page.audios:
        log(f"Page {page.id}: returning cached audios")
        trace_out()
        return page.audios
    # Field is empty, need to hydrate from database
    audio_data = []
    if not is_error() and is_module_active('hh_audio'):
        try:
            from hh_audio.audio_registry import get_audio
            results = page.gateway.conn.read("""
                SELECT a.id, ag.audio_rank
                FROM audio_groups ag
                JOIN audio a ON ag.audio_id = a.id
                WHERE ag.page_id = %s
                ORDER BY ag.audio_rank
            """, [page.id])
            for row in results:
                audio_id = row['id']
                audio_rank = row['audio_rank']
                audio = get_audio(audio_id)
                if audio:
                    # Ensure instances are fully loaded before getting audio_data
                    audio.get_instances()
                    audio_data_item = audio.get_audio_data()
                    audio_data_item['audio_rank'] = audio_rank  # Add rank from audio_groups
                    audio_data.append(audio_data_item)
                    log(f"Loaded audio {audio_id} (rank {audio_rank}): {audio_data_item.get('caption', 'untitled')}")
                else:
                    warn(f"Failed to load audio {audio_id}")
            log(f"Loaded {len(audio_data)} audio for page {page.id}")
        except Exception as e:
            warn(f"Failed to load audio for page {page.id}: {str(e)}")
            from hh.gateway.error.error_store import report_error
            report_error("backend", f"Failed to load audios: {str(e)}")
    page.audios = audio_data
    # Only flag cache refresh if we actually found audios (data changed)
    if audio_data:  # Only flag if actual audios were loaded
        page._flag_cache_refresh()
    trace_out()
    return audio_data


def get_videos_data(page: 'Page', rebuild: bool = False) -> List[Dict[str, Any]]:
    """Get videos data for this page, with optional rebuild."""
    trace_in()
    # If rebuild flag is set, clear the cache to force a rebuild
    if rebuild:
        page.videos = []
    # Check if field is already populated
    if hasattr(page, 'videos') and page.videos:
        log(f"Page {page.id}: returning cached videos")
        trace_out()
        return page.videos
    # Field is empty, need to hydrate from database
    video_data = []
    if not is_error() and is_module_active('hh_video'):
        try:
            from hh_video.video_registry import get_video
            results = page.gateway.conn.read("""
                SELECT v.id, vg.video_rank
                FROM video_groups vg
                JOIN video v ON vg.video_id = v.id
                WHERE vg.page_id = %s
                ORDER BY vg.video_rank
            """, [page.id])
            for row in results:
                video_id = row['id']
                video_rank = row['video_rank']
                video = get_video(video_id)
                if video:
                    # Ensure instances are fully loaded before getting video_data
                    video.get_instances()
                    video_data_item = video.get_video_data()
                    video_data_item['video_rank'] = video_rank  # Add rank from video_groups
                    video_data.append(video_data_item)
                    log(f"Loaded video {video_id} (rank {video_rank}): {video_data_item.get('caption', 'untitled')}")
                else:
                    warn(f"Failed to load video {video_id}")
            log(f"Loaded {len(video_data)} video for page {page.id}")
        except Exception as e:
            warn(f"Failed to load video for page {page.id}: {str(e)}")
            from hh.gateway.error.error_store import report_error
            report_error("backend", f"Failed to load videos: {str(e)}")
    page.videos = video_data
    # Only flag cache refresh if we actually found videos (data changed)
    if video_data:  # Only flag if actual videos were loaded
        page._flag_cache_refresh()
    trace_out()
    return video_data


def get_children_data(page: 'Page') -> List[Dict[str, Any]]:
    """Get children data for this page."""
    trace_in()
    children_data = []
    if not is_error():
        child_ids = page._get_child_page_ids()
    if not is_error():
        for i, child_id in enumerate(child_ids):
            if not is_error():
                child_page = get_page_from_registry(page_id=child_id)
                if child_page:
                    child_data = child_page.get_page_data()
                    # Add child count for this child page
                    child_count = child_page.get_child_count()
                    child_data['num_children'] = child_count
                    children_data.append(child_data)
                else:
                    warn(f"Failed to load child page {child_id}")
    log(f"Loaded {len(children_data)}/{len(child_ids)} child pages for page {page.id}: {[c['name'] for c in children_data]}")
    trace_out()
    return children_data


def get_path(page: 'Page') -> List[Dict[str, Any]]:
    """Get breadcrumb path for this page."""
    trace_in()
    path = []
    current_page = page
    level = 0
    while current_page and current_page.parent != 0:
        level += 1
        path.append({
            "id": current_page.id,
            "name": current_page._get_display_name(),
            "class": current_page.class_name
        })
        # Get parent page
        if current_page.parent is None:
            break
        parent_page = get_page_from_registry(page_id=current_page.parent)
        if not parent_page:
            warn(f"Parent page {current_page.parent} not found for page {current_page.id}")
            break
        current_page = parent_page
    # Add root page (parent = 0)
    if current_page:
        level += 1
        path.append({
            "id": current_page.id,
            "name": current_page._get_display_name(),
            "class": current_page.class_name
        })
    # Reverse to get root -> current order
    path.reverse()
    log(f"Built path for page {page.id}: {len(path)} levels -> {[p['name'] for p in path]}")
    trace_out()
    return path


def show_page(page: 'Page') -> Dict[str, Any]:
    """Assemble complete page data for display."""
    trace_in()
    cache_ready = getattr(page, 'cache_hydrated', False) and page.children_by_class is not None
    if cache_ready:
        log(f"Page {page.id}: cache available, methods will check cache independently")
    else:
        log(f"Page {page.id}: cache miss or stale entry; rebuilding show_page payload")

    # Check if page is stale based on timestamps alone - flag for refresh regardless of derived data
    if (page.cache_built_at is None) or (page.cache_built_at and page.last_modified and page.cache_built_at < page.last_modified):
        log(f"Page {page.id}: timestamps indicate stale cache (cache_built_at={page.cache_built_at}, last_modified={page.last_modified}), flagging for refresh")
        page._flag_cache_refresh()

    page_data = page.get_page_data()
    images_data = get_images_data(page)
    files_data = get_files_data(page)
    audios_data = get_audios_data(page)
    videos_data = get_videos_data(page)
    children_by_class = page._get_children_by_class()
    badge_headers = page._add_badge_headers()
    upper_content = page._add_upper_content()
    lower_content = page._add_lower_content()

    prepared_payload = get_prepared_text(page)
    if prepared_payload is not None:
        page_data = dict(page_data)
        page_data['prepared_text'] = prepared_payload

    response_data = {
        "page": page_data,
        "children_by_class": children_by_class,
        "images": images_data,
        "files": files_data,
        "audio": audios_data,
        "video": videos_data,
        "badge_headers": badge_headers,
        "upper_content": upper_content,
        "lower_content": lower_content,
    }

    # Add raw metadata for API consumers (not MCP agents who don't need it for CRUD)
    # MCP consumers get streamlined payloads, API consumers get full programmatic access
    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    if gateway and hasattr(gateway, 'backend') and gateway.backend == "api":
        response_data["metadata"] = page._get_metadata_dict()

    # Cache refresh will be handled by wrapper method system if flag is set

    total_children = sum(len(group['children']) for group in children_by_class.values())
    file_count = len(files_data)
    log(
        f"Assembled display data for page {page.id}: "
        f"{total_children} children in {len(children_by_class)} classes, "
        f"{len(images_data)} images, {file_count} files"
    )

    trace_out()
    return response_data