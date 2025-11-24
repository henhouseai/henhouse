"""Orphan checks module for maintenance daemon and manual runs."""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

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

def check_orphan_pages() -> list[int]:
    """Check for pages with missing parent pages."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT child.id
        FROM pages child
        LEFT JOIN pages parent ON parent.id = child.parent
        WHERE child.parent <> 0 AND parent.id IS NULL
        ORDER BY child.id
        """
    )
    return [row["id"] for row in rows]


def check_orphan_link_sources() -> list[int]:
    """Check for links whose source page is missing."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT l.id
        FROM links l
        LEFT JOIN pages p ON p.id = l.id
        WHERE p.id IS NULL
        ORDER BY l.id
        """
    )
    return [row["id"] for row in rows]


def check_orphan_link_targets() -> list[int]:
    """Check for links whose target page is missing."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT l.resolution_id
        FROM links l
        LEFT JOIN pages p ON p.id = l.resolution_id
        WHERE p.id IS NULL
        ORDER BY l.resolution_id
        """
    )
    return [row["resolution_id"] for row in rows]


def check_orphan_image_pages() -> list[int]:
    """Check for image links whose page is missing."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT il.id
        FROM image_links il
        LEFT JOIN pages p ON p.id = il.id
        WHERE p.id IS NULL
        ORDER BY il.id
        """
    )
    return [row["id"] for row in rows]


def check_orphan_image_targets() -> list[int]:
    """Check for image links whose image is missing."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT il.resolution_id
        FROM image_links il
        LEFT JOIN images i ON i.id = il.resolution_id
        WHERE i.id IS NULL
        ORDER BY il.resolution_id
        """
    )
    return [row["resolution_id"] for row in rows]


def check_orphan_image_group_pages() -> list[int]:
    """Check for image groups pointing to missing pages."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT DISTINCT ig.page_id
        FROM image_groups ig
        LEFT JOIN pages p ON p.id = ig.page_id
        WHERE p.id IS NULL
        ORDER BY ig.page_id
        """
    )
    return [row["page_id"] for row in rows]


def check_orphan_image_group_images() -> list[int]:
    """Check for image groups pointing to missing images."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT DISTINCT ig.image_id
        FROM image_groups ig
        LEFT JOIN images i ON i.id = ig.image_id
        WHERE i.id IS NULL
        ORDER BY ig.image_id
        """
    )
    return [row["image_id"] for row in rows]


def check_orphan_file_group_pages() -> list[int]:
    """Check for file groups pointing to missing pages."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT DISTINCT fg.page_id
        FROM file_groups fg
        LEFT JOIN pages p ON p.id = fg.page_id
        WHERE p.id IS NULL
        ORDER BY fg.page_id
        """
    )
    return [row["page_id"] for row in rows]


def check_orphan_file_group_files() -> list[int]:
    """Check for file groups pointing to missing files."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return []
    rows = gateway.conn.read(
        """
        SELECT DISTINCT fg.file_id
        FROM file_groups fg
        LEFT JOIN files f ON f.id = fg.file_id
        WHERE f.id IS NULL
        ORDER BY fg.file_id
        """
    )
    return [row["file_id"] for row in rows]


@register_action("orphan_check")
@register_command("orphan_check")
def orphan_check_action() -> bool:
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        report_error("action", "No gateway or connection available")
        return False

    try:
        counts = {
            "orphan_pages": check_orphan_pages(),
            "orphan_link_sources": check_orphan_link_sources(),
            "orphan_link_targets": check_orphan_link_targets(),
            "orphan_image_pages": check_orphan_image_pages(),
            "orphan_image_targets": check_orphan_image_targets(),
            "orphan_image_group_pages": check_orphan_image_group_pages(),
            "orphan_image_group_images": check_orphan_image_group_images(),
            "orphan_file_group_pages": check_orphan_file_group_pages(),
            "orphan_file_group_files": check_orphan_file_group_files(),
        }
        summary = {key: len(ids) for key, ids in counts.items()}
    except Exception as exc:  # noqa: BLE001
        report_error("action", f"Failed to run orphan check: {exc}")
        return False

    payload = {
        "operation": "orphan_check",
        "summary": summary,
        "counts": counts,
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

    lines = [render_header_block("l_orphan_check_header")]

    table = TableData()
    # Add header row
    total_count = sum(summary.get(key, 0) for key in counts.keys())
    table.add_row(
        "loaded",
        label=f"{total_count} orphan{'s' if total_count != 1 else ''}",
        count="Count",
        ids="IDs",
    )

    # Add data rows
    for key in counts.keys():
        count = summary.get(key, 0)
        ids_list = counts.get(key, [])
        preview_ids = ids_list[:20] if ids_list else []
        preview = ", ".join(str(val) for val in preview_ids) if preview_ids else ""
        
        table.add_row(
            key,
            count=str(count),
            ids=preview,
        )

    lines.append(
        render_block(
            table,
            FieldConfig()
            .add_header("header")
            .add_simple(["orphan_pages", "orphan_link_sources", "orphan_link_targets", "orphan_image_pages", "orphan_image_targets", "orphan_image_group_pages", "orphan_image_group_images", "orphan_file_group_pages", "orphan_file_group_files", "ids"]),
            block_type="maintenance",
            table_overrides={"margin_l": 4},
        )
    )

    gateway.response.add_output(finalize_output(lines))
    return True


register_maintenance_tool("orphan_check")

