"""Migration daemon action for migrating data from legacy database."""

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
from accounting.deploy.maint.migration_tasks import migrate_pages, migrate_accounts, migrate_statements, migrate_expense_categories, migrate_invoices, migrate_sales, migrate_fiscal_periods, migrate_fees, migrate_transfers, migrate_text, migrate_images, migrate_no_images, migrate_no_text, migrate_no_calc, migrate_calc

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


def _process_migration_phase(cursor, legacy_conn, phase: Dict[str, Any], batch_size: int, rerun_errors: bool = False) -> Dict[str, Any]:
    """Process a single migration phase.
    
    Args:
        cursor: Legacy database cursor
        legacy_conn: Legacy database connection
        phase: Phase dictionary from migration table
        batch_size: Number of items to process per batch
        rerun_errors: Whether this is a rerun-errors operation
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        trace_out()
        return {"error": "No gateway available"}
    
    phase_number = phase['phase_number']
    class_name = phase['class_name']
    
    # Check for special migration types (not class names)
    if class_name == 'no_images':
        # Special case: mark pages with no images (one-shot operation)
        result = migrate_no_images(legacy_conn, batch_size=batch_size)
        # If successful and has_more is False, mark phase as done immediately
        if "error" not in result and not result.get("has_more", True):
            cursor.execute("""
                UPDATE migration
                SET status = 'done'
                WHERE phase_number = %s
            """, (phase_number,))
            legacy_conn.commit()
            log(f"Phase {phase_number} (no_images) completed - set status to 'done'")
    elif class_name == 'no_text':
        # Special case: mark pages with no text (one-shot operation)
        result = migrate_no_text(legacy_conn, batch_size=batch_size)
        # If successful and has_more is False, mark phase as done immediately
        if "error" not in result and not result.get("has_more", True):
            cursor.execute("""
                UPDATE migration
                SET status = 'done'
                WHERE phase_number = %s
            """, (phase_number,))
            legacy_conn.commit()
            log(f"Phase {phase_number} (no_text) completed - set status to 'done'")
    elif class_name == 'text':
        # Special case: migrate page text
        result = migrate_text(legacy_conn, batch_size=batch_size)
    elif class_name == 'images':
        # Special case: migrate images
        result = migrate_images(legacy_conn, batch_size=batch_size)
    elif class_name == 'no_calc':
        # Special case: mark pages with no calculated values (one-shot operation)
        result = migrate_no_calc(legacy_conn, batch_size=batch_size)
        # If successful and has_more is False, mark phase as done immediately
        if "error" not in result and not result.get("has_more", True):
            cursor.execute("""
                UPDATE migration
                SET status = 'done'
                WHERE phase_number = %s
            """, (phase_number,))
            legacy_conn.commit()
            log(f"Phase {phase_number} (no_calc) completed - set status to 'done'")
    elif class_name == 'calc':
        # Special case: recalculate generated values
        result = migrate_calc(legacy_conn, batch_size=batch_size)
    else:
        # Regular class-based migration
        # Map class_name to migration function
        migration_functions = {
            'page': migrate_pages,
            'account': migrate_accounts,
            'statement': migrate_statements,
            'expenseCategory': migrate_expense_categories,
            'invoice': migrate_invoices,
            'sale': migrate_sales,
            'fiscalPeriod': migrate_fiscal_periods,
            'fee': migrate_fees,
            'transfer': migrate_transfers,
        }
        
        if class_name not in migration_functions:
            warn(f"Unknown migration class: {class_name}")
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "has_more": False,
                "error": f"Unknown migration class: {class_name}"
            }
        
        # Run the appropriate migration function
        migrate_func = migration_functions[class_name]
        result = migrate_func(legacy_conn, batch_size=batch_size)
    
    if "error" in result:
        trace_out()
        return result
    
    # Update phase statistics
    migrated = result.get("migrated", 0)
    skipped = result.get("skipped", 0)
    errors = result.get("errors", 0)
    
    # Get current counts - special handling for non-class migrations
    if class_name in ('text', 'images', 'no_images', 'no_text'):
        # For special migrations, we don't count by class
        # Use placeholder counts for now
        legacy_total = 0
        new_total = 0
    else:
        # Get current counts from legacy database for this class
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM pages
            WHERE class = %s
        """, (class_name,))
        legacy_total = cursor.fetchone()['total']
        
        # Get current counts from new database for this class
        new_total = gateway.conn.read("""
            SELECT COUNT(*) as total
            FROM pages
            WHERE class = %s
        """, (class_name,))[0]['total']
    
    # Update phase with new statistics
    cursor.execute("""
        UPDATE migration
        SET num_legacy = %s,
            num_new = %s,
            num_errors = num_errors + %s
        WHERE phase_number = %s
    """, (legacy_total, new_total, errors, phase_number))
    
    # If no more items to migrate, check if we should set status to 'error' or 'done'
    if not result.get("has_more", True):
        # Get current error count after update
        cursor.execute("""
            SELECT num_errors
            FROM migration
            WHERE phase_number = %s
        """, (phase_number,))
        current_errors = cursor.fetchone()['num_errors']
        
        # If there are any errors, set status to 'error', otherwise 'done'
        # This applies whether it's a normal run or a rerun-errors run
        if current_errors > 0:
            cursor.execute("""
                UPDATE migration
                SET status = 'error'
                WHERE phase_number = %s
            """, (phase_number,))
            log(f"Phase {phase_number} ({class_name}) completed with {current_errors} errors - setting status to 'error'")
        else:
            cursor.execute("""
                UPDATE migration
                SET status = 'done'
                WHERE phase_number = %s
            """, (phase_number,))
            if rerun_errors:
                log(f"Phase {phase_number} ({class_name}) rerun completed with no errors - setting status to 'done'")
            else:
                log(f"Phase {phase_number} ({class_name}) completed - setting status to 'done'")
    
    trace_out()
    return result


@register_action("migration_daemon")
@register_command("migration_daemon")
def migration_daemon_action() -> bool:
    """Run migration daemon cycle - migrate pages from legacy database.
    
    Optional arguments:
    --batch_size: Number of pages to process (default: 1 for single-shot, 100 for daemon)
    --rerun-errors or --rerun_errors: If set, process ALL phases with 'error' status in one cycle (zeros out num_errors for each phase first)
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    
    # Get batch_size from arguments, default to 1 for single-shot testing
    batch_size = gateway.get_arg("batch_size")
    if batch_size:
        try:
            batch_size = int(batch_size)
        except (ValueError, TypeError):
            batch_size = 1
    else:
        batch_size = 1  # Default to 1 for single-shot testing
    
    # Check if we should rerun error phases
    rerun_errors = gateway.get_arg("rerun_errors") or gateway.get_arg("rerun-errors")
    if rerun_errors:
        if isinstance(rerun_errors, str):
            rerun_errors = rerun_errors.lower() in ('true', '1', 'yes', 'on')
        else:
            rerun_errors = bool(rerun_errors)
    else:
        rerun_errors = False
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            cursor = legacy_conn.cursor()
            
            # Check migration table for active phase
            if rerun_errors:
                # For rerun-errors, process ALL phases with status 'error'
                cursor.execute("""
                    SELECT phase_number, description, class_name, status, num_legacy, num_new, num_errors
                    FROM migration
                    WHERE status = 'error'
                    ORDER BY phase_number
                """)
                error_phases = cursor.fetchall()
                
                if not error_phases:
                    # No error phases, return empty result
                    result = {
                        "migrated": 0,
                        "skipped": 0,
                        "errors": 0,
                        "has_more": False,
                        "message": "No migration phases with status 'error'"
                    }
                    payload = {
                        "operation": "migration_daemon",
                        "result": result
                    }
                    gateway.response.set_action_response(success_payload(payload))
                    log("Migration daemon: No error phases to rerun")
                    trace_out()
                    return True
                
                # Process all error phases
                total_migrated = 0
                total_skipped = 0
                total_errors = 0
                phases_processed = []
                
                for phase in error_phases:
                    phase_number = phase['phase_number']
                    class_name = phase['class_name']
                    
                    # Zero out num_errors before processing
                    cursor.execute("""
                        UPDATE migration
                        SET num_errors = 0
                        WHERE phase_number = %s
                    """, (phase_number,))
                    log(f"Zeroed out num_errors for phase {phase_number} ({class_name}) before rerun")
                    
                    # Process this phase
                    phase_result = _process_migration_phase(
                        cursor, legacy_conn, phase, batch_size, rerun_errors=True
                    )
                    
                    if "error" in phase_result:
                        warn(f"Migration error for phase {phase_number}: {phase_result['error']}")
                        continue
                    
                    total_migrated += phase_result.get("migrated", 0)
                    total_skipped += phase_result.get("skipped", 0)
                    total_errors += phase_result.get("errors", 0)
                    phases_processed.append({
                        "phase_number": phase_number,
                        "class_name": class_name,
                        "description": phase['description']
                    })
                
                legacy_conn.commit()
                
                result = {
                    "migrated": total_migrated,
                    "skipped": total_skipped,
                    "errors": total_errors,
                    "has_more": False,  # All error phases processed in one cycle
                    "phases_processed": phases_processed,
                    "message": f"Processed {len(phases_processed)} error phase(s)"
                }
                
                payload = {
                    "operation": "migration_daemon",
                    "result": result
                }
                gateway.response.set_action_response(success_payload(payload))
                log(f"Migration daemon rerun-errors: processed {len(phases_processed)} phase(s), {total_migrated} migrated, {total_skipped} skipped, {total_errors} errors")
                trace_out()
                return not is_error()
            else:
                # Normal mode: find the first phase with status 'doing'
                cursor.execute("""
                    SELECT phase_number, description, class_name, status, num_legacy, num_new, num_errors
                    FROM migration
                    WHERE status = 'doing'
                    AND phase_number = (
                        SELECT MIN(phase_number)
                        FROM migration
                        WHERE status = 'doing'
                    )
                    ORDER BY phase_number
                    LIMIT 1
                """)
                
                phase = cursor.fetchone()
                
                if not phase:
                    # No active phase, return empty result
                    result = {
                        "migrated": 0,
                        "skipped": 0,
                        "errors": 0,
                        "has_more": False,
                        "message": "No active migration phase with status 'doing'"
                    }
                    payload = {
                        "operation": "migration_daemon",
                        "result": result
                    }
                    gateway.response.set_action_response(success_payload(payload))
                    log("Migration daemon: No active phase with status 'doing'")
                    trace_out()
                    return True
                
                # Process single phase
                result = _process_migration_phase(cursor, legacy_conn, phase, batch_size, rerun_errors=False)
                
                if "error" in result:
                    warn(f"Migration error: {result['error']}")
                    report_error("action", f"Migration error: {result['error']}")
                    trace_out()
                    return False
                
                legacy_conn.commit()
                
                # Add phase info to result
                result["phase_number"] = phase['phase_number']
                result["class_name"] = phase['class_name']
                result["description"] = phase['description']
                
                payload = {
                    "operation": "migration_daemon",
                    "result": result
                }
                gateway.response.set_action_response(success_payload(payload))
                migrated = result.get("migrated", 0)
                skipped = result.get("skipped", 0)
                errors = result.get("errors", 0)
                log(f"Migration daemon phase {phase['phase_number']} ({phase['class_name']}): {migrated} migrated, {skipped} skipped, {errors} errors")
                trace_out()
                return not is_error()
            
    except Exception as e:
        warn(f"Migration daemon error: {e}")
        report_error("action", f"Migration daemon error: {e}")
        trace_out()
        return False


@register_parser("migration_daemon")
def migration_daemon_parser() -> bool:
    """Parse and display migration daemon results."""
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
        result = source_data.get("result", {})
        
        lines = [render_header_block("l_migration_daemon_header")]
        
        if "error" in result:
            lines.append(f"Error: {result['error']}")
        else:
            table = TableData()
            table.add_row(
                "header",
                label="Result",
                value="Value"
            )
            
            migrated = result.get("migrated", 0)
            skipped = result.get("skipped", 0)
            errors = result.get("errors", 0)
            account_migrated = result.get("account_migrated", 0)
            account_skipped = result.get("account_skipped", 0)
            account_errors = result.get("account_errors", 0)
            links_set = result.get("links_set", 0)
            link_errors = result.get("link_errors", 0)
            statement_migrated = result.get("statement_migrated", 0)
            statement_skipped = result.get("statement_skipped", 0)
            statement_errors = result.get("statement_errors", 0)
            
            table.add_row("migrated", label="Pages Migrated", value=str(migrated))
            table.add_row("skipped", label="Pages Skipped", value=str(skipped))
            table.add_row("errors", label="Errors", value=str(errors))
            
            # Add account migration results if present
            if account_migrated > 0 or account_skipped > 0 or account_errors > 0:
                table.add_row("account_migrated", label="Accounts Migrated", value=str(account_migrated))
                table.add_row("account_skipped", label="Accounts Skipped", value=str(account_skipped))
                table.add_row("account_errors", label="Account Errors", value=str(account_errors))
            
            # Add account link setting results if present
            if links_set > 0 or link_errors > 0:
                table.add_row("links_set", label="Account Links Set", value=str(links_set))
                table.add_row("link_errors", label="Link Errors", value=str(link_errors))
            
            # Add statement migration results if present (currently disabled)
            if statement_migrated > 0 or statement_skipped > 0 or statement_errors > 0:
                table.add_row("statement_migrated", label="Statements Migrated", value=str(statement_migrated))
                table.add_row("statement_skipped", label="Statements Skipped", value=str(statement_skipped))
                table.add_row("statement_errors", label="Statement Errors", value=str(statement_errors))
            
            if errors > 0 and "error_details" in result:
                error_details = result.get("error_details", [])
                if error_details:
                    lines.append("")
                    lines.append("Error Details:")
                    for error in error_details[:5]:  # Show first 5 errors
                        lines.append(f"  - {error}")
            
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["migrated", "skipped", "errors", "account_migrated", "account_skipped", "account_errors", "statement_migrated", "statement_skipped", "statement_errors"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration daemon parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration daemon parser error: {e}")
        report_error("backend", f"Migration daemon parser error: {e}")
        trace_out()
        return False


register_maintenance_tool("migration_daemon")

