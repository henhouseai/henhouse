from __future__ import annotations
from typing import Dict, List, Union, Any, Optional
import json
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data
from hh.page.render_helpers import (
    render_path_section,
    render_badge_headers_section,
    render_text_section,
    render_children_by_class_section,
    render_images_section
)

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


# render_path_section, render_badge_headers_section, render_text_section,
# render_children_by_class_section, and render_images_section are now imported from render_helpers

from hh.render.render import TableData, FieldConfig, render_block
from hh.render.config.config import safe_str
from hh.tp.tp import TextProcessor
from hh.render.html.image_group import ImageGroup


def render_page_summary_badge(badge_data: Dict[str, Any], page_id: Optional[int] = None) -> None:
    trace_in()
    gateway = get_gateway()
    # Skip rendering for HTTP backend - handled by AJAX
    if gateway and hasattr(gateway, 'backend') and gateway.backend == "http":
        log("Skipping page summary badge for HTTP backend (handled by AJAX)")
        trace_out()
        return
    page_data = TableData()
    # Known fields that have special handling
    known_fields = {'page_id', 'name', 'link', 'parent', 'class', 'modified', 'username', 'children'}
    field_config_list = []
    
    # Page ID
    page_id = badge_data.get('page_id')
    if page_id:
        page_data.add_row(
            'page_id',
            value=str(page_id)
        )
        field_config_list.append('page_id')
    # Page Name
    page_name = badge_data.get('name')
    if page_name:
        page_data.add_row(
            'page_name',
            value=safe_str(page_name)
        )
        field_config_list.append('page_name')
    # Page Link
    page_link = badge_data.get('link')
    if page_link:
        page_data.add_row(
            'page_link',
            value=safe_str(page_link)
        )
    else:
        page_data.add_row(
            'page_link',
            value='None'
        )
    field_config_list.append('page_link')
    # Parent
    parent = badge_data.get('parent')
    if parent is not None:
        page_data.add_row(
            'page_parent',
            value=str(parent)
        )
        field_config_list.append('page_parent')
    # Class
    page_class = badge_data.get('class')
    if page_class:
        page_data.add_row(
            'page_class',
            value=safe_str(page_class)
        )
        field_config_list.append('page_class')
    # Last Modified
    last_modified = badge_data.get('modified')
    if last_modified:
        page_data.add_row(
            'page_modified',
            value=safe_str(last_modified)
        )
        field_config_list.append('page_modified')
    # Username
    username = badge_data.get('username')
    if username:
        page_data.add_row(
            'page_username',
            value=safe_str(username)
        )
        field_config_list.append('page_username')
    # Number of Children
    children_count = badge_data.get('children', 0)
    page_data.add_row(
        'page_num_children',
        value=str(children_count)
    )
    field_config_list.append('page_num_children')
    
    # Handle any extra fields dynamically
    for key, value in badge_data.items():
        if key not in known_fields:
            # Convert None to blank string (don't skip - we want to show the row even if blank)
            if value is None:
                value_str = ''
            else:
                # Convert value to string, handling complex types
                if isinstance(value, (list, dict)):
                    value_str = str(value)
                else:
                    value_str = str(value)
            # Generate field name (e.g., 'path' -> 'page_path', 'language' -> 'page_language')
            field_name = f'page_{key}'
            page_data.add_row(
                field_name,
                value=safe_str(value_str)
            )
            field_config_list.append(field_name)
    
    # Add page_text to field config if it's in the standard list (even if not in badge_data)
    if 'page_text' not in field_config_list:
        field_config_list.insert(-1, 'page_text')  # Insert before page_num_children
    
    if page_data.num_rows() > 0:
        # Generate wrapper_id with page_id if available
        wrapper_id = f'pageSummary_{page_id}' if page_id is not None else None
        
        badge_block = render_block(
            page_data,
            FieldConfig()
                .add_header('show_page_header')
                .add_simple(field_config_list),
            table_overrides={'margin_l': 4},
            block_type='badge_headers',
            wrapper_id=wrapper_id
        )
        gateway.response.set_upper_content(badge_block)
    trace_out()


def render_generic_badge(badge_name: str, badge_data: Dict[str, Any], page_id: Optional[int] = None) -> None:
    trace_in()
    gateway = get_gateway()
    # Create header row
    badge_rows = TableData()
    badge_rows.add_row(
        'badge_headers_header',
        label=f'Badge: {badge_name.replace("_", " ").title()}',
        key='Field',
        value='Value'
    )
    # Create data rows for each badge field
    for key, value in badge_data.items():
        if isinstance(value, (list, dict)):
            value = str(value)
        elif value is None:
            value = "None"
        else:
            value = str(value)
        badge_rows.add_row(
            'badge_headers_item',
            key=safe_str(key),
            value=safe_str(value)
        )
    if badge_rows.num_rows() > 0:
        # Generate wrapper_id with page_id if available
        if page_id is not None:
            badge_name_safe = badge_name.replace('_', '-')
            wrapper_id = f'badge_{badge_name_safe}_{page_id}'
        else:
            wrapper_id = None
        
        badge_block = render_block(
            badge_rows,
            FieldConfig()
                .add_header('extra_data_header')
                .add_simple(['extra_data_item']),
            table_overrides={'margin_l': 4},
            block_type='badge_headers',
            wrapper_id=wrapper_id
        )
        gateway.response.set_upper_content(badge_block)
    trace_out()


def render_upper_content_section(upper_content: List[str]) -> None:
    trace_in()
    block = 'upper_content'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    if not gateway.is_no(block) and upper_content:
        log(f"Rendering upper content section with {len(upper_content)} items")
        for content_item in upper_content:
            if isinstance(content_item, str):
                gateway.response.set_upper_content(content_item)
    trace_out()


def render_lower_content_section(lower_content: List[str]) -> None:
    trace_in()
    block = 'lower_content'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return
    if not gateway.is_no(block) and lower_content:
        log(f"Rendering lower content section with {len(lower_content)} items")
        for content_item in lower_content:
            if isinstance(content_item, str):
                gateway.response.set_lower_content(content_item)
    trace_out()


# render_children_by_class_section is now imported from render_helpers


def render_children_section(children_data: List[Dict[str, Union[str, int]]], page_id: Optional[int] = None) -> None:
    trace_in()
    block = 'children'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block) and children_data:
        log("Rendering children data section")
        # Create header row
        children_rows = TableData()
        children_rows.add_row(
            'children_header',
            label='Child Pages',
            id='ID',
            name='Name', 
            page_class='Class',
            modified='Modified',
            num_children='Children'
        )
        # Create data rows for each child
        for child in children_data:
            child_id = child.get('id')
            children_rows.add_row(
                'child_page',
                id=str(child_id) if child_id is not None else 'N/A',
                name=safe_str(child.get('name', 'N/A')),
                page_class=safe_str(child.get('class', 'N/A')),
                modified=safe_str(child.get('last_modified', 'N/A')),
                num_children=str(child.get('num_children', 0))
            )
            # Add page link metadata to label, id, and name columns
            if child_id is not None:
                children_rows.add_page_link_to_column('label', child_id)
                children_rows.add_page_link_to_column('id', child_id)
                children_rows.add_page_link_to_column('name', child_id)
        if children_rows.num_rows() > 0:
            # Generate wrapper_id with page_id if available
            wrapper_id = f'childPages_{page_id}' if page_id is not None else None
            
            children_block = render_block(
                children_rows,
                FieldConfig()
                    .add_header('children_header')
                    .add_simple(['child_page']),
                table_overrides={'margin_l': 4},
                block_type=block,
                wrapper_id=wrapper_id
            )
            gateway.response.set_lower_content(children_block)
    trace_out()


# render_images_section is now imported from render_helpers


def render_files_section(files_data: List[Dict[str, Any]], page_id: Optional[int] = None) -> None:
    trace_in()
    block = 'files'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block) and files_data:
        log(f"Rendering files section with {len(files_data)} files")
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
            if file_path:
                files_rows.add_file_link_to_column('name', file_path)
                files_rows.add_file_link_to_column('path', file_path)
        if files_rows.num_rows() > 0:
            # Generate wrapper_id with page_id if available
            wrapper_id = f'fileGroup_{page_id}' if page_id is not None else None
            
            files_block = render_block(
                files_rows,
                FieldConfig()
                    .add_header('files_header')
                    .add_simple(['file_item']),
                table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},
                block_type=block,
                wrapper_id=wrapper_id
            )
            gateway.response.set_file_group(files_block)
    trace_out()


def render_extra_data_section(extra_data: Dict[str, Any], page_id: Optional[int] = None) -> None:
    trace_in()
    block = 'extra_data'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
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
            if key == 'processed_images' and isinstance(value, list):
                value = f"{len(value)} images processed"
            elif key == 'failed_images' and isinstance(value, list):
                value = f"{len(value)} images failed"
            elif isinstance(value, (list, dict)):
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
            
            # Generate wrapper_id with page_id if available
            wrapper_id = f'extraData_{page_id}' if page_id is not None else None
            
            extra_block = render_block(
                extra_rows,
                field_config,
                table_overrides={'margin_l': 4},
                block_type=block,
                wrapper_id=wrapper_id
            )
            gateway.response.set_lower_content(extra_block)
    trace_out()


# render_text_section is now imported from render_helpers

@register_http('show_page')
@register_parser('show_page')
@register_parser('add_page')
@register_parser('add_image')
@register_parser('add_images')
@register_parser('modify_name')
@register_parser('modify_text')
@register_parser('move_page')
@register_parser('copy_page')
@register_parser('remove_image')
@register_parser('set_image_rank')
@register_parser('copy_image')
@register_parser('copy_images')
@register_parser('move_image')
@register_parser('move_images')
def show_page() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    json_data = gateway.response.get_action_response()
    # Inject header block into contentWrapperHeader
    header_content = render_header_block('l_show_page_header', 'page_header')
    if header_content:
        gateway.response.set_content_wrapper_header(header_content)
    source_data = get_data(json_data)
    log("Processing show page data successfully")
    
    page_data = source_data.get('page', {})
    
    # Render all sections - response classes handle output format differences
    cache_built_at = source_data.pop('cache_built_at', None)
    page_id = page_data.get('id')
    
    # Use helpers (overlay_mode=False for HTTP backend)
    render_path_section(page_data, page_id=page_id, overlay_mode=False)
    badge_headers = source_data.get('badge_headers', {})
    if badge_headers:
        render_badge_headers_section(badge_headers, page_id=page_id, overlay_mode=False)
    
    render_text_section(page_data, overlay_mode=False)
    
    upper_content = source_data.get('upper_content', [])
    if upper_content:
        render_upper_content_section(upper_content)
    
    children_by_class = source_data.get('children_by_class', {})
    images_data = source_data.get('images', [])
    files_data = source_data.get('files', [])
    if images_data:
        render_images_section(images_data, page_id=page_id, overlay_mode=False)
    if files_data:
        render_files_section(files_data, page_id=page_id)
    if children_by_class:
        render_children_by_class_section(children_by_class, page_id=page_id, overlay_mode=False)
    lower_content = source_data.get('lower_content', [])
    if lower_content:
        render_lower_content_section(lower_content)
    extra_data = {
        k: v
        for k, v in source_data.items()
        if k
        not in [
            'page',
            'children_by_class',
            'images',
            'files',
            'badge_headers',
            'upper_content',
            'lower_content',
            'cache_built_at',
        ]
    }
    if extra_data:
        render_extra_data_section(extra_data, page_id=page_id)
    
    log(f"Show page handler executed successfully")
    
    trace_out()
    return True
