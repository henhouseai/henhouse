"""
Shared rendering helper functions for show_page HTTP backend and get_browser action.
These functions generate HTML for page sections and can be used in both contexts.
"""
from __future__ import annotations
from typing import Dict, List, Union, Any, Optional
import json
from hh.render.render import render_block, FieldConfig, TableData
from hh.render.config.config import safe_str
from hh.render.html.image_group import ImageGroup
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.tp.tp import TextProcessor

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


def render_path_section(
    page_data: Dict[str, Any],
    page_id: Optional[int] = None,
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """
    Render the breadcrumb path section.
    
    Returns HTML string if overlay_mode is True, otherwise sets on gateway.response.
    """
    """
    Render the breadcrumb path section.
    
    Returns HTML string if overlay_mode is True, otherwise sets on gateway.response.
    """
    trace_in()
    gateway = get_gateway()
    if additional_classes is None:
        additional_classes = []
    
    path_data = page_data.get('path', [])
    if not path_data:
        log("No path data available")
        trace_out()
        return None
    
    # Special handling for HTTP backend - build path HTML for server-side rendering
    if gateway and hasattr(gateway, 'backend') and gateway.backend == "http" and not overlay_mode:
        log(f"Building path HTML for HTTP backend with {len(path_data)} levels")
        path_items = []
        for path_item in path_data:
            path_item_id = path_item.get('id')
            if path_item_id is not None:
                name = path_item.get('name') or path_item.get('title') or f"Page {path_item_id}"
                link_href = f"{path_item_id}"
                path_items.append(f'<li><a href="{link_href}">{safe_str(name)}</a></li>')
        if path_items:
            path_html = f'<ul class="path">{"".join(path_items)}</ul>'
            gateway.response.set_path(path_html)
            log(f"Set path HTML for HTTP backend: {len(path_html)} characters")
        trace_out()
        return None
    
    log(f"Rendering path section with {len(path_data)} levels")
    # Create header row
    path_rows = TableData()
    path_rows.add_row(
        'page_path_header',
        label='Path',
        id='ID',
        name='Name'
    )
    # Create data rows for each path level
    for i, path_item in enumerate(path_data):
        path_item_id = path_item.get('id')
        name = path_item.get('name', f"Page {path_item_id}" if path_item_id else 'Unknown')
        path_rows.add_row(
            'page_path',
            id=str(path_item_id) if path_item_id is not None else 'Unknown',
            name=safe_str(name)
        )
        # Add page link metadata to label, id, and name columns
        if path_item_id is not None:
            path_rows.add_page_link_to_column('label', path_item_id)
            path_rows.add_page_link_to_column('id', path_item_id)
            path_rows.add_page_link_to_column('name', path_item_id)
    
    if path_rows.num_rows() > 0:
        # Generate wrapper_id with page_id if available
        wrapper_id = f'{wrapper_id_prefix}pagePath_{page_id}' if page_id is not None else None
        
        wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
        
        path_block = render_block(
            path_rows,
            FieldConfig()
                .add_header('page_path_header')
                .add_simple(['page_path']),
            table_overrides={'margin_l': 4},
            block_type='path',
            wrapper_id=wrapper_id,
            wrapper_extra_classes=wrapper_extra_classes,
            backend='http' if overlay_mode else None
        )
        
        if overlay_mode:
            trace_out()
            # Strip trailing newlines
            return path_block.rstrip('\n') if path_block else None
        else:
            gateway.response.set_upper_content(path_block)
    
    trace_out()
    return None


def render_badge_headers_section(
    badge_headers: Dict[str, Any],
    page_id: Optional[int] = None,
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """
    Render badge headers section.
    
    Returns HTML string if overlay_mode is True, otherwise sets on gateway.response.
    """
    trace_in()
    gateway = get_gateway()
    if additional_classes is None:
        additional_classes = []
    
    if not gateway:
        warn("No gateway available")
        trace_out()
        return None
    
    block = 'badges'
    if gateway.is_no(block) or not badge_headers:
        trace_out()
        return None
    
    log(f"Rendering badge headers with {len(badge_headers)} badges")
    html_parts = []
    
    # Render each badge as a separate table
    for badge_name, badge_data in badge_headers.items():
        if not isinstance(badge_data, dict):
            continue
        log(f"Rendering badge '{badge_name}' with {len(badge_data)} fields")
        # Special handling for page_summary badge
        if badge_name == 'page_summary':
            badge_html = render_page_summary_badge(
                badge_data,
                page_id=page_id,
                overlay_mode=overlay_mode,
                wrapper_id_prefix=wrapper_id_prefix,
                additional_classes=additional_classes
            )
        else:
            # Generic badge rendering for other badge types
            badge_html = render_generic_badge(
                badge_name,
                badge_data,
                page_id=page_id,
                overlay_mode=overlay_mode,
                wrapper_id_prefix=wrapper_id_prefix,
                additional_classes=additional_classes
            )
        
        if badge_html:
            html_parts.append(badge_html)
    
    if overlay_mode:
        trace_out()
        # Strip trailing newlines from each part before joining to avoid blank lines between sections
        cleaned_parts = [part.rstrip('\n') for part in html_parts if part]
        result = '\n'.join(cleaned_parts) if cleaned_parts else None
        return result
    else:
        for html_part in html_parts:
            gateway.response.set_upper_content(html_part)
        trace_out()
        return None


def render_page_summary_badge(
    badge_data: Dict[str, Any],
    page_id: Optional[int] = None,
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """Render page summary badge."""
    trace_in()
    gateway = get_gateway()
    if additional_classes is None:
        additional_classes = []
    
    # Skip rendering for HTTP backend - handled by AJAX
    if gateway and hasattr(gateway, 'backend') and gateway.backend == "http" and not overlay_mode:
        log("Skipping page summary badge for HTTP backend (handled by AJAX)")
        trace_out()
        return None
    
    page_data = TableData()
    # Known fields that have special handling
    known_fields = {'page_id', 'name', 'link', 'parent', 'class', 'modified', 'username', 'children'}
    field_config_list = []
    
    # Page ID
    badge_page_id = badge_data.get('page_id')
    if badge_page_id:
        page_data.add_row(
            'page_id',
            value=str(badge_page_id)
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
        wrapper_id = f'{wrapper_id_prefix}pageSummary_{badge_page_id}' if badge_page_id is not None else None
        
        wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
        
        badge_block = render_block(
            page_data,
            FieldConfig()
                .add_header('show_page_header')
                .add_simple(field_config_list),
            table_overrides={'margin_l': 4},
            block_type='badge_headers',
            wrapper_id=wrapper_id,
            wrapper_extra_classes=wrapper_extra_classes,
            backend='http' if overlay_mode else None
        )
        
        if overlay_mode:
            trace_out()
            return badge_block
        else:
            gateway.response.set_upper_content(badge_block)
    
    trace_out()
    return None


def render_generic_badge(
    badge_name: str,
    badge_data: Dict[str, Any],
    page_id: Optional[int] = None,
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """Render generic badge."""
    trace_in()
    gateway = get_gateway()
    if additional_classes is None:
        additional_classes = []
    
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
            wrapper_id = f'{wrapper_id_prefix}badge_{badge_name_safe}_{page_id}'
        else:
            wrapper_id = None
        
        wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
        
        badge_block = render_block(
            badge_rows,
            FieldConfig()
                .add_header('extra_data_header')
                .add_simple(['extra_data_item']),
            table_overrides={'margin_l': 4},
            block_type='badge_headers',
            wrapper_id=wrapper_id,
            wrapper_extra_classes=wrapper_extra_classes,
            backend='http' if overlay_mode else None
        )
        
        if overlay_mode:
            trace_out()
            return badge_block
        else:
            gateway.response.set_upper_content(badge_block)
    
    trace_out()
    return None


def render_text_section(
    page_data: Dict[str, Union[str, int]],
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """
    Render text content section.
    
    Returns HTML string if overlay_mode is True, otherwise sets on gateway.response.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return None
    
    block = 'text'
    text_content = page_data.get('text')
    prepared_content = page_data.get('prepared_text')
    
    if gateway.is_no(block) or (text_content is None and not prepared_content):
        trace_out()
        return None
    
    log("Rendering text content section with TextProcessor")
    # Determine final decorator based on backend and user preference
    use_json = gateway.request.get_arg('json') if gateway.request else False
    if use_json:
        final_decorator = 'mcp'
    else:
        final_decorator = gateway.backend if not overlay_mode else 'http'
    
    processor = TextProcessor()
    processed_text = ""
    processed_payload = None
    
    if prepared_content:
        debug("Using prepared text from cache for rendering")
        if isinstance(prepared_content, str):
            try:
                processed_payload = json.loads(prepared_content)
            except json.JSONDecodeError:
                warn("Failed to decode prepared_text JSON, falling back to live processing")
        else:
            processed_payload = prepared_content
    
    if processed_payload is None:
        debug("Prepared text unavailable, preprocessing raw text")
        preprocessed = processor.preprocess(str(text_content))
        if preprocessed is None:
            processed_payload = None
        else:
            processed_payload = preprocessed
    
    if processed_payload is not None:
        processed_text = processor.postprocess(processed_payload, final_decorator=final_decorator)
    else:
        debug("Preprocessing failed, returning raw text")
        processed_text = str(text_content)
    
    # Get page_id from page_data for ID attribute
    page_id = page_data.get('id')
    id_attr = f' id="{wrapper_id_prefix}page-text-{page_id}"' if page_id else ''
    
    # Build class string: always "content pageText", plus any additional classes
    class_parts = ['content', 'pageText']
    if additional_classes:
        class_parts.extend(additional_classes)
    class_str = ' '.join(class_parts)
    
    # Standardize: id always comes before class
    wrapped_text = f'<div{id_attr} class="{class_str}">{safe_str(processed_text)}</div>'
    
    if overlay_mode:
        trace_out()
        return wrapped_text
    else:
        gateway.response.set_page_text(processed_text)
        trace_out()
        return None


def render_children_by_class_section(
    children_by_class: Dict[str, Dict[str, Any]],
    page_id: int = None,
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """
    Render children by class section.
    
    Returns HTML string if overlay_mode is True, otherwise sets on gateway.response.
    """
    trace_in()
    gateway = get_gateway()
    if additional_classes is None:
        additional_classes = []
    
    if not gateway:
        warn("No gateway available")
        trace_out()
        return None
    
    block = 'children'
    if gateway.is_no(block) or not children_by_class:
        trace_out()
        return None
    
    log(f"Rendering children by class section with {len(children_by_class)} classes")
    
    # Get page object for getChildrenOf() calls
    page = None
    if page_id:
        from hh.page.page_registry import get_page
        page = get_page(page_id)
    
    # Determine view_type based on backend
    if overlay_mode or gateway.backend == "parser":
        # Overlay mode or parser backend: force table format
        view_type = 'table'
    else:
        # HTTP backend: don't pass view_type, let each class use its own default
        view_type = None
    
    html_parts = []
    
    for class_name, class_data in children_by_class.items():
        # Re-fetch children data with appropriate view_type using static getChildrenOf method
        if page:
            from hh.page.page_class_registry import get_page_class
            PageClass = get_page_class(class_name)
            if PageClass:
                if view_type is not None:
                    children_data = PageClass.getChildrenOf(page.id, view_type=view_type)
                else:
                    # Don't pass view_type - let class use its own default
                    children_data = PageClass.getChildrenOf(page.id)
            else:
                # Fallback to existing data if class not found
                children_data = class_data.get('children', [])
        else:
            # Fallback to existing data if page not available
            children_data = class_data.get('children', [])
        
        if not children_data:
            continue
        
        log(f"Rendering {len(children_data)} children for class '{class_name}' (view_type: {view_type})")
        
        # Check data format
        data_format = children_data[0].get('_format', 'table') if children_data else 'table'
        
        # Error check: parser backend should never receive tile data
        if gateway.backend == "parser" and data_format == 'tile':
            warn(f"Parser backend received tile-formatted data for class '{class_name}' - this should never happen")
            report_error("backend", f"Parser backend received tile data for class '{class_name}'")
            trace_out()
            return None
        
        if data_format == 'tile' and (overlay_mode or gateway.backend == "http"):
            # Render as tiles using PageGroup (requires page_id for headers/content IDs)
            if page_id is None:
                warn(f"page_id is required for tile rendering of class '{class_name}'")
                # Fall through to table rendering
            else:
                # Generate toggle header (stays static, doesn't get swapped)
                page_id_str = str(page_id)
                class_name_safe = class_name.replace('_', '-')
                header_id = f"{wrapper_id_prefix}child_pages_{class_name_safe}_header_{page_id_str}"
                from hh.render.html.page_group import snake_case_to_title_case
                human_readable_name = snake_case_to_title_case(class_name)
                # Add overlay class if in overlay mode
                header_classes = 'contentHeader'
                if additional_classes:
                    header_classes += ' ' + ' '.join(additional_classes)
                header_html = f'<div id="{header_id}" class="{header_classes}">\n  <a class="updatePageView_{page_id_str}" data-section="children" data-class-name="{class_name}">{human_readable_name}</a>\n</div>'
                
                from hh.render.html.page_group import PageGroup
                wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
                page_group = PageGroup(children_data, page_id, class_name, target_width=300, wrapper_extra_classes=wrapper_extra_classes)
                content_html = page_group.render()  # Get HTML string (includes wrapper divs)
                # Strip trailing newlines from content_html before joining
                content_html_clean = content_html.rstrip('\n') if content_html else ''
                # Prepend header and add to parts
                html_parts.append(header_html + '\n' + content_html_clean)
                continue  # Skip table rendering
        
        # Render as table (parser backend, HTTP with table override, or HTTP tiles without page_id)
        # Get all field names dynamically from first child, preserving order
        # Exclude metadata fields like 'field_type' and '_format' from display
        first_child = children_data[0]
        field_names = [k for k in first_child.keys() if not k.startswith('_') and k != 'field_type' and k != '_format']
        
        # Check if any child has children - if not, remove num_children column
        if 'num_children' in field_names:
            has_any_children = any(child.get('num_children', 0) > 0 for child in children_data)
            if not has_any_children:
                field_names.remove('num_children')
        
        # Create header row dynamically using field names
        children_rows = TableData()
        header_kwargs = {}
        for field_name in field_names:
            header_kwargs[field_name] = field_name.replace('_', ' ').title()
        children_rows.add_row('children_header', **header_kwargs)
        
        # Collect all unique field_types from children for FieldConfig
        field_types = set()
        for child in children_data:
            field_type = child.get('field_type', 'page')
            field_types.add(field_type)
        field_types_list = sorted(list(field_types))
        
        # Create data rows dynamically for each child
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
            
            # Add page link metadata to first three fields
            if child_id is not None:
                children_rows.add_page_link_to_column('label', child_id)
                if len(field_names) > 0:
                    children_rows.add_page_link_to_column(field_names[0], child_id)
                if len(field_names) > 1:
                    children_rows.add_page_link_to_column(field_names[1], child_id)
        
        if children_rows.num_rows() > 0:
            page_id_str = str(page_id) if page_id is not None else ''
            class_name_safe = class_name.replace('_', '-')
            header_id = f"{wrapper_id_prefix}child_pages_{class_name_safe}_header_{page_id_str}"
            content_id = f"{wrapper_id_prefix}child_pages_{class_name_safe}_{page_id_str}"
            from hh.render.html.page_group import snake_case_to_title_case
            human_readable_name = snake_case_to_title_case(class_name)
            # Add overlay class if in overlay mode
            header_classes = 'contentHeader'
            if additional_classes:
                header_classes += ' ' + ' '.join(additional_classes)
            header_html = f'<div id="{header_id}" class="{header_classes}">\n  <a class="updatePageView_{page_id_str}" data-section="children" data-class-name="{class_name}">{human_readable_name}</a>\n</div>'
            # Render block with wrapper configuration
            wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
            
            children_block = render_block(
                children_rows,
                FieldConfig()
                    .add_header('children_header')
                    .add_simple(field_types_list),
                table_overrides={'margin_l': 4},
                block_type=block,
                wrapper_id=content_id,
                wrapper_extra_classes=wrapper_extra_classes,
                backend='http' if overlay_mode else None
            )
            # Strip trailing newlines from children_block before joining
            children_block_clean = children_block.rstrip('\n') if children_block else ''
            html_parts.append(header_html + '\n' + children_block_clean)
    
    if overlay_mode:
        trace_out()
        # Strip trailing newlines from each part before joining to avoid blank lines between sections
        cleaned_parts = [part.rstrip('\n') for part in html_parts if part]
        result = '\n'.join(cleaned_parts) if cleaned_parts else None
        return result
    else:
        for html_part in html_parts:
            if gateway.backend == "http" and page_id is not None:
                gateway.response.add_child_pages(html_part)
            else:
                gateway.response.set_lower_content(html_part)
        trace_out()
        return None


def render_images_section(
    images_data: List[Dict[str, Any]],
    page_id: int = None,
    overlay_mode: bool = False,
    wrapper_id_prefix: str = '',
    additional_classes: List[str] = None
) -> Optional[str]:
    """
    Render images section.
    
    Returns HTML string if overlay_mode is True, otherwise sets on gateway.response.
    """
    trace_in()
    gateway = get_gateway()
    if additional_classes is None:
        additional_classes = []
    
    if not gateway:
        warn("No gateway available")
        trace_out()
        return None
    
    block = 'images'
    if gateway.is_no(block) or not images_data:
        trace_out()
        return None
    
    # For HTTP backend with tiles, page_id is required for headers/content IDs
    # For parser backend or HTTP with tables, page_id is optional (backward compatible)
    if (overlay_mode or gateway.backend == "http") and page_id is None:
        warn("page_id is required for HTTP backend image rendering")
        trace_out()
        return None
    
    log(f"Rendering images section with {len(images_data)} images")
    
    if gateway.backend == "parser" and not overlay_mode:
        # Parser backend: render as table (no HTML wrappers, just CLI table)
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
            wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
            
            images_block = render_block(
                images_rows,
                FieldConfig()
                    .add_header('images_header')
                    .add_simple(['image_item']),
                table_overrides={'margin_l': 4, 'column_align': {'rank': 'center'}},
                block_type=block,
                wrapper_extra_classes=wrapper_extra_classes
            )
            if overlay_mode:
                trace_out()
                return images_block
            else:
                gateway.response.set_lower_content(images_block)
                trace_out()
                return None
    else:
        # HTTP backend or overlay mode: render as tiles
        if page_id is None:
            warn("page_id is required for tile rendering")
            trace_out()
            return None
        page_id_str = str(page_id)
        header_id = f"{wrapper_id_prefix}pageImageGroupHeader_{page_id_str}"
        # Add overlay class if in overlay mode
        header_classes = 'contentHeader'
        if additional_classes:
            header_classes += ' ' + ' '.join(additional_classes)
        header_html = f'<div id="{header_id}" class="{header_classes}">\n  <a class="updatePageView_{page_id_str}" data-section="images">IMAGES</a>\n</div>'
        
        wrapper_extra_classes = ' '.join(additional_classes) if additional_classes else None
        image_group = ImageGroup(images_data, page_id, target_width=300, wrapper_extra_classes=wrapper_extra_classes)
        content_html = image_group.render()  # Get HTML string (includes wrapper divs)
        # Prepend header
        result = header_html + content_html
        
        if overlay_mode:
            trace_out()
            return result
        else:
            gateway.response.set_image_group(result)
            trace_out()
            return None
    
    trace_out()
    return None

