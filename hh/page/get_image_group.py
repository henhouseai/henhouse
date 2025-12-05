"""Get image group action - returns JSON data for all images in a page's image group."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway, trace_in, trace_out, log, warn
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.page.page_registry import get_page
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)


@register_action("get_image_group")
@register_command("get_image_group")
def get_image_group_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        # Accept both 'id' and 'page_id' parameters
        page_id_arg = gateway.get_arg("id") or gateway.get_arg("page_id")
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

        # Load page
        page = get_page(page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
            trace_out()
            return False

        # Get images data
        images_data = page.get_images_data()
        
        # Transform to viewer format
        images = []
        for image_data in images_data:
            image_id = image_data.get('id')
            if image_id is None:
                continue
            
            # Get instances and transform to viewer format
            instances = image_data.get('instances', [])
            viewer_instances = []
            for instance in instances:
                viewer_instances.append({
                    'width': instance.get('width', 0),
                    'height': instance.get('height', 0),
                    'filesize': instance.get('filesize', 0),
                    'src': instance.get('src', '')
                })
            
            # Sort instances by width (ascending) - smallest first
            viewer_instances.sort(key=lambda x: x['width'])
            
            images.append({
                'id': image_id,
                'caption': image_data.get('caption', 'untitled'),
                'visibility': image_data.get('visibility', 1),
                'viewCount': image_data.get('view_count', 0),
                'instances': viewer_instances
            })

        payload = {
            "page_id": page_id,
            "images": images
        }
        gateway.response.set_action_response(success_payload(payload))
        log(f"Generated image group data for page {page_id} with {len(images)} images")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to get image group: {exc}")
        report_error("action", f"Failed to get image group: {exc}")
        trace_out()
        return False


@register_parser("get_image_group")
def get_image_group_parser() -> bool:
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
        images = source_data.get("images", [])

        lines = [render_header_block("l_get_image_group_header")]

        table = TableData()
        table.add_row("get_image_group_header", info="")

        table.add_row("page_id", info=str(page_id) if page_id is not None else "N/A")
        table.add_row("num_images", info=str(len(images)))
        
        # Dump the full JSON structure
        json_output = json.dumps(source_data, indent=2, ensure_ascii=False)
        table.add_row("json_data", info=json_output)

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("get_image_group_header")
                .add_simple(["page_id", "num_images", "json_data"]),
                block_type="maintenance",
                table_overrides={"margin_l": 4}
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

