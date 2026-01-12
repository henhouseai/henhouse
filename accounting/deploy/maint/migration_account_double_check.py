"""Migration account double check action for checking accounts in new system without legacy links."""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block
from accounting.deploy.maint.migration_tasks import get_migration_account_double_check

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


@register_action("migration_account_double_check")
@register_command("migration_account_double_check")
def migration_account_double_check_action() -> bool:
    """Get migration account double check results - accounts in new system without legacy links."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False
    
    try:
        result = get_migration_account_double_check()
        
        if "error" in result:
            warn(f"Failed to get migration account double check: {result['error']}")
            report_error("action", f"Failed to get migration account double check: {result['error']}")
            trace_out()
            return False
        
        payload = {
            "operation": "migration_account_double_check",
            "new_orphans": result.get("new_orphans", []),
            "new_orphan_count": result.get("new_orphan_count", 0),
            "legacy_orphans": result.get("legacy_orphans", []),
            "legacy_orphan_count": result.get("legacy_orphan_count", 0),
            "data_mismatches": result.get("data_mismatches", []),
            "mismatch_count": result.get("mismatch_count", 0)
        }
        gateway.response.set_action_response(success_payload(payload))
        log("Migration account double check retrieved successfully")
        trace_out()
        return not is_error()
        
    except Exception as e:
        warn(f"Migration account double check error: {e}")
        report_error("action", f"Migration account double check error: {e}")
        trace_out()
        return False


@register_parser("migration_account_double_check")
def migration_account_double_check_parser() -> bool:
    """Parse and display migration account double check results."""
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
        new_orphans = source_data.get("new_orphans", [])
        new_orphan_count = source_data.get("new_orphan_count", 0)
        legacy_orphans = source_data.get("legacy_orphans", [])
        legacy_orphan_count = source_data.get("legacy_orphan_count", 0)
        data_mismatches = source_data.get("data_mismatches", [])
        mismatch_count = source_data.get("mismatch_count", 0)
        
        lines = [render_header_block("l_migration_account_double_check_header")]
        
        total_issues = new_orphan_count + legacy_orphan_count + mismatch_count
        
        # Summary table
        summary_table = TableData()
        summary_table.add_row(
            "header",
            label="Check Type",
            count="Count"
        )
        summary_table.add_row("new_orphans", label="New accounts without legacy links", count=str(new_orphan_count))
        summary_table.add_row("legacy_orphans", label="Legacy accounts without new entries", count=str(legacy_orphan_count))
        summary_table.add_row("mismatches", label="Data mismatches", count=str(mismatch_count))
        summary_table.add_row("total", label="Total issues", count=str(total_issues))
        
        lines.append(
            render_block(
                summary_table,
                FieldConfig()
                    .add_header("header")
                    .add_simple(["new_orphans", "legacy_orphans", "mismatches", "total"]),
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
                label=f"New Accounts Without Legacy Links ({new_orphan_count})",
                id="ID",
                name="Name",
                type="Type"
            )
            
            for account in new_orphans[:50]:
                new_orphan_table.add_row(
                    "orphan",
                    id=str(account.get('id', '?')),
                    name=account.get('name') or '(null)',
                    type=account.get('type', 'unknown')
                )
            
            if len(new_orphans) > 50:
                new_orphan_table.add_row(
                    "more",
                    id=f"... ({len(new_orphans) - 50} more)",
                    name="",
                    type=""
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
                label=f"Legacy Accounts Without New Entries ({legacy_orphan_count})",
                legacy_id="Legacy ID",
                new_id="New ID",
                name="Name",
                type="Type"
            )
            
            for account in legacy_orphans[:50]:
                legacy_orphan_table.add_row(
                    "orphan",
                    legacy_id=str(account.get('legacy_id', '?')),
                    new_id=str(account.get('new_id', '?')),
                    name=account.get('name') or '(null)',
                    type=account.get('type', 'unknown')
                )
            
            if len(legacy_orphans) > 50:
                legacy_orphan_table.add_row(
                    "more",
                    legacy_id=f"... ({len(legacy_orphans) - 50} more)",
                    new_id="",
                    name="",
                    type=""
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
        
        gateway.response.add_output(finalize_output(lines))
        log(f"Migration account double check parser completed successfully")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Migration account double check parser error: {e}")
        report_error("backend", f"Migration account double check parser error: {e}")
        trace_out()
        return False


register_maintenance_tool("migration_account_double_check")


