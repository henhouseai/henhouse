from __future__ import annotations
from typing import Dict, Any, Mapping, cast
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block

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

@register_action('set_page_display_style')
@register_command('set_page_display_style')
def set_page_display_style() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set('display_style') and not gateway.is_set('displayStyle'):
            warn("No display style value provided")
            report_error("action", "Display style value is required (use display_style or displayStyle)")
    page_id: int = 0
    display_style: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        display_style_arg = gateway.get_arg('display_style') or gateway.get_arg('displayStyle')
        try:
            page_id = int(page_id_arg)
            display_style = int(display_style_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg} or display style: {display_style_arg}")
            report_error("action", "Page ID and display style must be numbers")
    
    page = None
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    
    old_display_style: int | None = None
    if not is_error() and page is not None:
        old_display_style = getattr(page, 'displayStyle', None)
        # Check if update is needed
        if old_display_style == display_style:
            log(f"Page {page_id} display style is already {display_style}, no update needed")
        else:
            log(f"Setting page {page_id} display style from {old_display_style} to {display_style}")
            success = page.modify_display_style(display_style)
            if not success:
                warn(f"Failed to set page {page_id} display style to {display_style}")
                report_error("action", f"Failed to set page {page_id} display style to {display_style}")
    
    if not is_error():
        # Build response structure
        response_data = {
            "page_id": page_id,
            "old_display_style": old_display_style,
            "new_display_style": display_style
        }
        
        log(f"Successfully set page {page_id} display style from {old_display_style} to {display_style}")
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()


@register_parser('set_page_display_style')
def set_page_display_style_parser() -> bool:
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
        old_display_style = source_data.get("old_display_style")
        new_display_style = source_data.get("new_display_style")
        
        lines = [render_header_block("l_set_page_display_style_header")]
        
        table = TableData()
        table.add_row("set_page_display_style_header", info="")
        
        # Operation details
        table.add_row("page_id", info=str(page_id))
        table.add_row("extra_data_old_display_style", info=str(old_display_style))
        table.add_row("extra_data_new_display_style", info=str(new_display_style))
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("set_page_display_style_header")
                .add_simple(["page_id", "extra_data_old_display_style", "extra_data_new_display_style"]),
                block_type="rows",
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

