"""Migration double check action for checking pages in new system without legacy links."""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block
from ext.deploy.maint.migration_tasks import get_migration_double_check, get_migration_images_double_check, get_migration_text_double_check, repair_migration_issues

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


@register_action("migration_double_check")
@register_command("migration_double_check")
def migration_double_check_action() -> bool:
    """Get migration double check results - pages in new system without legacy links.
    
    Optional parameters:
    - repair: If true, repair issues found (default: false)
    - repair_limit: Maximum number of repairs to perform (default: 100)
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    try:
        # Check if repair mode is enabled
        repair_arg = gateway.get_arg('repair')
        repair = repair_arg if repair_arg else False
        if isinstance(repair, str):
            repair = repair.lower() in ('true', '1', 'yes', 'on')
        
        repair_limit_arg = gateway.get_arg('repair_limit')
        repair_limit = int(repair_limit_arg) if repair_limit_arg else 1
        
        # Get phase_number (required)
        phase_number_arg = gateway.get_arg('phase_number') or gateway.get_arg('phase')
        if not phase_number_arg:
            warn("Phase number is required")
            report_error("action", "Phase number is required")
            trace_out()
            return False
        
        try:
            phase_number = int(phase_number_arg)
        except ValueError:
            warn(f"Invalid phase number: {phase_number_arg}")
            report_error("action", "Phase number must be a number")
            trace_out()
            return False
        
        # Get class_name from migration table
        from ext.deploy.maint.legacy_db_connection import get_legacy_db_connection
        with get_legacy_db_connection() as legacy_conn:
            cursor = legacy_conn.cursor()
            cursor.execute("""
                SELECT phase_number, description, class_name
                FROM migration
                WHERE phase_number = %s
            """, (phase_number,))
            phase = cursor.fetchone()
            
            if not phase:
                warn(f"Phase {phase_number} not found in migration table")
                report_error("action", f"Phase {phase_number} not found")
                trace_out()
                return False
            
            type_filter = phase['class_name']
        
        # Special handling for non-class-based migrations
        if type_filter == 'text':
            # For text migration, check for pages missing text migration
            result = get_migration_text_double_check()
            
            if "error" in result:
                warn(f"Failed to get migration text double check: {result['error']}")
                report_error("action", f"Failed to get migration text double check: {result['error']}")
                trace_out()
                return False
            
            repair_result = None  # No repair for text yet
        elif type_filter == 'no_text':
            # For no_text phase, return empty results (no orphan checks needed)
            # Counts will be calculated separately below
            result = {
                "new_orphans": [],
                "new_orphan_count": 0,
                "legacy_orphans": [],
                "legacy_orphan_count": 0,
                "data_mismatches": [],
                "mismatch_count": 0,
                "missing_text_pages": [],
                "missing_text_count": 0
            }
            repair_result = None
        elif type_filter == 'images':
            # For images migration, do two-way orphan check
            result = get_migration_images_double_check()
            
            if "error" in result:
                warn(f"Failed to get migration images double check: {result['error']}")
                report_error("action", f"Failed to get migration images double check: {result['error']}")
                trace_out()
                return False
            
            # If repair mode, perform repairs
            repair_result = None
            if repair:
                repair_result = repair_migration_issues(repair_limit=repair_limit, type_filter='images')
                if repair_result and "error" in repair_result:
                    warn(f"Repair error: {repair_result['error']}")
                    # Don't fail, just log the error
                elif repair_result:
                    result["repairs_made"] = repair_result.get("repairs_made", 0)
                    result["repair_errors"] = repair_result.get("errors", 0)
                    result["repair_has_more"] = repair_result.get("has_more", False)
                    log(f"Image repairs: {repair_result.get('repairs_made', 0)} made, {repair_result.get('errors', 0)} errors")
                    
                    # After repairs, re-check to get updated counts
                    result = get_migration_images_double_check()
        else:
            # Get check results for class-based migrations
            result = get_migration_double_check(type_filter=type_filter)
            
            if "error" in result:
                warn(f"Failed to get migration double check: {result['error']}")
                report_error("action", f"Failed to get migration double check: {result['error']}")
                trace_out()
                return False
            
            # If repair mode, perform repairs
            repair_result = None
            if repair:
                repair_result = repair_migration_issues(repair_limit=repair_limit, type_filter=type_filter)
                if repair_result and "error" in repair_result:
                    warn(f"Repair error: {repair_result['error']}")
                    # Don't fail, just log the error
                elif repair_result:
                    result["repairs_made"] = repair_result.get("repairs_made", 0)
                    result["repair_errors"] = repair_result.get("errors", 0)
                    result["repair_has_more"] = repair_result.get("has_more", False)
                    log(f"Repairs: {repair_result.get('repairs_made', 0)} made, {repair_result.get('errors', 0)} errors")
                    
                    # After repairs, re-check to get updated counts
                    result = get_migration_double_check(type_filter=type_filter)
        
        # Update migration table with counts
        from ext.deploy.maint.legacy_db_connection import get_legacy_db_connection
        with get_legacy_db_connection() as legacy_conn:
            update_cursor = legacy_conn.cursor()
            
            # Special handling for non-class-based migrations
            if type_filter == 'text':
                # Get counts from legacy database for pages with text
                update_cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM pages
                    WHERE text IS NOT NULL
                    AND text != ''
                    AND new_id IS NOT NULL
                """)
                legacy_total = update_cursor.fetchone()['total']
                
                # Get counts from new database for pages with text
                new_total = gateway.conn.read("""
                    SELECT COUNT(*) as total
                    FROM pages
                    WHERE text IS NOT NULL
                    AND text != ''
                """, [])[0]['total']
            elif type_filter == 'no_text':
                # Get counts from legacy database for pages with no text
                update_cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM pages
                    WHERE text IS NULL OR text = ''
                """)
                legacy_total = update_cursor.fetchone()['total']
                
                # Get counts from new database for pages with no text
                new_total = gateway.conn.read("""
                    SELECT COUNT(*) as total
                    FROM pages
                    WHERE text IS NULL OR text = ''
                """, [])[0]['total']
            elif type_filter == 'images':
                # Get counts from legacy database for images
                update_cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM images
                    WHERE new_id IS NOT NULL
                """)
                legacy_total = update_cursor.fetchone()['total']
                
                # Get counts from new database for images
                new_total = gateway.conn.read("""
                    SELECT COUNT(*) as total
                    FROM images
                """, [])[0]['total']
            else:
                # Get counts from legacy database for this class
                update_cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM pages
                    WHERE class = %s
                """, (type_filter,))
                legacy_total = update_cursor.fetchone()['total']
                
                # Get counts from new database for this class
                new_total = gateway.conn.read("""
                    SELECT COUNT(*) as total
                    FROM pages
                    WHERE class = %s
                """, (type_filter,))[0]['total']
            
            # Calculate total errors (orphans + mismatches + missing text)
            new_orphan_count_val = result.get("new_orphan_count", 0)
            legacy_orphan_count_val = result.get("legacy_orphan_count", 0)
            mismatch_count_val = result.get("mismatch_count", 0)
            missing_text_count_val = result.get("missing_text_count", 0)
            # Type conversion: ensure values are integers
            new_orphan_count = int(new_orphan_count_val) if isinstance(new_orphan_count_val, (int, float, str)) else 0
            legacy_orphan_count = int(legacy_orphan_count_val) if isinstance(legacy_orphan_count_val, (int, float, str)) else 0
            mismatch_count = int(mismatch_count_val) if isinstance(mismatch_count_val, (int, float, str)) else 0
            missing_text_count = int(missing_text_count_val) if isinstance(missing_text_count_val, (int, float, str)) else 0
            total_errors = new_orphan_count + legacy_orphan_count + mismatch_count + missing_text_count
            
            # Update migration table
            update_cursor.execute("""
                UPDATE migration
                SET num_legacy = %s,
                    num_new = %s,
                    num_errors = %s
                WHERE phase_number = %s
            """, (legacy_total, new_total, total_errors, phase_number))
            
            legacy_conn.commit()
            
            result["phase_number"] = phase_number
            result["num_legacy"] = legacy_total
            result["num_new"] = new_total
            result["num_errors"] = total_errors
            result["missing_text_count"] = missing_text_count
        
        payload = {
            "operation": "migration_double_check",
            "phase_number": phase_number,
            "class_name": type_filter,
            "new_orphans": result.get("new_orphans", []),
            "new_orphan_count": result.get("new_orphan_count", 0),
            "legacy_orphans": result.get("legacy_orphans", []),
            "legacy_orphan_count": result.get("legacy_orphan_count", 0),
            "data_mismatches": result.get("data_mismatches", []),
            "mismatch_count": result.get("mismatch_count", 0),
            "missing_text_pages": result.get("missing_text_pages", []),
            "missing_text_count": result.get("missing_text_count", 0),
            "repairs_made": result.get("repairs_made", 0),
            "repair_errors": result.get("repair_errors", 0),
            "repair_has_more": result.get("repair_has_more", False),
            "num_legacy": result.get("num_legacy", 0),
            "num_new": result.get("num_new", 0),
            "num_errors": result.get("num_errors", 0)
        }
        gateway.response.set_action_response(success_payload(payload))
        log("Migration double check retrieved successfully")
        trace_out()
        return not is_error()
        
    except Exception as e:
        warn(f"Migration double check error: {e}")
        report_error("action", f"Migration double check error: {e}")
        trace_out()
        return False


@register_parser("migration_double_check")
def migration_double_check_parser() -> bool:
    """Parse and display migration double check results."""
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
        class_name = source_data.get("class_name")
        new_orphans = source_data.get("new_orphans", [])
        new_orphan_count = source_data.get("new_orphan_count", 0)
        legacy_orphans = source_data.get("legacy_orphans", [])
        legacy_orphan_count = source_data.get("legacy_orphan_count", 0)
        data_mismatches = source_data.get("data_mismatches", [])
        mismatch_count = source_data.get("mismatch_count", 0)
        missing_text_pages = source_data.get("missing_text_pages", [])
        missing_text_count = source_data.get("missing_text_count", 0)
        repairs_made = source_data.get("repairs_made", 0)
        repair_errors = source_data.get("repair_errors", 0)
        num_legacy = source_data.get("num_legacy", 0)
        num_new = source_data.get("num_new", 0)
        num_errors = source_data.get("num_errors", 0)
        
        lines = [render_header_block("l_migration_double_check_header")]
        
        total_issues = new_orphan_count + legacy_orphan_count + mismatch_count + missing_text_count
        
        # Phase info table
        if phase_number:
            phase_table = TableData()
            phase_table.add_row("header", label="Field", value="Value")
            phase_table.add_row("phase", label="Phase Number", value=str(phase_number))
            phase_table.add_row("class", label="Class Name", value=class_name or "")
            phase_table.add_row("legacy", label="Legacy Count", value=str(num_legacy))
            phase_table.add_row("new", label="New Count", value=str(num_new))
            phase_table.add_row("errors", label="Total Errors", value=str(num_errors))
            
            lines.append(
                render_block(
                    phase_table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["phase", "class", "legacy", "new", "errors"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
            lines.append("")
        
        # Summary table
        summary_table = TableData()
        summary_table.add_row(
            "header",
            label="Check Type",
            count="Count"
        )
        summary_table.add_row("new_orphans", label="New pages without legacy links", count=str(new_orphan_count))
        summary_table.add_row("legacy_orphans", label="Legacy pages without new entries", count=str(legacy_orphan_count))
        summary_table.add_row("mismatches", label="Data mismatches", count=str(mismatch_count))
        summary_table.add_row("missing_text", label="Pages missing text migration", count=str(missing_text_count))
        summary_table.add_row("total", label="Total issues", count=str(total_issues))
        
        # Add repair results if repairs were made
        if repairs_made > 0 or repair_errors > 0:
            summary_table.add_row("repairs", label="Repairs made", count=str(repairs_made))
            summary_table.add_row("repair_errors", label="Repair errors", count=str(repair_errors))
        
        lines.append(
            render_block(
                summary_table,
                FieldConfig()
                    .add_header("header")
                    .add_simple(["new_orphans", "legacy_orphans", "mismatches", "missing_text", "total", "repairs", "repair_errors"]),
                block_type="maintenance",
                table_overrides={"margin_l": 4}
            )
        )
        
        # New system orphans table
        if new_orphan_count > 0:
            lines.append("")
            new_orphan_table = TableData()
            new_orphan_table.add_row(
                "header",
                label=f"New Pages Without Legacy Links ({new_orphan_count})",
                id="ID",
                name="Name",
                class_name="Class"
            )
            
            for page in new_orphans[:50]:
                new_orphan_table.add_row(
                    "orphan",
                    id=str(page.get('id', '?')),
                    name=page.get('name') or '(null)',
                    class_name=page.get('class', 'page')
                )
            
            if len(new_orphans) > 50:
                new_orphan_table.add_row(
                    "more",
                    id=f"... ({len(new_orphans) - 50} more)",
                    name="",
                    class_name=""
                )
            
            lines.append(
                render_block(
                    new_orphan_table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["orphan", "more"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        
        # Legacy system orphans table
        if legacy_orphan_count > 0:
            lines.append("")
            legacy_orphan_table = TableData()
            legacy_orphan_table.add_row(
                "header",
                label=f"Legacy Pages Without New Entries ({legacy_orphan_count})",
                legacy_id="Legacy ID",
                new_id="New ID",
                name="Name",
                class_name="Class"
            )
            
            for page in legacy_orphans[:50]:
                legacy_orphan_table.add_row(
                    "orphan",
                    legacy_id=str(page.get('legacy_id', '?')),
                    new_id=str(page.get('new_id', '?')),
                    name=page.get('name') or '(null)',
                    class_name=page.get('class', 'page')
                )
            
            if len(legacy_orphans) > 50:
                legacy_orphan_table.add_row(
                    "more",
                    legacy_id=f"... ({len(legacy_orphans) - 50} more)",
                    new_id="",
                    name="",
                    class_name=""
                )
            
            lines.append(
                render_block(
                    legacy_orphan_table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["orphan", "more"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        
        # Data mismatches table
        if mismatch_count > 0:
            lines.append("")
            mismatch_table = TableData()
            mismatch_table.add_row(
                "header",
                label=f"Data Mismatches ({mismatch_count})",
                id="New ID",
                legacy_id="Legacy ID",
                field="Field",
                legacy_value="Legacy Value",
                new_value="New Value"
            )
            
            for mismatch in data_mismatches[:50]:
                mismatch_table.add_row(
                    "mismatch",
                    id=str(mismatch.get('id', '?')),
                    legacy_id=str(mismatch.get('legacy_id', '?')),
                    field=mismatch.get('field', '?'),
                    legacy_value=mismatch.get('legacy_value', ''),
                    new_value=mismatch.get('new_value', '')
                )
            
            if len(data_mismatches) > 50:
                mismatch_table.add_row(
                    "more",
                    id=f"... ({len(data_mismatches) - 50} more)",
                    legacy_id="",
                    field="",
                    legacy_value="",
                    new_value=""
                )
            
            lines.append(
                render_block(
                    mismatch_table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["mismatch", "more"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        
        # Missing text pages table
        if missing_text_count > 0:
            lines.append("")
            missing_text_table = TableData()
            missing_text_table.add_row(
                "header",
                label=f"Pages Missing Text Migration ({missing_text_count})",
                legacy_id="Legacy ID",
                new_id="New ID",
                name="Name",
                class_name="Class"
            )
            
            for page in missing_text_pages[:50]:
                missing_text_table.add_row(
                    "missing_text",
                    legacy_id=str(page.get('legacy_id', '?')),
                    new_id=str(page.get('new_id', '?')),
                    name=page.get('name') or '(null)',
                    class_name=page.get('class', 'page')
                )
            
            if len(missing_text_pages) > 50:
                missing_text_table.add_row(
                    "more",
                    legacy_id=f"... ({len(missing_text_pages) - 50} more)",
                    new_id="",
                    name="",
                    class_name=""
                )
            
            lines.append(
                render_block(
                    missing_text_table,
                    FieldConfig()
                        .add_header("header")
                        .add_simple(["missing_text", "more"]),
                    block_type="maintenance",
                    table_overrides={"margin_l": 4}
                )
            )
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration double check parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration double check parser error: {e}")
        report_error("backend", f"Migration double check parser error: {e}")
        trace_out()
        return False


register_maintenance_tool("migration_double_check")

