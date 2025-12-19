"""Get page section action - returns HTML for a specific page section."""

from __future__ import annotations

from typing import Any, Dict, Mapping, cast

from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway, trace_in, trace_out, log, warn
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.page.page_registry import get_page
from hh.render.html.image_group import ImageGroup
from hh.render.html.page_group import PageGroup
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

        if section not in ["images", "children", "files", "audio", "video"]:
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
            # Default: HTTP backend = tile for images/children, parser = table
            # Audio and video always use table view
            if gateway.backend == "http" and section in ["images", "children"]:
                view_type = "tile"
            else:
                view_type = "table"

        # Check for overlay flag
        overlay_mode = gateway.is_set('overlay') if gateway else False
        wrapper_id_prefix = 'overlay_' if overlay_mode else ''
        wrapper_extra_classes = 'overlay' if overlay_mode else None

        # Render section based on type
        dom_content = ""
        if section == "images":
            images_data = page.get_images_data()
            if view_type == "tile":
                # Render as tiles (no headers for get_page_section - only content)
                page_id_str = str(page_id)
                content_id = f"{wrapper_id_prefix}pageImageGroup_{page_id_str}"
                image_group = ImageGroup(images_data, page_id, target_width=300, 
                                        wrapper_id=content_id, wrapper_extra_classes=wrapper_extra_classes)
                dom_content = image_group.render()  # Returns HTML string (includes wrapper divs)
            else:
                # Render as table (shouldn't happen for MCP, but handle it)
                from hh.render.render import FieldConfig, TableData, render_block
                from hh.render.config.config import safe_str
                images_rows = TableData()
                images_rows.add_row(
                    'images_header',
                    label='Images',
                    rank='Rank',
                    id='ID',
                    caption='Caption',
                    uploaded='Uploaded',
                    instances='Instances'
                )
                for image in images_data:
                    image_id = image.get('id')
                    instances_count = len(image.get('instances', []))
                    images_rows.add_row(
                        'image_item',
                        rank=str(image.get('image_rank', 'N/A')),
                        id=str(image_id) if image_id is not None else 'N/A',
                        caption=safe_str(image.get('caption', 'untitled')),
                        uploaded=safe_str(image.get('uploaded', 'N/A')),
                        instances=str(instances_count)
                    )
                    if image_id is not None:
                        images_rows.add_image_link_to_column('label', image_id)
                        images_rows.add_image_link_to_column('rank', image_id)
                        images_rows.add_image_link_to_column('id', image_id)
                        images_rows.add_image_link_to_column('caption', image_id)
                
                if images_rows.num_rows() > 0:
                    page_id_str = str(page_id)
                    content_id = f"{wrapper_id_prefix}pageImageGroup_{page_id_str}"
                    # Render block with wrapper configuration
                    dom_content = render_block(
                        images_rows,
                        FieldConfig()
                            .add_header('images_header')
                            .add_simple(['image_item']),
                        table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},  # type: ignore[dict-item]
                        block_type='images',
                        backend='http',  # Force HTTP for MCP
                        wrapper_id=content_id,
                        wrapper_extra_classes=wrapper_extra_classes
                    )
        elif section == "children":
            # Get class_name parameter (required for children section)
            class_name = gateway.get_arg("class_name")
            if not class_name:
                warn("class_name is required for children section")
                report_error("action", "class_name is required for children section")
                trace_out()
                return False
            
            # Get children data with requested view_type using static getChildrenOf method
            from hh.page.page_class_registry import get_page_class
            PageClass = get_page_class(class_name)
            if PageClass:
                children_data = PageClass.getChildrenOf(page.id, view_type=view_type)
            else:
                warn(f"Page class '{class_name}' not found")
                report_error("action", f"Page class '{class_name}' not found")
                children_data = []
            if children_data:
                if view_type == "tile":
                    # Render as tiles (no headers for get_page_section - only content)
                    page_id_str = str(page_id)
                    class_name_safe = class_name.replace('_', '-')
                    content_id = f"{wrapper_id_prefix}child_pages_{class_name_safe}_{page_id_str}"
                    page_group = PageGroup(children_data, page_id, class_name, target_width=300,
                                          wrapper_id=content_id, wrapper_extra_classes=wrapper_extra_classes)
                    dom_content = page_group.render()  # Returns HTML string (includes wrapper divs)
                else:
                    # Render as table (shouldn't happen for MCP, but handle it)
                    from hh.render.render import FieldConfig, TableData, render_block
                    from hh.render.config.config import safe_str
                    # Get all field names dynamically from first child
                    first_child = children_data[0]
                    field_names = [k for k in first_child.keys() if not k.startswith('_') and k != 'field_type' and k != '_format']
                    
                    # Check if any child has children - if not, remove num_children column
                    if 'num_children' in field_names:
                        has_any_children = any(child.get('num_children', 0) > 0 for child in children_data)
                        if not has_any_children:
                            field_names.remove('num_children')
                    
                    # Create header row dynamically
                    children_rows = TableData()
                    header_kwargs = {}
                    for field_name in field_names:
                        header_kwargs[field_name] = field_name.replace('_', ' ').title()
                    children_rows.add_row('children_header', **header_kwargs)
                    
                    # Collect all unique field_types
                    field_types = set()
                    for child in children_data:
                        field_type = child.get('field_type', 'page')
                        field_types.add(field_type)
                    field_types_list = sorted(list(field_types))
                    
                    # Create data rows
                    for child in children_data:
                        child_id = child.get('id')
                        data_kwargs = {}
                        for field_name in field_names:
                            value = child.get(field_name)
                            if value is None:
                                data_kwargs[field_name] = 'N/A'
                            elif isinstance(value, str):
                                data_kwargs[field_name] = safe_str(value)
                            else:
                                data_kwargs[field_name] = str(value)
                        field_type = child.get('field_type', 'page')
                        children_rows.add_row(field_type, **data_kwargs)
                        
                        if child_id is not None and isinstance(child_id, int):
                            children_rows.add_page_link_to_column('label', child_id)
                            if len(field_names) > 0:
                                children_rows.add_page_link_to_column(field_names[0], child_id)
                            if len(field_names) > 1:
                                children_rows.add_page_link_to_column(field_names[1], child_id)
                    
                    if children_rows.num_rows() > 0:
                        page_id_str = str(page_id)
                        class_name_safe = class_name.replace('_', '-')
                        content_id = f"{wrapper_id_prefix}child_pages_{class_name_safe}_{page_id_str}"
                        # Render block with wrapper configuration
                        dom_content = render_block(
                            children_rows,
                            FieldConfig()
                                .add_header('children_header')
                                .add_simple(field_types_list),
                            table_overrides={'margin_l': 4},
                            block_type='children',
                            backend='http',  # Force HTTP for MCP
                            wrapper_id=content_id,
                            wrapper_extra_classes=wrapper_extra_classes
                        )
            else:
                warn(f"No children found for class '{class_name}'")
                dom_content = ""
        elif section == "files":
            # Files section - render as table
            files_data = page.get_files_data()
            if files_data:
                from hh.render.render import FieldConfig, TableData, render_block
                from hh.render.config.config import safe_str
                files_rows = TableData()
                files_rows.add_row(
                    'files_header',
                    label='Files',
                    rank='Rank',
                    id='ID',
                    name='Name',
                    description='Description',
                    uploaded='Uploaded',
                    size='Size',
                    path='Path',
                )
                for file_entry in files_data:
                    file_id = file_entry.get('id')
                    size_bytes = file_entry.get('size_bytes')
                    size_display = f"{size_bytes:,} B" if isinstance(size_bytes, int) else 'N/A'
                    file_path = file_entry.get('file_path') or ''
                    files_rows.add_row(
                        'file_item',
                        rank=str(file_entry.get('file_rank', 'N/A')),
                        id=str(file_id) if file_id is not None else 'N/A',
                        name=safe_str(file_entry.get('file_name', 'unnamed')),
                        description=safe_str(file_entry.get('description', '')),
                        uploaded=safe_str(file_entry.get('uploaded', 'N/A')),
                        size=size_display,
                        path=safe_str(file_path),
                    )
                    if file_id is not None:
                        files_rows.add_file_link_to_column('name', file_id)
                        files_rows.add_file_link_to_column('path', file_id)
                
                if files_rows.num_rows() > 0:
                    page_id_str = str(page_id)
                    content_id = f"{wrapper_id_prefix}pageFileGroup_{page_id_str}"
                    dom_content = render_block(
                        files_rows,
                        FieldConfig()
                            .add_header('files_header')
                            .add_simple(['file_item']),
                        table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},  # type: ignore[dict-item]
                        block_type='files',
                        backend='http',  # Force HTTP for MCP
                        wrapper_id=content_id,
                        wrapper_extra_classes=wrapper_extra_classes
                    )
        elif section == "audio":
            # Audio section - render as table
            audio_data = page.get_audio_data()
            if audio_data:
                from hh.render.render import FieldConfig, TableData, render_block
                from hh.render.config.config import safe_str
                audio_rows = TableData()
                audio_rows.add_row(
                    'audio_header',
                    label='Audio',
                    rank='Rank',
                    id='ID',
                    caption='Caption',
                    uploaded='Uploaded',
                    duration='Duration',
                    size='Size',
                    instances='Instances'
                )
                for audio_entry in audio_data:
                    audio_id = audio_entry.get('id')
                    max_filesize = audio_entry.get('max_filesize', 0)
                    size_display = f"{max_filesize:,} B" if isinstance(max_filesize, int) else 'N/A'
                    duration_seconds = audio_entry.get('duration_seconds')
                    duration_display = f"{duration_seconds:.1f}s" if duration_seconds is not None else 'N/A'
                    instances_count = len(audio_entry.get('instances', []))
                    audio_rows.add_row(
                        'audio_item',
                        rank=str(audio_entry.get('audio_rank', 'N/A')),
                        id=str(audio_id) if audio_id is not None else 'N/A',
                        caption=safe_str(audio_entry.get('caption', 'untitled')),
                        uploaded=safe_str(audio_entry.get('uploaded', 'N/A')),
                        duration=duration_display,
                        size=size_display,
                        instances=str(instances_count)
                    )
                    if audio_id is not None:
                        audio_rows.add_audio_link_to_column('label', audio_id)
                        audio_rows.add_audio_link_to_column('rank', audio_id)
                        audio_rows.add_audio_link_to_column('id', audio_id)
                        audio_rows.add_audio_link_to_column('caption', audio_id)
                
                if audio_rows.num_rows() > 0:
                    page_id_str = str(page_id)
                    content_id = f"{wrapper_id_prefix}pageAudioGroup_{page_id_str}"
                    dom_content = render_block(
                        audio_rows,
                        FieldConfig()
                            .add_header('audio_header')
                            .add_simple(['audio_item']),
                        table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},  # type: ignore[dict-item]
                        block_type='audio',
                        backend='http',  # Force HTTP for MCP
                        wrapper_id=content_id,
                        wrapper_extra_classes=wrapper_extra_classes
                    )
        elif section == "video":
            # Video section - render as table
            video_data = page.get_video_data()
            if video_data:
                from hh.render.render import FieldConfig, TableData, render_block
                from hh.render.config.config import safe_str
                video_rows = TableData()
                video_rows.add_row(
                    'video_header',
                    label='Video',
                    rank='Rank',
                    id='ID',
                    caption='Caption',
                    uploaded='Uploaded',
                    dimensions='Dimensions',
                    duration='Duration',
                    size='Size',
                    instances='Instances'
                )
                for video_entry in video_data:
                    video_id = video_entry.get('id')
                    max_filesize = video_entry.get('max_filesize', 0)
                    size_display = f"{max_filesize:,} B" if isinstance(max_filesize, int) else 'N/A'
                    width = video_entry.get('width')
                    height = video_entry.get('height')
                    dimensions_display = f"{width}x{height}" if width is not None and height is not None else 'N/A'
                    duration_seconds = video_entry.get('duration_seconds')
                    duration_display = f"{duration_seconds:.1f}s" if duration_seconds is not None else 'N/A'
                    instances_count = len(video_entry.get('instances', []))
                    video_rows.add_row(
                        'video_item',
                        rank=str(video_entry.get('video_rank', 'N/A')),
                        id=str(video_id) if video_id is not None else 'N/A',
                        caption=safe_str(video_entry.get('caption', 'untitled')),
                        uploaded=safe_str(video_entry.get('uploaded', 'N/A')),
                        dimensions=dimensions_display,
                        duration=duration_display,
                        size=size_display,
                        instances=str(instances_count)
                    )
                    if video_id is not None:
                        video_rows.add_video_link_to_column('label', video_id)
                        video_rows.add_video_link_to_column('rank', video_id)
                        video_rows.add_video_link_to_column('id', video_id)
                        video_rows.add_video_link_to_column('caption', video_id)
                
                if video_rows.num_rows() > 0:
                    page_id_str = str(page_id)
                    content_id = f"{wrapper_id_prefix}pageVideoGroup_{page_id_str}"
                    dom_content = render_block(
                        video_rows,
                        FieldConfig()
                            .add_header('video_header')
                            .add_simple(['video_item']),
                        table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},  # type: ignore[dict-item]
                        block_type='video',
                        backend='http',  # Force HTTP for MCP
                        wrapper_id=content_id,
                        wrapper_extra_classes=wrapper_extra_classes
                    )
        else:
            warn(f"Section {section} not yet implemented")
            report_error("action", f"Section {section} not yet implemented")
            trace_out()
            return False

        # Get page metadata
        page_data = page.get_page_data()
        payload: Dict[str, Any] = {
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

