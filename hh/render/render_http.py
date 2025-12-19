from __future__ import annotations
from typing import Dict, Union, Optional
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
# Import shared data structures from render module
from hh.render.render import TableData, FieldConfig

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


def render_html_table(table_data: TableData, field_configs: Optional[FieldConfig] = None, table_class: str = 'standard', table_overrides: Optional[Dict[str, Union[str, int, bool]]] = None, wrapper_id: Optional[str] = None, wrapper_extra_classes: Optional[str] = None) -> str:
    """HTML renderer - renders tables as HTML for web output."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    log("HTTP backend detected - using HTML renderer")
    from hh.render.html.html_flexible import render_html_flexible_table
    result = render_html_flexible_table(table_data, field_configs, table_class, table_overrides, wrapper_id=wrapper_id, wrapper_extra_classes=wrapper_extra_classes)
    log(f"HTML renderer completed: {len(result)} characters")
    trace_out()
    return result


def render_html_header(subheader_key: str, header_id: str) -> str:
    """HTML renderer - renders headers as HTML wrapped in a div with id attribute."""
    trace_in()
    import html
    from hh.render.config.config import dc
    
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    
    log("HTTP backend detected - using HTML header renderer")
    
    # Determine headers (no longer stored as response metadata; seeds are used instead)
    main_header = None
    sub_header = None
    if not gateway.is_no('main_header'):
        main_header = dc('l_main_header', True)
    if subheader_key and not gateway.is_no('sub_header'):
        sub_header = dc(subheader_key, True)
    
    # Generate header content
    header_parts = []
    if main_header:
        header_parts.append(main_header)
        log(f"Added main header: {main_header}")
    if sub_header:
        header_parts.append(sub_header)
        log(f"Added sub header: {sub_header}")
    
    if not header_parts:
        log("No header parts generated")
        trace_out()
        return ""
    
    header_content = "".join(header_parts)
    
    # Return content only (no wrapper div - response object handles wrapping)
    log(f"HTML header rendered: {len(header_content)} characters")
    trace_out()
    return header_content
