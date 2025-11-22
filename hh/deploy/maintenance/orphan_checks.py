"""Orphan checks module for maintenance daemon."""

import logging
from typing import Any, Dict

from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read


@db_read
def check_orphans(conn) -> Dict[str, int]:
    """Check for orphaned records across all tables.
    Returns a dictionary with counts of each type of orphan."""
    try:
        orphan_pages = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM pages child
            LEFT JOIN pages parent ON parent.id = child.parent
            WHERE child.parent <> 0 AND parent.id IS NULL
            """,
        )[0]["cnt"]

        orphan_link_sources = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM links l
            LEFT JOIN pages p ON p.id = l.id
            WHERE p.id IS NULL
            """,
        )[0]["cnt"]

        orphan_link_targets = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM links l
            LEFT JOIN pages p ON p.id = l.resolution_id
            WHERE p.id IS NULL
            """,
        )[0]["cnt"]

        orphan_image_pages = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM image_links il
            LEFT JOIN pages p ON p.id = il.id
            WHERE p.id IS NULL
            """,
        )[0]["cnt"]

        orphan_image_targets = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM image_links il
            LEFT JOIN images i ON i.id = il.resolution_id
            WHERE i.id IS NULL
            """,
        )[0]["cnt"]

        return {
            "orphan_pages": orphan_pages,
            "orphan_link_sources": orphan_link_sources,
            "orphan_link_targets": orphan_link_targets,
            "orphan_image_pages": orphan_image_pages,
            "orphan_image_targets": orphan_image_targets,
        }
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to check orphan counts: %s", exc)
        return {}


def log_orphan_counts(conn) -> None:
    """Check and log orphan counts."""
    counts = check_orphans(conn)
    
    orphan_pages = counts.get("orphan_pages", 0)
    orphan_link_sources = counts.get("orphan_link_sources", 0)
    orphan_link_targets = counts.get("orphan_link_targets", 0)
    orphan_image_pages = counts.get("orphan_image_pages", 0)
    orphan_image_targets = counts.get("orphan_image_targets", 0)

    if orphan_pages:
        logging.warning("Orphan pages detected (child missing parent): %s", orphan_pages)
    if orphan_link_sources or orphan_link_targets:
        logging.warning(
            "Orphan links detected: source_missing=%s target_missing=%s",
            orphan_link_sources,
            orphan_link_targets,
        )
    if orphan_image_pages or orphan_image_targets:
        logging.warning(
            "Orphan image links detected: page_missing=%s image_missing=%s",
            orphan_image_pages,
            orphan_image_targets,
        )

