"""Get browser action - returns HTML for browser overlay with structured sections."""

from __future__ import annotations
from typing import Dict, Any, Optional
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.response.json_standard import success_payload
from hh.page.page_registry import get_page, find_page
from hh.page.render_helpers import (
    render_path_section,
    render_badge_headers_section,
    render_text_section,
    render_children_by_class_section,
    render_images_section
)
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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


@register_action('get_browser')
@register_command('get_browser')
def get_browser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    # Get page identifier
    if not gateway.is_set('id') and not gateway.is_set('name') and not gateway.is_set('link'):
        warn("No page identifier provided")
        report_error("action", "Page ID, name, or link is required")
        trace_out()
        return False
    
    page = None
    page_id = gateway.get_arg('id')
    page_name = gateway.get_arg('name')
    page_link = gateway.get_arg('link')
    search_term = None
    
    # Determine which parameter was provided
    if page_id:
        log(f"Using page ID: {page_id}")
        try:
            page_id = int(page_id)
        except ValueError:
            warn(f"Invalid page ID: {page_id}")
            report_error("action", "Page ID must be a number")
            trace_out()
            return False
        if not is_error():
            page = get_page(page_id=page_id)
            if not page:
                warn(f"Page {page_id} not found")
                report_error("action", f"Page {page_id} not found")
                trace_out()
                return False
    elif page_name or page_link:
        # Use name as alias for link
        search_term = page_name if page_name else page_link
        log(f"Searching for page with name/link: {search_term}")
        page = find_page(link=search_term)
        if not page:
            warn(f"No page found with name/link: {search_term}")
            report_error("action", f"No page found with name/link: {search_term}")
            trace_out()
            return False
        page_id = page.id
    
    if is_error():
        trace_out()
        return False
    
    # Get full page data directly (not via show_page which returns lightweight for MCP)
    page_data = page.get_page_data()
    images_data = page.get_images_data()
    files_data = page.get_files_data()
    children_by_class = page._get_children_by_class()
    badge_headers = page._add_badge_headers()
    upper_content = page._add_upper_content()
    lower_content = page._add_lower_content()
    
    # Get prepared text if available
    prepared_payload = page.get_prepared_text()
    if prepared_payload is not None:
        page_data = dict(page_data)
        page_data['prepared_text'] = prepared_payload
    
    # Render all sections with overlay mode
    overlay_mode = True
    wrapper_id_prefix = 'overlay_'
    additional_classes = ['overlay']
    
    # Render sections (these return HTML strings in overlay mode)
    path_html = render_path_section(
        page_data,
        page_id=page_id,
        overlay_mode=overlay_mode,
        wrapper_id_prefix=wrapper_id_prefix,
        additional_classes=additional_classes
    ) or ""
    
    badges_html = ""
    if badge_headers:
        badges_html = render_badge_headers_section(
            badge_headers,
            page_id=page_id,
            overlay_mode=overlay_mode,
            wrapper_id_prefix=wrapper_id_prefix,
            additional_classes=additional_classes
        ) or ""
    
    text_html = render_text_section(
        page_data,
        overlay_mode=overlay_mode
    ) or ""
    
    children_html = ""
    if children_by_class:
        children_html = render_children_by_class_section(
            children_by_class,
            page_id=page_id,
            overlay_mode=overlay_mode,
            wrapper_id_prefix=wrapper_id_prefix,
            additional_classes=additional_classes
        ) or ""
    
    images_html = ""
    if images_data:
        images_html = render_images_section(
            images_data,
            page_id=page_id,
            overlay_mode=overlay_mode,
            wrapper_id_prefix=wrapper_id_prefix,
            additional_classes=additional_classes
        ) or ""
    
    # Build structured response
    payload = {
        "page_id": page_data.get("id"),
        "page_name": page_data.get("name"),
        "parent": page_data.get("parent"),
        "class": page_data.get("class"),
        "sections": {
            "path": path_html,
            "badges": badges_html,
            "text": text_html,
            "children": children_html,
            "images": images_html,
            "files": ""  # TODO: implement files section when needed
        }
    }
    
    gateway.response.set_action_response(success_payload(payload))
    log(f"Generated browser HTML for page {page_id}")
    trace_out()
    return True


@register_parser('get_browser')
def get_browser_parser() -> bool:
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
        from hh.gateway.response.json_standard import get_data
        from hh.render.render import FieldConfig, TableData, render_block, render_header_block, finalize_output
        
        source_data = get_data(gateway.response.get_action_response())
        page_id = source_data.get("page_id")
        page_name = source_data.get("page_name")
        parent = source_data.get("parent")
        page_class = source_data.get("class")
        sections = source_data.get("sections", {})
        
        lines = [render_header_block("l_get_browser_header")]
        
        table = TableData()
        table.add_row("get_browser_header", info="")
        table.add_row("page_id", info=str(page_id) if page_id is not None else "N/A")
        table.add_row("page_name", info=str(page_name) if page_name else "N/A")
        table.add_row("page_parent", info=str(parent) if parent is not None else "N/A")
        table.add_row("page_class", info=str(page_class) if page_class else "N/A")
        table.add_row("path_html", info=sections.get("path", ""))
        table.add_row("badges_html", info=sections.get("badges", ""))
        table.add_row("text_html", info=sections.get("text", ""))
        table.add_row("children_html", info=sections.get("children", ""))
        table.add_row("images_html", info=sections.get("images", ""))
        
        # Add horizontal rules after Class (row 3) and after each HTML section (rows 4-7)
        # Row indices: 0=header, 1=page_id, 2=page_name, 3=page_parent, 4=page_class, 
        #              5=path_html, 6=badges_html, 7=text_html, 8=children_html, 9=images_html
        separator_after_rows = [4, 5, 6, 7, 8]  # After Class and each HTML section
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                    .add_header("get_browser_header")
                    .add_simple([
                        "page_id",
                        "page_name",
                        "page_parent",
                        "page_class",
                        "path_html",
                        "badges_html",
                        "text_html",
                        "children_html",
                        "images_html",
                    ]),
                block_type="maintenance",
                table_overrides={"margin_l": 4, "separator_after_rows": separator_after_rows}
            )
        )
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False

