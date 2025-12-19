"""Get audio group action - returns JSON data for all audio files in a page's audio group."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, cast

from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway, trace_in, trace_out, log, warn
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.page.page_registry import get_page
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)


@register_action("get_audio_group")
@register_command("get_audio_group")
def get_audio_group_action() -> bool:
    trace_in()
    gateway = get_gateway()

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

        # Get audio data
        audio_data = page.get_audio_data()
        
        # Transform to viewer format
        audio_files = []
        for audio_entry in audio_data:
            audio_id = audio_entry.get('id')
            if audio_id is None:
                continue
            
            # Get instances and transform to viewer format
            instances = audio_entry.get('instances', [])
            viewer_instances = []
            for instance in instances:
                viewer_instances.append({
                    'instance_type': instance.get('instance_type', 'full'),
                    'file_path': instance.get('file_path', ''),
                    'mime_type': instance.get('mime_type', ''),
                    'size_bytes': instance.get('size_bytes', 0),
                    'duration_seconds': instance.get('duration_seconds'),
                    'bitrate': instance.get('bitrate')
                })
            
            audio_files.append({
                'id': audio_id,
                'caption': audio_entry.get('caption', 'untitled'),
                'visibility': audio_entry.get('visibility', 1),
                'viewCount': audio_entry.get('view_count', 0),
                'uploaded': audio_entry.get('uploaded'),
                'mime_type': audio_entry.get('mime_type', 'N/A'),
                'duration_seconds': audio_entry.get('duration_seconds'),
                'bitrate': audio_entry.get('bitrate'),
                'instances': viewer_instances
            })

        payload = {
            "page_id": page_id,
            "audio": audio_files
        }
        gateway.response.set_action_response(success_payload(payload))
        log(f"Generated audio group data for page {page_id} with {len(audio_files)} audio files")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to get audio group: {exc}")
        report_error("action", f"Failed to get audio group: {exc}")
        trace_out()
        return False


@register_parser("get_audio_group")
def get_audio_group_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        action_response = gateway.response.get_action_response()
        if action_response is None:
            warn("Action response is None")
            report_error("backend", "Action response is None")
            trace_out()
            return False
        source_data = get_data(cast(Mapping[str, Any], action_response))
        page_id = source_data.get("page_id")
        audio_files = source_data.get("audio", [])

        lines = [render_header_block("l_get_audio_group_header")]

        table = TableData()
        table.add_row("get_audio_group_header", info="")

        table.add_row("page_id", info=str(page_id) if page_id is not None else "N/A")
        table.add_row("num_audio", info=str(len(audio_files)))
        
        # Dump the full JSON structure
        json_output = json.dumps(source_data, indent=2, ensure_ascii=False)
        table.add_row("json_data", info=json_output)

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("get_audio_group_header")
                .add_simple(["page_id", "num_audio", "json_data"]),
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
