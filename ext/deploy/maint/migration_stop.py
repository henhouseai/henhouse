"""Migration stop action to set all 'doing' phases to 'todo' status."""

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


@register_action("migration_stop")
@register_command("migration_stop")
def migration_stop_action() -> bool:
    """Stop migration by setting all 'doing' phases back to 'todo'."""
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
            
            # Find all phases with status 'doing'
            cursor.execute("""
                SELECT phase_number, description, class_name
                FROM migration
                WHERE status = 'doing'
                ORDER BY phase_number
            """)
            
            phases = cursor.fetchall()
            
            if not phases:
                warn("No phases currently in 'doing' status")
                # Not an error, just nothing to stop
                payload = {
                    "operation": "migration_stop",
                    "phases_stopped": 0
                }
                gateway.response.set_action_response(success_payload(payload))
                trace_out()
                return True
            
            # Set all 'doing' phases back to 'todo'
            cursor.execute("""
                UPDATE migration
                SET status = 'todo'
                WHERE status = 'doing'
            """)
            
            legacy_conn.commit()
            
            payload = {
                "operation": "migration_stop",
                "phases_stopped": len(phases),
                "phases": [{"phase_number": p['phase_number'], "description": p['description']} for p in phases]
            }
            gateway.response.set_action_response(success_payload(payload))
            log(f"Stopped {len(phases)} migration phase(s)")
            trace_out()
            return not is_error()
            
    except Exception as e:
        warn(f"Migration stop error: {e}")
        report_error("action", f"Migration stop error: {e}")
        trace_out()
        return False


@register_parser("migration_stop")
def migration_stop_parser() -> bool:
    """Parse and display migration stop results."""
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
        
        phases_stopped = source_data.get("phases_stopped", 0)
        phases = source_data.get("phases", [])
        
        lines = [render_header_block("l_migration_stop_header")]
        
        table = TableData()
        table.add_row("header", label="Result", value="Value")
        table.add_row("stopped", label="Phases Stopped", value=str(phases_stopped))
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                    .add_header("header")
                    .add_simple(["stopped"]),
                block_type="maintenance",
                table_overrides={"margin_l": 4}
            )
        )
        
        if phases:
            lines.append("\nStopped Phases:")
            phase_table = TableData()
            phase_table.add_row("header", phase_number="Phase", description="Description")
            for phase in phases:
                phase_table.add_row(
                    "phase",
                    phase_number=str(phase.get('phase_number', '')),
                    description=phase.get('description', '')
                )
            lines.append(
                render_block(
                    phase_table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["phase"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration stop parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration stop parser error: {e}")
        report_error("backend", f"Migration stop parser error: {e}")
        trace_out()
        return False


register_maintenance_tool("migration_stop")


