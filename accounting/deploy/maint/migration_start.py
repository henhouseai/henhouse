"""Migration start action to set migration phases to 'doing' status."""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block
from accounting.deploy.maint.legacy_db_connection import get_legacy_db_connection

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


@register_action("migration_start")
@register_command("migration_start")
def migration_start_action() -> bool:
    """Start migration by setting the first 'todo' phase to 'doing'."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            cursor = legacy_conn.cursor()
            
            # Find the first phase with status 'todo' that has no earlier phases in 'doing' or 'todo'
            cursor.execute("""
                SELECT phase_number, description, class_name
                FROM migration
                WHERE status = 'todo'
                AND phase_number = (
                    SELECT MIN(phase_number)
                    FROM migration
                    WHERE status IN ('todo', 'doing')
                )
                ORDER BY phase_number
                LIMIT 1
            """)
            
            phase = cursor.fetchone()
            
            if not phase:
                warn("No phases available to start (all phases are done or in review)")
                report_error("action", "No phases available to start")
                trace_out()
                return False
            
            phase_number = phase['phase_number']
            
            # Set this phase to 'doing'
            cursor.execute("""
                UPDATE migration
                SET status = 'doing'
                WHERE phase_number = %s
            """, (phase_number,))
            
            legacy_conn.commit()
            
            payload = {
                "operation": "migration_start",
                "phase_number": phase_number,
                "description": phase['description'],
                "class_name": phase['class_name']
            }
            gateway.response.set_action_response(success_payload(payload))
            log(f"Started migration phase {phase_number}: {phase['description']} ({phase['class_name']})")
            trace_out()
            return not is_error()
            
    except Exception as e:
        warn(f"Migration start error: {e}")
        report_error("action", f"Migration start error: {e}")
        trace_out()
        return False


@register_parser("migration_start")
def migration_start_parser() -> bool:
    """Parse and display migration start results."""
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
        
        lines = [render_header_block("l_migration_start_header")]
        
        if phase_number:
            table = TableData()
            table.add_row("header", label="Field", value="Value")
            table.add_row("phase", label="Phase Number", value=str(phase_number))
            table.add_row("description", label="Description", value=description or "")
            table.add_row("class", label="Class Name", value=class_name or "")
            
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["phase", "description", "class"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        else:
            lines.append("No phase started")
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration start parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration start parser error: {e}")
        report_error("backend", f"Migration start parser error: {e}")
        trace_out()
        return False


register_maintenance_tool("migration_start")


