"""Orphan checks module for maintenance daemon and manual runs."""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from hh.gateway.connection.connection import get_connection, load_dsn_pair, r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

ORPHAN_KEYS = {
    "orphan_pages": "Pages with missing parent pages",
    "orphan_link_sources": "Links whose source page is missing",
    "orphan_link_targets": "Links whose target page is missing",
    "orphan_image_pages": "Image links whose page is missing",
    "orphan_image_targets": "Image links whose image is missing",
    "orphan_image_group_pages": "Image groups pointing to missing pages",
    "orphan_image_group_images": "Image groups pointing to missing images",
    "orphan_file_group_pages": "File groups pointing to missing pages",
    "orphan_file_group_files": "File groups pointing to missing files",
}


@db_read
def check_orphans(conn) -> Dict[str, Any]:
    """Check for orphaned records across all tables.
    Returns a dictionary with counts and IDs of each type of orphan."""
    try:
        orphan_page_rows = r_query(
            conn,
            """
            SELECT child.id
            FROM pages child
            LEFT JOIN pages parent ON parent.id = child.parent
            WHERE child.parent <> 0 AND parent.id IS NULL
            ORDER BY child.id
            """,
        )
        orphan_pages = [row["id"] for row in orphan_page_rows]

        orphan_link_source_rows = r_query(
            conn,
            """
            SELECT l.id
            FROM links l
            LEFT JOIN pages p ON p.id = l.id
            WHERE p.id IS NULL
            ORDER BY l.id
            """,
        )
        orphan_link_sources = [row["id"] for row in orphan_link_source_rows]

        orphan_link_target_rows = r_query(
            conn,
            """
            SELECT l.resolution_id
            FROM links l
            LEFT JOIN pages p ON p.id = l.resolution_id
            WHERE p.id IS NULL
            ORDER BY l.resolution_id
            """,
        )
        orphan_link_targets = [row["resolution_id"] for row in orphan_link_target_rows]

        orphan_image_page_rows = r_query(
            conn,
            """
            SELECT il.id
            FROM image_links il
            LEFT JOIN pages p ON p.id = il.id
            WHERE p.id IS NULL
            ORDER BY il.id
            """,
        )
        orphan_image_pages = [row["id"] for row in orphan_image_page_rows]

        orphan_image_target_rows = r_query(
            conn,
            """
            SELECT il.resolution_id
            FROM image_links il
            LEFT JOIN images i ON i.id = il.resolution_id
            WHERE i.id IS NULL
            ORDER BY il.resolution_id
            """,
        )
        orphan_image_targets = [row["resolution_id"] for row in orphan_image_target_rows]

        # Check image_groups for missing pages or images
        orphan_image_group_pages = r_query(
            conn,
            """
            SELECT DISTINCT ig.page_id
            FROM image_groups ig
            LEFT JOIN pages p ON p.id = ig.page_id
            WHERE p.id IS NULL
            ORDER BY ig.page_id
            """,
        )
        orphan_image_group_page_ids = [row["page_id"] for row in orphan_image_group_pages]

        orphan_image_group_images = r_query(
            conn,
            """
            SELECT DISTINCT ig.image_id
            FROM image_groups ig
            LEFT JOIN images i ON i.id = ig.image_id
            WHERE i.id IS NULL
            ORDER BY ig.image_id
            """,
        )
        orphan_image_group_image_ids = [row["image_id"] for row in orphan_image_group_images]

        # Check file_groups for missing pages or files
        orphan_file_group_pages = r_query(
            conn,
            """
            SELECT DISTINCT fg.page_id
            FROM file_groups fg
            LEFT JOIN pages p ON p.id = fg.page_id
            WHERE p.id IS NULL
            ORDER BY fg.page_id
            """,
        )
        orphan_file_group_page_ids = [row["page_id"] for row in orphan_file_group_pages]

        orphan_file_group_files = r_query(
            conn,
            """
            SELECT DISTINCT fg.file_id
            FROM file_groups fg
            LEFT JOIN files f ON f.id = fg.file_id
            WHERE f.id IS NULL
            ORDER BY fg.file_id
            """,
        )
        orphan_file_group_file_ids = [row["file_id"] for row in orphan_file_group_files]

        return {
            "orphan_pages": orphan_pages,
            "orphan_link_sources": orphan_link_sources,
            "orphan_link_targets": orphan_link_targets,
            "orphan_image_pages": orphan_image_pages,
            "orphan_image_targets": orphan_image_targets,
            "orphan_image_group_pages": orphan_image_group_page_ids,
            "orphan_image_group_images": orphan_image_group_image_ids,
            "orphan_file_group_pages": orphan_file_group_page_ids,
            "orphan_file_group_files": orphan_file_group_file_ids,
        }
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to check orphan counts: %s", exc)
        return {}


def log_orphan_counts(conn) -> None:
    """Check and log orphan counts with IDs."""
    counts = check_orphans(conn)
    
    orphan_pages = counts.get("orphan_pages", [])
    orphan_link_sources = counts.get("orphan_link_sources", [])
    orphan_link_targets = counts.get("orphan_link_targets", [])
    orphan_image_pages = counts.get("orphan_image_pages", [])
    orphan_image_targets = counts.get("orphan_image_targets", [])
    orphan_image_group_pages = counts.get("orphan_image_group_pages", [])
    orphan_image_group_images = counts.get("orphan_image_group_images", [])
    orphan_file_group_pages = counts.get("orphan_file_group_pages", [])
    orphan_file_group_files = counts.get("orphan_file_group_files", [])

    if orphan_pages:
        page_ids = ",".join(str(p) for p in orphan_pages)
        logging.warning("Orphan pages detected (child missing parent): %s [IDs: %s]", len(orphan_pages), page_ids)
    if orphan_link_sources or orphan_link_targets:
        source_ids = ",".join(str(s) for s in orphan_link_sources) if orphan_link_sources else "none"
        target_ids = ",".join(str(t) for t in orphan_link_targets) if orphan_link_targets else "none"
        logging.warning(
            "Orphan links detected: source_missing=%s [IDs: %s] target_missing=%s [IDs: %s]",
            len(orphan_link_sources),
            source_ids,
            len(orphan_link_targets),
            target_ids,
        )
    if orphan_image_pages or orphan_image_targets:
        page_ids = ",".join(str(p) for p in orphan_image_pages) if orphan_image_pages else "none"
        image_ids = ",".join(str(i) for i in orphan_image_targets) if orphan_image_targets else "none"
        logging.warning(
            "Orphan image links detected: page_missing=%s [IDs: %s] image_missing=%s [IDs: %s]",
            len(orphan_image_pages),
            page_ids,
            len(orphan_image_targets),
            image_ids,
        )
    if orphan_image_group_pages or orphan_image_group_images:
        page_ids = ",".join(str(p) for p in orphan_image_group_pages) if orphan_image_group_pages else "none"
        image_ids = ",".join(str(i) for i in orphan_image_group_images) if orphan_image_group_images else "none"
        logging.warning(
            "Orphan image_groups detected: page_missing=%s [IDs: %s] image_missing=%s [IDs: %s]",
            len(orphan_image_group_pages),
            page_ids,
            len(orphan_image_group_images),
            image_ids,
        )
    if orphan_file_group_pages or orphan_file_group_files:
        page_ids = ",".join(str(p) for p in orphan_file_group_pages) if orphan_file_group_pages else "none"
        file_ids = ",".join(str(f) for f in orphan_file_group_files) if orphan_file_group_files else "none"
        logging.warning(
            "Orphan file_groups detected: page_missing=%s [IDs: %s] file_missing=%s [IDs: %s]",
            len(orphan_file_group_pages),
            page_ids,
            len(orphan_file_group_files),
            file_ids,
        )


def _validate_target(target: str | None) -> Tuple[str | None, Dict[str, str]]:
    if not target:
        return None, ORPHAN_KEYS
    normalized = target.strip().lower().replace("-", "_")
    for key in ORPHAN_KEYS:
        if normalized == key.lower():
            return key, {key: ORPHAN_KEYS[key]}
    raise ValueError(
        f"Unknown orphan target '{target}'. Choose from: {', '.join(sorted(ORPHAN_KEYS))}"
    )


def _perform_orphan_check(target: str | None = None) -> Dict[str, Any]:
    primary_dsn, _ = load_dsn_pair()
    if not primary_dsn:
        raise RuntimeError("Primary DSN missing; cannot run orphan check")
    conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
    try:
        counts = check_orphans(conn)
    finally:
        conn.close()
    selected_key, labels = _validate_target(target)
    if selected_key:
        filtered_counts = {selected_key: counts.get(selected_key, [])}
    else:
        filtered_counts = {key: counts.get(key, []) for key in labels}
    summary = {key: len(ids) for key, ids in filtered_counts.items()}
    return {
        "counts": filtered_counts,
        "summary": summary,
        "labels": labels,
    }


@register_action("orphan_check")
@register_command("orphan_check")
def orphan_check_action() -> bool:
    gateway = get_gateway()
    if not gateway:
        report_error("backend", "No gateway available")
        return False

    target = gateway.get_arg("target") or gateway.get_arg("type") or ""
    try:
        result = _perform_orphan_check(target or None)
    except ValueError as exc:
        report_error("request", str(exc))
        return False
    except Exception as exc:  # noqa: BLE001
        report_error("backend", f"Failed to run orphan check: {exc}")
        return False

    payload = {
        "operation": "orphan_check",
        "target": target or "all",
        "summary": result["summary"],
        "counts": result["counts"],
        "labels": result["labels"],
    }
    gateway.response.set_action_response(success_payload(payload))
    return not is_error()


@register_parser("orphan_check")
def orphan_check_parser() -> bool:
    gateway = get_gateway()
    if not gateway:
        report_error("backend", "No gateway available")
        return False
    if not gateway.response.has_action_response():
        report_error("backend", "No action response available")
        return False

    source_data = get_data(gateway.response.get_action_response())
    summary = source_data.get("summary", {})
    counts = source_data.get("counts", {})
    labels = source_data.get("labels", ORPHAN_KEYS)

    lines = [render_header_block("l_orphan_check_header")]

    table = TableData()
    for key in labels.keys():
        preview_ids = counts.get(key, [])[:20]
        preview = ", ".join(str(val) for val in preview_ids) if preview_ids else "none"
        table.add_row(
            key,
            status=f"{summary.get(key, 0)} issues",
            details=f"Sample IDs: {preview}",
        )

    lines.append(
        render_block(
            table,
            FieldConfig()
            .add_header("orphan_check_header")
            .add_simple(list(labels.keys())),
            block_type="maintenance",
            table_overrides={"margin_l": 4},
        )
    )

    gateway.response.add_output(finalize_output(lines))
    return True


register_maintenance_tool("orphan_check")

