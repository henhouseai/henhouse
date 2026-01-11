"""Migration status action for checking migration progress."""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block
from ext.deploy.maint.migration_tasks import get_migration_status
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


@register_action("migration_status")
@register_command("migration_status")
def migration_status_action() -> bool:
    """Get migration status from legacy database."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    try:
        status_data = get_migration_status()
        
        if "error" in status_data:
            warn(f"Failed to get migration status: {status_data['error']}")
            report_error("action", f"Failed to get migration status: {status_data['error']}")
            trace_out()
            return False
        
        # Get migration table contents
        migration_phases = []
        try:
            with get_legacy_db_connection() as legacy_conn:
                cursor = legacy_conn.cursor()
                cursor.execute("""
                    SELECT phase_number, description, class_name, num_legacy, num_new, num_errors, status
                    FROM migration
                    ORDER BY phase_number
                """)
                migration_phases = cursor.fetchall()
                
                # Refresh counts for images and text phases (they may be 0 if not processed yet)
                for phase in migration_phases:
                    class_name = phase.get('class_name')
                    phase_number = phase.get('phase_number')
                    
                    if class_name == 'images':
                        # Count images in legacy database
                        cursor.execute("SELECT COUNT(*) as total FROM images")
                        legacy_total = cursor.fetchone()['total']
                        
                        # Count images in new database
                        new_total = gateway.conn.read("SELECT COUNT(*) as total FROM images", [])[0]['total']
                        
                        # Update the phase data with current counts
                        phase['num_legacy'] = legacy_total
                        phase['num_new'] = new_total
                        
                        # Also update in database
                        cursor.execute("""
                            UPDATE migration
                            SET num_legacy = %s, num_new = %s
                            WHERE phase_number = %s
                        """, (legacy_total, new_total, phase_number))
                        
                    elif class_name == 'text':
                        # Count pages with non-null, non-zero text in legacy database
                        cursor.execute("""
                            SELECT COUNT(*) as total
                            FROM pages
                            WHERE text IS NOT NULL AND text != ''
                        """)
                        legacy_total = cursor.fetchone()['total']
                        
                        # Count pages with non-null, non-zero text in new database
                        new_total = gateway.conn.read("""
                            SELECT COUNT(*) as total
                            FROM pages
                            WHERE text IS NOT NULL AND text != ''
                        """, [])[0]['total']
                        
                        # Update the phase data with current counts
                        phase['num_legacy'] = legacy_total
                        phase['num_new'] = new_total
                        
                        # Also update in database
                        cursor.execute("""
                            UPDATE migration
                            SET num_legacy = %s, num_new = %s
                            WHERE phase_number = %s
                        """, (legacy_total, new_total, phase_number))
                        
                    elif class_name == 'no_images':
                        # Count pages with no images in legacy database
                        cursor.execute("""
                            SELECT COUNT(*) as total
                            FROM pages p
                            LEFT JOIN images i ON i.parent = p.id
                            WHERE i.id IS NULL
                        """)
                        legacy_total = cursor.fetchone()['total']
                        
                        # Count pages with no images in new database
                        new_total = gateway.conn.read("""
                            SELECT COUNT(*) as total
                            FROM pages p
                            LEFT JOIN image_groups ig ON ig.page_id = p.id
                            WHERE ig.page_id IS NULL
                        """, [])[0]['total']
                        
                        # Update the phase data with current counts
                        phase['num_legacy'] = legacy_total
                        phase['num_new'] = new_total
                        
                        # Also update in database
                        cursor.execute("""
                            UPDATE migration
                            SET num_legacy = %s, num_new = %s
                            WHERE phase_number = %s
                        """, (legacy_total, new_total, phase_number))
                        
                    elif class_name == 'no_text':
                        # Count pages with empty/null text in legacy database
                        cursor.execute("""
                            SELECT COUNT(*) as total
                            FROM pages
                            WHERE text IS NULL OR text = ''
                        """)
                        legacy_total = cursor.fetchone()['total']
                        
                        # Count pages with empty/null text in new database
                        new_total = gateway.conn.read("""
                            SELECT COUNT(*) as total
                            FROM pages
                            WHERE text IS NULL OR text = ''
                        """, [])[0]['total']
                        
                        # Update the phase data with current counts
                        phase['num_legacy'] = legacy_total
                        phase['num_new'] = new_total
                        
                        # Also update in database
                        cursor.execute("""
                            UPDATE migration
                            SET num_legacy = %s, num_new = %s
                            WHERE phase_number = %s
                        """, (legacy_total, new_total, phase_number))
                
                # Commit the updates
                legacy_conn.commit()
        except Exception as e:
            warn(f"Failed to get migration table: {e}")
            # Don't fail, just log the error
        
        payload = {
            "operation": "migration_status",
            "status": status_data.get("status", {}),
            "status_breakdown": status_data.get("status_breakdown", {}),
            "migration_phases": migration_phases
        }
        gateway.response.set_action_response(success_payload(payload))
        log("Migration status retrieved successfully")
        trace_out()
        return not is_error()
        
    except Exception as e:
        warn(f"Migration status error: {e}")
        report_error("action", f"Migration status error: {e}")
        trace_out()
        return False


@register_parser("migration_status")
def migration_status_parser() -> bool:
    """Parse and display migration status."""
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
        migration_status = source_data.get("status", {})
        status_breakdown = source_data.get("status_breakdown", {})
        
        lines = [render_header_block("l_migration_status_header")]
        
        # Define status columns in order: 0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5
        status_columns = [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5]
        
        # Migration status table
        table = TableData()
        # Build header row with status columns
        header_kwargs = {
            "label": "Table",
            "total": "Total",
            "migrated": "Migrated",
            "remaining": "Remaining",
            "percent": "%"
        }
        # Add status columns to header
        for status_val in status_columns:
            header_kwargs[str(status_val)] = str(status_val)
        table.add_row("header", **header_kwargs)
        
        for table_key, table_status in migration_status.items():
            if isinstance(table_status, dict) and "total" in table_status:
                total = table_status.get("total", 0)
                migrated = table_status.get("migrated", 0)
                remaining = table_status.get("remaining", 0)
                percent = f"{(migrated / total * 100):.1f}%" if total > 0 else "0%"
                
                # Get status breakdown for this class
                breakdown = status_breakdown.get(table_key, {})
                
                # Build row data
                row_kwargs = {
                    "label": table_key,
                    "total": str(total),
                    "migrated": str(migrated),
                    "remaining": str(remaining),
                    "percent": percent
                }
                
                # Add status counts for each status column
                for status_val in status_columns:
                    count = breakdown.get(status_val, 0)
                    row_kwargs[str(status_val)] = str(count)
                
                table.add_row(table_key, **row_kwargs)
        
        # Build field config with all columns
        field_config = FieldConfig().add_header("header")
        for table_key in migration_status.keys():
            field_config.add_simple([table_key])
        
        lines.append(
            render_block(
                table,
                field_config,
                block_type="maintenance",
                table_overrides={"margin_l": 4}
            )
        )
        
        # Migration phases table (from migration table)
        migration_phases = source_data.get("migration_phases", [])
        if migration_phases:
            lines.append("")
            lines.append("Migration Phases:")
            phase_table = TableData()
            phase_table.add_row(
                "header",
                phase_number="Phase",
                description="Description",
                class_name="Class",
                status="Status",
                num_legacy="Legacy",
                num_new="New",
                num_errors="Errors"
            )
            
            for phase in migration_phases:
                phase_table.add_row(
                    "phase",
                    phase_number=str(phase.get('phase_number', '')),
                    description=phase.get('description', ''),
                    class_name=phase.get('class_name', ''),
                    status=phase.get('status', ''),
                    num_legacy=str(phase.get('num_legacy', 0)),
                    num_new=str(phase.get('num_new', 0)),
                    num_errors=str(phase.get('num_errors', 0))
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
        log(f"Migration status parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration status parser error: {e}")
        report_error("backend", f"Migration status parser error: {e}")
        trace_out()
        return False

