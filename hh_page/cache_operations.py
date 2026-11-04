"""
Cache Operations for Page Class

This module contains cache-related operations that were extracted from the Page class
to reduce its size and improve maintainability.

Functions in this module operate on a Page instance passed as the first parameter.
"""

import datetime as dt
from typing import TYPE_CHECKING

from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn
from hh.gateway.error.error_store import report_error, is_error

if TYPE_CHECKING:
    from hh_page.page import Page

trace_in = get_trace_in()
trace_out = get_trace_out()
log = get_log()
debug = get_debug()
warn = get_warn()


def refresh_cached_page(page: 'Page') -> bool:
    """
    Refresh the cache database with all 5 derived fields. Called by refresh_stale_page_caches() during gateway commit.

    Args:
        page: The Page instance to operate on

    Returns:
        bool: True if successful, False otherwise
    """
    trace_in()
    log(f"_refresh_cached_page: Starting for page {page.id}")

    tier_level = getattr(page.gateway.response, "user_tier_level", 0) if page.gateway and page.gateway.response else 0
    if tier_level < 3:
        log(
            f"_refresh_cached_page: Skipping cache write for page {page.id} (tier_level={tier_level})"
        )
        page._cache_needs_refresh = False
        trace_out()
        return True

    # Ensure all derived fields are populated by calling their internal mixin methods
    # The getters check if field is populated first, and only hydrate if empty
    # The getters set the attributes themselves, so we just call them
    # This ensures we always have fully hydrated data to cache

    if not page.display_name:
        page._get_display_name()

    if page.prepared_text is None:
        page.get_prepared_text()

    if not page.children_by_class:
        page._get_children_by_class()

    # Dynamically populate and cache all registered media types
    from hh.gateway.registry.media_registry import get_registered_media_types
    from hh_page import data_operations

    registered_media = get_registered_media_types()
    media_summary = {}

    # Process all known media types (programmatically generated)
    for media_type in ['image', 'file', 'audio', 'video']:
        # Only process if media module is registered
        if media_type in registered_media:
            # Generate attribute name programmatically: 'audio' -> 'audios'
            attribute = f'{media_type}s'
            # Generate getter function name: 'audio' -> 'get_audios_data'
            getter_name = f'get_{media_type}s_data'
            getter = getattr(data_operations, getter_name)

            # Ensure data is populated
            if not getattr(page, attribute, None):
                getter(page)

            # Add to media_summary
            data = getattr(page, attribute, None)
            if data:  # Only include if there's actual data
                media_summary[media_type] = data

    # Serialize all data
    display_name_str = page.display_name
    prepared_json = page._dump_json(page.prepared_text) if page.prepared_text is not None else None
    children_json = page._dump_json(page.children_by_class) if page.children_by_class else None
    media_summary_json = page._dump_json(media_summary) if media_summary else None

    # Get existing metadata (only the metadata JSON field, not main DB fields)
    # Main DB fields are now stored as first-class columns, not in metadata
    existing_metadata = getattr(page, 'metadata', {}) or {}
    if not isinstance(existing_metadata, dict):
        existing_metadata = {}
    metadata_json = page._dump_json(existing_metadata)

    now = dt.datetime.now()

    try:
        # Buffer cache database write with all main DB fields as first-class columns
        # plus derived fields and metadata (which now only contains custom metadata, not main DB fields)
        # Uses INSERT ... ON DUPLICATE KEY UPDATE to handle both insert and update cases
        page.gateway.conn.buffer_cache(
            "pages",
            """
                INSERT INTO pages (id, name, link, text, parent, class, last_modified, username, comments, visibility, displayStyle, viewCount, display_name, prepared_text, children_summary, media_summary, links_out, metadata, cache_built_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    link = VALUES(link),
                    text = VALUES(text),
                    parent = VALUES(parent),
                    class = VALUES(class),
                    last_modified = VALUES(last_modified),
                    username = VALUES(username),
                    comments = VALUES(comments),
                    visibility = VALUES(visibility),
                    displayStyle = VALUES(displayStyle),
                    viewCount = VALUES(viewCount),
                    display_name = VALUES(display_name),
                    prepared_text = VALUES(prepared_text),
                    children_summary = VALUES(children_summary),
                    media_summary = VALUES(media_summary),
                    links_out = VALUES(links_out),
                    metadata = VALUES(metadata),
                    cache_built_at = VALUES(cache_built_at)
            """,
            (
                page.id,
                page.name,
                page.link,
                page.text,
                page.parent,
                page.class_name,
                page.last_modified,
                page.username,
                page.comments,
                page.visibility,
                getattr(page, 'displayStyle', 1),
                getattr(page, 'viewCount', 0),
                display_name_str,
                prepared_json,
                children_json,
                media_summary_json,
                page._dump_json({}),  # links_out - currently not used, store empty dict
                metadata_json,
                now,
            ),
        )
        # Always bump main database cache_built_at
        page.gateway.conn.update(
            """
                UPDATE pages
                SET cache_built_at = %s
                WHERE id = %s
            """,
            (now, page.id),
        )

        # Note: Cache writes are buffered, so verification would fail until write_cache() is called
        # Verification removed since buffered writes aren't immediately visible in cache DB

        log(f"Refreshed cache for page {page.id}")
    except Exception as exc:
        warn(f"Failed to update cache for page {page.id}: {exc}")
        report_error("connection", f"Failed to update cache for page {page.id}")
        trace_out()
        return False

    page._cache_needs_refresh = False  # Reset flag after refresh

    trace_out()
    return not is_error()