"""Migration add phase action to add a new migration phase."""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block
from ext.deploy.maint.legacy_db_connection import get_legacy_db_connection

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


@register_action("migration_add_phase")
@register_command("migration_add_phase")
def migration_add_phase_action() -> bool:
    """Add a new migration phase."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    try:
        description = gateway.get_arg('description')
        class_name = gateway.get_arg('class_name')
        status = gateway.get_arg('status') or 'todo'
        
        if not description:
            warn("Description is required")
            report_error("action", "Description is required")
            trace_out()
            return False
        
        if not class_name:
            warn("Class name is required")
            report_error("action", "Class name is required")
            trace_out()
            return False
        
        with get_legacy_db_connection() as legacy_conn:
            cursor = legacy_conn.cursor()
            
            # Insert new phase (phase_number will auto-increment)
            cursor.execute("""
                INSERT INTO migration (description, class_name, status, num_legacy, num_new, num_errors)
                VALUES (%s, %s, %s, 0, 0, 0)
            """, (description, class_name, status))
            
            phase_number = cursor.lastrowid
            legacy_conn.commit()
            
            payload = {
                "operation": "migration_add_phase",
                "phase_number": phase_number,
                "description": description,
                "class_name": class_name,
                "status": status
            }
            gateway.response.set_action_response(success_payload(payload))
            log(f"Added migration phase {phase_number}: {description} ({class_name})")
            trace_out()
            return not is_error()
            
    except Exception as e:
        warn(f"Migration add phase error: {e}")
        report_error("action", f"Migration add phase error: {e}")
        trace_out()
        return False


@register_parser("migration_add_phase")
def migration_add_phase_parser() -> bool:
    """Parse and display migration add phase results."""
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
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})
        
        phase_number = source_data.get("phase_number")
        description = source_data.get("description")
        class_name = source_data.get("class_name")
        status = source_data.get("status")
        
        lines = [render_header_block("l_migration_add_phase_header")]
        
        if phase_number:
            table = TableData()
            table.add_row("header", label="Field", value="Value")
            table.add_row("phase", label="Phase Number", value=str(phase_number))
            table.add_row("description", label="Description", value=description or "")
            table.add_row("class", label="Class Name", value=class_name or "")
            table.add_row("status", label="Status", value=status or "")
            
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["phase", "description", "class", "status"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        else:
            lines.append("Failed to add phase")
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration add phase parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration add phase parser error: {e}")
        report_error("backend", f"Migration add phase parser error: {e}")
        trace_out()
        return False


register_maintenance_tool("migration_add_phase")


