"""
Migration script for legacy work_dockets, asks, tasks, steps tables.
Reads legacy data and prints summary before migration.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from collections import defaultdict

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


@register_action('migrate_legacy_work')
@register_command('migrate_legacy_work')
def migrate_legacy_work() -> bool:
    """
    Read legacy work_dockets, asks, tasks, steps tables and print summary.
    """
    trace_in()
    gateway = get_gateway()
    
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "Gateway connection not available")
        trace_out()
        return False
    
    try:
        # Read all work_dockets
        log("Reading work_dockets...")
        work_dockets = gateway.conn.read(
            "SELECT id, page_id, started_ts, ended_ts, active, meta, title, description, status, sort_order FROM work_dockets ORDER BY id"
        )
        
        # Read all asks
        log("Reading asks...")
        asks = gateway.conn.read(
            "SELECT id, page_id, work_docket_id, title, status, meta, description, sort_order FROM asks ORDER BY id"
        )
        
        # Read all tasks
        log("Reading tasks...")
        tasks = gateway.conn.read(
            "SELECT id, page_id, ask_id, title, status, meta, description, sort_order FROM tasks ORDER BY id"
        )
        
        # Read all steps
        log("Reading steps...")
        steps = gateway.conn.read(
            "SELECT id, page_id, task_id, title, description, status, meta, sort_order FROM steps ORDER BY id"
        )
        
        # Build in-memory representation
        work_dockets_dict = {wd['id']: wd for wd in work_dockets}
        asks_dict = {ask['id']: ask for ask in asks}
        tasks_dict = {task['id']: task for task in tasks}
        steps_dict = {step['id']: step for step in steps}
        
        # Build relationship maps
        asks_by_docket = defaultdict(list)
        for ask in asks:
            asks_by_docket[ask['work_docket_id']].append(ask)
        
        tasks_by_ask = defaultdict(list)
        for task in tasks:
            if task['ask_id']:
                tasks_by_ask[task['ask_id']].append(task)
        
        steps_by_task = defaultdict(list)
        for step in steps:
            if step['task_id']:
                steps_by_task[step['task_id']].append(step)
        
        # Check for -full flag
        show_full = gateway.is_set('full')
        
        # Print summary
        summary_lines = []
        summary_lines.append("=" * 80)
        summary_lines.append("LEGACY WORK DATA SUMMARY")
        summary_lines.append("=" * 80)
        summary_lines.append("")
        summary_lines.append(f"Work Dockets: {len(work_dockets)}")
        summary_lines.append(f"Asks: {len(asks)}")
        summary_lines.append(f"Tasks: {len(tasks)}")
        summary_lines.append(f"Steps: {len(steps)}")
        summary_lines.append("")
        
        if not show_full:
            summary_lines.append("(Use -full flag to see detailed listings)")
            summary_lines.append("")
        
        # Work dockets detail (only if -full flag is set)
        if show_full:
            summary_lines.append("WORK DOCKETS:")
            summary_lines.append("-" * 80)
            for wd_id, wd in sorted(work_dockets_dict.items()):
                page_id_str = f"page_id={wd['page_id']}" if wd['page_id'] else "page_id=NULL"
                asks_count = len(asks_by_docket[wd_id])
                summary_lines.append(f"  WorkDocket {wd_id}: {page_id_str}, title='{wd.get('title', '')}', status={wd['status']}, sort_order={wd['sort_order']}, asks={asks_count}")
            
            summary_lines.append("")
            
            # Asks detail
            summary_lines.append("ASKS:")
            summary_lines.append("-" * 80)
            for ask_id, ask in sorted(asks_dict.items()):
                page_id_str = f"page_id={ask['page_id']}" if ask['page_id'] else "page_id=NULL"
                docket_id = ask['work_docket_id']
                tasks_count = len(tasks_by_ask[ask_id])
                summary_lines.append(f"  Ask {ask_id}: {page_id_str}, work_docket_id={docket_id}, title='{ask.get('title', '')}', status={ask['status']}, sort_order={ask['sort_order']}, tasks={tasks_count}")
            
            summary_lines.append("")
            
            # Tasks detail
            summary_lines.append("TASKS:")
            summary_lines.append("-" * 80)
            for task_id, task in sorted(tasks_dict.items()):
                page_id_str = f"page_id={task['page_id']}" if task['page_id'] else "page_id=NULL"
                ask_id = task['ask_id']
                steps_count = len(steps_by_task[task_id])
                summary_lines.append(f"  Task {task_id}: {page_id_str}, ask_id={ask_id}, title='{task.get('title', '')}', status={task['status']}, sort_order={task['sort_order']}, steps={steps_count}")
            
            summary_lines.append("")
        
        # Steps detail (summary only, too many to list individually)
        summary_lines.append("STEPS:")
        summary_lines.append("-" * 80)
        steps_with_page_id = sum(1 for s in steps if s['page_id'])
        steps_without_page_id = len(steps) - steps_with_page_id
        summary_lines.append(f"  Total steps: {len(steps)}")
        summary_lines.append(f"  Steps with page_id: {steps_with_page_id}")
        summary_lines.append(f"  Steps without page_id: {steps_without_page_id}")
        
        # Check for orphaned records
        summary_lines.append("")
        summary_lines.append("ORPHANED RECORDS:")
        summary_lines.append("-" * 80)
        
        orphaned_asks = [ask for ask in asks if ask['work_docket_id'] not in work_dockets_dict]
        orphaned_tasks = [task for task in tasks if task['ask_id'] and task['ask_id'] not in asks_dict]
        orphaned_steps = [step for step in steps if step['task_id'] and step['task_id'] not in tasks_dict]
        
        summary_lines.append(f"  Orphaned asks (work_docket_id not found): {len(orphaned_asks)}")
        if orphaned_asks:
            for ask in orphaned_asks[:10]:  # Show first 10
                summary_lines.append(f"    Ask {ask['id']}: work_docket_id={ask['work_docket_id']}")
            if len(orphaned_asks) > 10:
                summary_lines.append(f"    ... and {len(orphaned_asks) - 10} more")
        
        summary_lines.append(f"  Orphaned tasks (ask_id not found): {len(orphaned_tasks)}")
        if orphaned_tasks:
            for task in orphaned_tasks[:10]:  # Show first 10
                summary_lines.append(f"    Task {task['id']}: ask_id={task['ask_id']}")
            if len(orphaned_tasks) > 10:
                summary_lines.append(f"    ... and {len(orphaned_tasks) - 10} more")
        
        summary_lines.append(f"  Orphaned steps (task_id not found): {len(orphaned_steps)}")
        if orphaned_steps:
            for step in orphaned_steps[:10]:  # Show first 10
                summary_lines.append(f"    Step {step['id']}: task_id={step['task_id']}")
            if len(orphaned_steps) > 10:
                summary_lines.append(f"    ... and {len(orphaned_steps) - 10} more")
        
        summary_lines.append("")
        summary_lines.append("=" * 80)
        
        # Output summary
        summary_text = "\n".join(summary_lines)
        log(summary_text)
        
        # Set response
        gateway.response.set_action_response({
            "summary": summary_text,
            "counts": {
                "work_dockets": len(work_dockets),
                "asks": len(asks),
                "tasks": len(tasks),
                "steps": len(steps)
            },
            "orphaned": {
                "asks": len(orphaned_asks),
                "tasks": len(orphaned_tasks),
                "steps": len(orphaned_steps)
            }
        })
        
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Error reading legacy work data: {e}")
        report_error("action", f"Error reading legacy work data: {e}")
        trace_out()
        return False
