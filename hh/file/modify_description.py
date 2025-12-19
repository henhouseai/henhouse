from __future__ import annotations
from typing import Dict, Any, Mapping, cast
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.file.file_registry import get_file
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

@register_action('modify_file_description')
@register_command('modify_file_description')
def modify_file_description() -> bool:
    trace_in()
    gateway = get_gateway()
    file_id_arg = gateway.get_arg('file_id') or gateway.get_arg('id')
    description = gateway.get_arg('description')
    
    if not file_id_arg:
        warn("No file ID provided")
        report_error("action", "File ID is required")
    if description is None:
        warn("No description provided")
        report_error("action", "Description is required")
    if description is True:
        if gateway.get_arg('clear'):
            description = ''
        else:
            warn("Empty description provided, use -clear to clear it")
            report_error("action", "Empty description provided, use -clear to clear it")

    file_id: int = 0
    if not is_error():
        try:
            file_id = int(file_id_arg)
        except ValueError:
            warn(f"Invalid file ID: {file_id_arg}")
            report_error("action", "File ID must be a number")
    
    file = None
    if not is_error():
        log(f"Loading file {file_id}")
        file = get_file(file_id=file_id)
        if not file:
            warn(f"File {file_id} not found")
            report_error("action", f"File {file_id} not found")
    
    old_description: str = ""
    if not is_error() and file is not None:
        log(f"Modifying description for file {file_id} to: {description}")
        old_description = file.description if file.description is not None else ""
        success = file.modify_description(description)
        if not success:
            warn(f"Failed to modify description for file {file_id}")
            report_error("action", f"Failed to modify description for file {file_id}")
    
    if not is_error():
        # Build minimal response structure
        response_data = {
            "file_id": file_id,
            "old_description": old_description,
            "new_description": description
        }
        
        log(f"Successfully modified description for file {file_id}")
        gateway.response.set_action_response(success_payload(response_data))
    
    trace_out()
    return not is_error()


@register_parser('modify_file_description')
def modify_file_description_parser() -> bool:
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
        file_id = source_data.get("file_id")
        old_description = source_data.get("old_description", "")
        new_description = source_data.get("new_description", "")
        
        lines = [render_header_block("l_modify_file_description_header")]
        
        table = TableData()
        table.add_row("modify_file_description_header", info="")
        
        # Operation details
        table.add_row("file_id", info=str(file_id))
        table.add_row("extra_data_old_description", info=old_description if old_description else "N/A")
        table.add_row("extra_data_new_description", info=new_description if new_description else "N/A")
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("modify_file_description_header")
                .add_simple(["file_id", "extra_data_old_description", "extra_data_new_description"]),
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
