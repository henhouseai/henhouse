"""Migration orphan check action for checking orphaned records in legacy database."""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block
from ext.deploy.maint.migration_tasks import get_migration_orphan_checks

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


@register_action("migration_orphan_check")
@register_command("migration_orphan_check")
def migration_orphan_check_action() -> bool:
    """Get migration orphan check results from legacy database."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    try:
        result = get_migration_orphan_checks()
        
        if "error" in result:
            warn(f"Failed to get migration orphan checks: {result['error']}")
            report_error("action", f"Failed to get migration orphan checks: {result['error']}")
            trace_out()
            return False
        
        payload = {
            "operation": "migration_orphan_check",
            "orphans": result.get("orphans", {}),
            "orphan_summary": result.get("orphan_summary", {})
        }
        gateway.response.set_action_response(success_payload(payload))
        log("Migration orphan check retrieved successfully")
        trace_out()
        return not is_error()
        
    except Exception as e:
        warn(f"Migration orphan check error: {e}")
        report_error("action", f"Migration orphan check error: {e}")
        trace_out()
        return False


@register_parser("migration_orphan_check")
def migration_orphan_check_parser() -> bool:
    """Parse and display migration orphan check results."""
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
        orphans = source_data.get("orphans", {})
        orphan_summary = source_data.get("orphan_summary", {})
        
        lines = [render_header_block("l_orphan_check_header")]
        
        # Orphan check table - always show, even if all zeros
        total_orphans = sum(orphan_summary.values())
        
        orphan_table = TableData()
        has_orphans = total_orphans > 0
        
        # Add header row - conditionally show IDs column
        if has_orphans:
            orphan_table.add_row(
                "header",
                label=f"{total_orphans} orphan{'s' if total_orphans != 1 else ''}",
                count="Count",
                ids="IDs"
            )
        else:
            orphan_table.add_row(
                "header",
                label="0 orphans",
                count="Count"
            )
        
        # Add all orphan check rows, even if count is 0
        for key in orphans.keys():
            count = orphan_summary.get(key, 0)
            ids_list = orphans.get(key, [])
            preview = ""
            
            if has_orphans and count > 0:
                if key == "unexpected_page_classes":
                    # Handle unexpected_page_classes which is a list of dicts
                    if isinstance(ids_list, list) and len(ids_list) > 0:
                        preview_items = ids_list[:10]
                        preview = ", ".join(f"{item.get('id', '?')}({item.get('class', '?')})" for item in preview_items)
                        if len(ids_list) > 10:
                            preview += f" ... ({len(ids_list)} total)"
                elif isinstance(ids_list, list):
                    # Handle regular ID lists
                    preview_ids = ids_list[:20]
                    preview = ", ".join(str(val) for val in preview_ids) if preview_ids else ""
                    if len(ids_list) > 20:
                        preview += f" ... ({len(ids_list)} total)"
            
            if has_orphans:
                orphan_table.add_row(
                    key,
                    count=str(count),
                    ids=preview
                )
            else:
                orphan_table.add_row(
                    key,
                    count=str(count)
                )
        
        lines.append(
            render_block(
                orphan_table,
                FieldConfig()
                    .add_header("header")
                    .add_simple(list(orphans.keys())),
                block_type="maintenance",
                table_overrides={"margin_l": 4}
            )
        )
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration orphan check parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration orphan check parser error: {e}")
        report_error("backend", f"Migration orphan check parser error: {e}")
        trace_out()
        return False


