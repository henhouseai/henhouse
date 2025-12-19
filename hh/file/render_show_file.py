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
        'file_usage_header',
        label='Pages Using This File',
        page_id='Page ID',
        page_name='Page Name',
        usage_count='Count',
        rank_range='Rank'
    )
    
    # Create data rows for each page using this file
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
                .add_header('file_usage_header')
                .add_simple(['page_class']),
            table_overrides={'margin_l': 4},
            block_type='usage'
        ))
        break_section(lines)
    trace_out()


def render_file_section(file_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway.is_no(block):
        log("Rendering file data section")
        
        # Get folder path from file_path (trim filename)
        file_path = file_data.get('file_path', 'N/A')
        if file_path and file_path != 'N/A':
            # Remove filename, keep just the folder path
            last_slash = file_path.rfind('/')
            if last_slash != -1:
                file_path = file_path[:last_slash + 1]
        
        file_summary = TableData()
        
        # File ID
        file_id = file_data.get('id')
        if file_id:
            file_summary.add_row(
                'file_id',
                value=str(file_id)
            )
        
        # File Name
        file_name = file_data.get('file_name', 'untitled')
        file_summary.add_row(
            'file_name',
            value=safe_str(file_name)
        )
        
        # Description
        description = file_data.get('description', '')
        file_summary.add_row(
            'file_description',
            value=safe_str(description) if description else 'N/A'
        )
        
        # MIME Type
        mime_type = file_data.get('mime_type', 'N/A')
        file_summary.add_row(
            'file_mime',
            value=safe_str(mime_type)
        )
        
        # Size (bytes)
        size_bytes = file_data.get('size_bytes', 0)
        file_summary.add_row(
            'file_size_bytes',
            value=str(size_bytes)
        )
        
        # File Path
        file_summary.add_row(
            'file_path',
            value=safe_str(file_path)
        )
        
        # Uploaded Date
        uploaded = file_data.get('uploaded')
        if uploaded:
            file_summary.add_row(
                'file_uploaded',
                value=safe_str(uploaded)
            )
        
        # Last Modified
        last_modified = file_data.get('last_modified')
        if last_modified:
            file_summary.add_row(
                'file_last_modified',
                value=safe_str(last_modified)
            )
        
        # Visibility
        visibility = file_data.get('visibility', 1)
        file_summary.add_row(
            'file_visibility',
            value=str(visibility)
        )
        
        lines.append(render_block(
            file_summary,
            FieldConfig()
                .add_header('show_file_header')
                .add_simple(['file_id', 'file_name', 'file_description', 'file_mime', 'file_size_bytes', 'file_path', 'file_uploaded', 'file_last_modified', 'file_visibility']),
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


@register_http('show_file')
@register_parser('show_file')
def show_file() -> bool:
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
    lines.append(render_header_block('l_show_file_header'))
    source_data = get_data(cast(Mapping[str, Any], action_response))
    log("Processing show file data successfully")
    # Render usage section first
    usage_data = source_data.get('usage', [])
    render_usage_section(usage_data, lines)
    # Render main file data section
    file_data = source_data.get('file', {})
    render_file_section(file_data, lines)
    # Render extra action-specific data section (if any)
    extra_data = {k: v for k, v in source_data.items() if k not in ['file', 'usage', 'extra_actions']}
    if extra_data:
        render_extra_data_section(extra_data, lines)
    # Render download link at the bottom
    file_id = file_data.get('id')
    if file_id is not None:
        log(f"Rendering download link for file {file_id}")
        download_url = f"/file/{file_id}/download"
        file_name = file_data.get('file_name', 'file')
        download_link = f'<p><a href="{download_url}">Click here to download: {safe_str(file_name)}</a></p>'
        lines.append(download_link)
        break_section(lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
