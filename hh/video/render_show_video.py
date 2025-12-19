from __future__ import annotations
from typing import Dict, List, Any, Mapping, cast
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def render_usage_section(usage_data: List[Dict[str, Any]], lines: List[str]) -> None:
    trace_in()
    if not usage_data:
        log("No usage data available")
        trace_out()
        return
    log(f"Rendering usage section with {len(usage_data)} pages")
    
    usage_table = TableData()
    
    # Create header row
    usage_table.add_row(
        'video_usage_header',
        label='Pages Using This Video',
        page_id='Page ID',
        page_name='Page Name',
        usage_count='Count',
        rank_range='Rank'
    )
    
    # Create data rows for each page using this video
    for usage_item in usage_data:
        page_id_raw = usage_item.get('page_id')
        page_name = usage_item.get('page_name', 'Unknown')
        page_class = usage_item.get('page_class', 'page')
        usage_count = usage_item.get('usage_count', 0)
        ranks_str = usage_item.get('ranks', '')
        # Use the comma-separated ranks directly from the query
        rank_range = ranks_str if ranks_str else "N/A"
        
        usage_table.add_row(
            f'{page_class}_class',
            page_id=str(page_id_raw) if page_id_raw is not None else 'Unknown',
            page_name=safe_str(page_name),
            usage_count=str(usage_count),
            rank_range=rank_range
        )
        # Add page link metadata to label, page_id, and page_name columns
        if page_id_raw is not None:
            usage_table.add_page_link_to_column('label', page_id_raw)
            usage_table.add_page_link_to_column('page_id', page_id_raw)
            usage_table.add_page_link_to_column('page_name', page_id_raw)
    
    if usage_table.num_rows() > 0:
        lines.append(render_block(
            usage_table,
            FieldConfig()
                .add_header('video_usage_header')
                .add_simple(['page_class']),
            table_overrides={'margin_l': 4},
            block_type='usage'
        ))
        break_section(lines)
    trace_out()


def render_video_section(video_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway.is_no(block):
        log("Rendering video data section")
        
        # Get folder path from file_path (trim filename)
        file_path = video_data.get('file_path', 'N/A')
        if file_path and file_path != 'N/A':
            # Remove filename, keep just the folder path
            last_slash = file_path.rfind('/')
            if last_slash != -1:
                file_path = file_path[:last_slash + 1]
        
        video_summary = TableData()
        
        # Video ID
        video_id = video_data.get('id')
        if video_id:
            video_summary.add_row(
                'video_id',
                value=str(video_id)
            )
        
        # Caption
        caption = video_data.get('caption', 'untitled')
        video_summary.add_row(
            'video_caption',
            value=safe_str(caption)
        )
        
        # MIME Type
        mime_type = video_data.get('mime_type', 'N/A')
        video_summary.add_row(
            'video_mime_type',
            value=safe_str(mime_type)
        )
        
        # Max Filesize
        max_filesize = video_data.get('max_filesize', 0)
        video_summary.add_row(
            'video_max_filesize',
            value=str(max_filesize)
        )
        
        # Width (if available)
        width = video_data.get('width')
        if width is not None:
            video_summary.add_row(
                'video_width',
                value=str(width)
            )
        
        # Height (if available)
        height = video_data.get('height')
        if height is not None:
            video_summary.add_row(
                'video_height',
                value=str(height)
            )
        
        # Duration (if available)
        duration_seconds = video_data.get('duration_seconds')
        if duration_seconds is not None:
            video_summary.add_row(
                'video_duration_seconds',
                value=str(duration_seconds)
            )
        
        # Bitrate (if available)
        bitrate = video_data.get('bitrate')
        if bitrate is not None:
            video_summary.add_row(
                'video_bitrate',
                value=str(bitrate)
            )
        
        # Number of Instances
        num_instances = video_data.get('num_instances', 0)
        video_summary.add_row(
            'video_num_instances',
            value=str(num_instances)
        )
        
        # File Path
        video_summary.add_row(
            'video_file_path',
            value=safe_str(file_path)
        )
        
        # Uploaded Date
        uploaded = video_data.get('uploaded')
        if uploaded:
            video_summary.add_row(
                'video_uploaded',
                value=safe_str(uploaded)
            )
        
        lines.append(render_block(
            video_summary,
            FieldConfig()
                .add_header('show_video_header')
                .add_simple(['video_id', 'video_caption', 'video_mime_type', 'video_max_filesize', 'video_width', 'video_height', 'video_duration_seconds', 'video_bitrate', 'video_num_instances', 'video_file_path', 'video_uploaded']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_instances_section(instances_data: List[Dict[str, Any]], lines: List[str]) -> None:
    trace_in()
    block = 'instances'
    gateway = get_gateway()
    if not gateway.is_no(block) and instances_data:
        log(f"Rendering instances section with {len(instances_data)} instances")
        
        instances_table = TableData()
        
        # Create header row
        instances_table.add_row(
            'video_instances_header',
            label='Video Instances',
            instance_type='Type',
            mime_type='MIME Type',
            size_bytes='Size',
            width='Width',
            height='Height',
            duration_seconds='Duration',
            bitrate='Bitrate',
            filename='Filename'
        )
        
        # Create data rows for each instance
        for instance in instances_data:
            file_path = instance.get('file_path', '')
            instances_table.add_row(
                'video_instance_item',
                instance_type=str(instance.get('instance_type', 'full')),
                mime_type=safe_str(instance.get('mime_type', 'N/A')),
                size_bytes=str(instance.get('size_bytes', 0)),
                width=str(instance.get('width', 'N/A')) if instance.get('width') is not None else 'N/A',
                height=str(instance.get('height', 'N/A')) if instance.get('height') is not None else 'N/A',
                duration_seconds=str(instance.get('duration_seconds', 'N/A')) if instance.get('duration_seconds') is not None else 'N/A',
                bitrate=str(instance.get('bitrate', 'N/A')) if instance.get('bitrate') is not None else 'N/A',
                filename=safe_str(instance.get('filename', 'N/A'))
            )
            # Add video file link metadata to filename column
            if file_path:
                instances_table.add_image_file_link_to_column('filename', file_path)
        
        if instances_table.num_rows() > 0:
            lines.append(render_block(
                instances_table,
                FieldConfig()
                    .add_header('video_instances_header')
                    .add_simple(['video_instance_item']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()


def render_extra_data_section(extra_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    block = 'extra_data'
    gateway = get_gateway()
    if not gateway.is_no(block) and extra_data:
        log(f"Rendering extra data section with {len(extra_data)} items")
        
        # Determine header label from operation field if present
        header_label = 'Action Details'  # Default
        if 'operation' in extra_data:
            operation = extra_data['operation']
            # Convert operation name to title case
            header_label = operation.replace('_', ' ').title()
        
        # Create header row
        extra_rows = TableData()
        extra_rows.add_row(
            'extra_data_header',
            label=header_label,
            value=''
        )
        
        # Programmatically create field config based on what's in extra_data
        field_config = FieldConfig()
        field_config.add_header('extra_data_header')
        
        # Create data rows for each extra field
        row_types = []
        for key, value in extra_data.items():
            # Generate row type based on key
            row_type = f'extra_data_{key}'
            
            # Handle special cases for better display
            if isinstance(value, (list, dict)):
                value = str(value)
            elif value is None:
                value = "None"
            else:
                value = str(value)
            
            # Add row with just label and value (no key column)
            extra_rows.add_row(
                row_type,
                label='',  # Label will come from .ini file
                value=safe_str(value)
            )
            row_types.append(row_type)
        
        if extra_rows.num_rows() > 0:
            # Add all row types to field config
            field_config.add_simple(row_types)
            
            lines.append(render_block(
                extra_rows,
                field_config,
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()


@register_http('show_video')
@register_parser('show_video')
def show_video() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    action_response = gateway.response.get_action_response()
    if action_response is None:
        warn("Action response is None")
        report_error("backend", "Action response is None")
        trace_out()
        return False
    lines = []
    lines.append(render_header_block('l_show_video_header'))
    source_data = get_data(cast(Mapping[str, Any], action_response))
    log("Processing show video data successfully")
    # Render usage section first
    usage_data = source_data.get('usage', [])
    render_usage_section(usage_data, lines)
    # Render main video data section
    video_data = source_data.get('video', {})
    render_video_section(video_data, lines)
    # Render instances data section (if any)
    instances_data = source_data.get('instances', [])
    if instances_data:
        render_instances_section(instances_data, lines)
    # Render extra action-specific data section (if any)
    extra_data = {k: v for k, v in source_data.items() if k not in ['video', 'usage', 'instances', 'extra_actions']}
    if extra_data:
        render_extra_data_section(extra_data, lines)
    # Render streaming link at the bottom
    video_id = video_data.get('id')
    if video_id is not None:
        log(f"Rendering streaming link for video {video_id}")
        stream_url = f"/video/{video_id}/stream"
        caption = video_data.get('caption', 'video')
        stream_link = f'<p><a href="{stream_url}">Click here to stream: {safe_str(caption)}</a></p>'
        lines.append(stream_link)
        break_section(lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
