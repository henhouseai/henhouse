"""Get page section action - returns HTML for a specific page section."""

from __future__ import annotations

from typing import Any, Dict

from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway, trace_in, trace_out, log, warn
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.page.page_registry import get_page
from hh.render.html.tiles import render_image_tile_link
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)


@register_action("get_page_section")
@register_command("get_page_section")
def get_page_section_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        page_id_arg = gateway.get_arg("id")
        if not page_id_arg:
            warn("Page ID is required")
            report_error("action", "Page ID is required")
            trace_out()
            return False

        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
            trace_out()
            return False

        section = gateway.get_arg("section")
        if not section:
            warn("Section is required")
            report_error("action", "Section is required")
            trace_out()
            return False

        if section not in ["images", "children", "files"]:
            warn(f"Invalid section: {section}")
            report_error("action", f"Invalid section: {section}")
            trace_out()
            return False

        # Load page
        page = get_page(page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
            trace_out()
            return False

        # Determine view_type
        view_type = gateway.get_arg("view_type")
        if not view_type:
            # Default: HTTP backend = tile for images, parser = table
            if gateway.backend == "http" and section == "images":
                view_type = "tile"
            else:
                view_type = "table"

        # Check URL override flag
        if gateway.request.is_set("image_table") and section == "images":
            view_type = "table"

        # Render section based on type
        dom_content = ""
        if section == "images":
            images_data = page.get_images_data()
            if view_type == "tile":
                # Render as tiles
                page_id_str = str(page_id)
                header_id = f"pageImageGroupHeader_{page_id_str}"
                content_id = f"pageImageGroup_{page_id_str}"
                
                header_html = f'<div id="{header_id}" class="contentHeader">IMAGES</div>'
                content_html = f'<div id="{content_id}" class="content pageImageGroup"><ul>'
                
                for image in images_data:
                    tile_html = render_image_tile_link(image, target_width=300)
                    content_html += f"<li>{tile_html}</li>"
                
                content_html += "</ul></div><div class=\"clearboth\"></div>"
                dom_content = header_html + content_html
            else:
                # Render as table (for parser backend testing)
                dom_content = "<table><tr><th>Rank</th><th>ID</th><th>Caption</th></tr>"
                for image in images_data:
                    image_id = image.get("id", "N/A")
                    rank = image.get("image_rank", "N/A")
                    caption = image.get("caption", "untitled")
                    dom_content += f"<tr><td>{rank}</td><td>{image_id}</td><td>{caption}</td></tr>"
                dom_content += "</table>"
        else:
            warn(f"Section {section} not yet implemented")
            report_error("action", f"Section {section} not yet implemented")
            trace_out()
            return False

        # Get page metadata
        page_data = page.get_page_data()
        payload = {
            "page_id": page_data.get("id"),
            "page_name": page_data.get("name"),
            "parent": page_data.get("parent"),
            "class": page_data.get("class"),
            "section": section,
            "view_type": view_type,
            "dom_content": dom_content,
        }
        gateway.response.set_action_response(success_payload(payload))
        log(f"Generated {section} section for page {page_id} in {view_type} mode")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to get page section: {exc}")
        report_error("action", f"Failed to get page section: {exc}")
        trace_out()
        return False


@register_parser("get_page_section")
def get_page_section_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        source_data = get_data(gateway.response.get_action_response())
        page_id = source_data.get("page_id")
        page_name = source_data.get("page_name")
        parent = source_data.get("parent")
        page_class = source_data.get("class")
        section = source_data.get("section")
        view_type = source_data.get("view_type")
        dom_content = source_data.get("dom_content", "")

        lines = [render_header_block("l_get_page_section_header")]

        table = TableData()
        table.add_row("get_page_section_header", info="")

        table.add_row("page_id", info=str(page_id) if page_id is not None else "N/A")
        table.add_row("page_name", info=str(page_name) if page_name else "N/A")
        table.add_row("page_parent", info=str(parent) if parent is not None else "N/A")
        table.add_row("page_class", info=str(page_class) if page_class else "N/A")
        table.add_row("section", info=str(section) if section else "N/A")
        table.add_row("view_type", info=str(view_type) if view_type else "N/A")
        table.add_row("dom_content", info=dom_content)

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("get_page_section_header")
                .add_simple(
                    [
                        "page_id",
                        "page_name",
                        "page_parent",
                        "page_class",
                        "section",
                        "view_type",
                        "dom_content",
                    ]
                ),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False

