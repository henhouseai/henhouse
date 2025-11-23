from __future__ import annotations
from typing import Dict, Union, List
from hh.gateway.connection.decorators import db_write
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.utils import ensure_iso_timestamps
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error

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

def get_active_agents(conn) -> List[Dict[str, Union[str, int]]]:
    trace_in()
    query = """
    SELECT a.id, a.agent_key, a.role, a.status, a.created_at, ap.display_name
    FROM agents a
    LEFT JOIN agent_profiles ap ON a.id = ap.agent_id
    WHERE a.status = 'active' AND a.role != 'operator'
    ORDER BY a.created_at DESC
    """
    agents = r_query(conn, query)
    log(f"Found {len(agents)} active agents (excluding operators)")
    for agent in agents:
        ensure_iso_timestamps(agent, ['created_at'])
    trace_out()
    return agents

@register_action('agent_purge')
@register_command('agent_purge')
@db_write
def agent_purge(conn, args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    dry_run = gateway.get_arg('dry_run')
    confirm = gateway.get_arg('confirm')
    log(f"Purge operation parameters: dry_run={dry_run}, confirm={confirm}")
    if not dry_run and not confirm:
        warn("Purge operation attempted without confirmation")
        report_error("action", "Purge operation requires --confirm flag for safety. Use --dry-run to see what would be affected first")
        trace_out()
        return False
    try:
        active_agents = get_active_agents(conn)
        operations = []
        if dry_run:
            log("Executing dry run mode - no changes will be made")
            operations.append({
                "operation": "UPDATE agents SET status='inactive', `terminated`=1 WHERE status='active' AND role != 'operator'",
                "description": f"Archive active agents (excluding operators) - {len(active_agents)} currently active"
            })
            with conn.cursor() as cursor:
                sub_queries = [
                    ("subscription_ask", "DELETE FROM subscription_ask"),
                    ("subscription_task", "DELETE FROM subscription_task"),
                    ("subscription_step", "DELETE FROM subscription_step"),
                    ("subscription_sidecar", "DELETE FROM subscription_sidecar"),
                    ("subscription_keyword", "DELETE FROM subscription_keyword"),
                    ("subscription_docket", "DELETE FROM subscription_docket"),
                    ("subscription_agent", "DELETE FROM subscription_agent"),
                    ("subscription_operator", "DELETE FROM subscription_operator"),
                    ("watercooler_queue_step", "DELETE FROM watercooler_queue_step"),
                    ("watercooler_queue_task", "DELETE FROM watercooler_queue_task"),
                    ("watercooler_queue_ask", "DELETE FROM watercooler_queue_ask"),
                    ("watercooler_queue_docket", "DELETE FROM watercooler_queue_docket"),
                    ("watercooler_queue_sidecar", "DELETE FROM watercooler_queue_sidecar"),
                    ("watercooler_queue_keyword", "DELETE FROM watercooler_queue_keyword"),
                    ("watercooler_queue_agent", "DELETE FROM watercooler_queue_agent"),
                    ("watercooler_queue_operator", "DELETE FROM watercooler_queue_operator"),
                ]
                for table_name, query in sub_queries:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count_result = cursor.fetchone()
                    count = count_result['count'] if count_result else 0
                    operations.append({
                        "operation": query,
                        "description": f"Clean {count} {table_name} records for all agents"
                    })
            result_data = {
                "type": "agent_purge",
                "success": True,
                "message": f"Dry run: Would archive agents and clean operational state and queues",
                "agents_affected": len(active_agents),
                "agents": active_agents,
                "dry_run": True,
                "operations": operations
            }
            log(f"Dry run completed: {len(active_agents)} agents would be affected")
            gateway.response.set_action_response(success_payload(result_data))
            trace_out()
            return True
        log("Executing actual purge operation - changes will be made")
        with conn.cursor() as cursor:
            cursor.execute("UPDATE agents SET status='inactive', `terminated`=1 WHERE status='active' AND role != 'operator'")
            agents_updated = cursor.rowcount
            log(f"Updated {agents_updated} agents to inactive status")
            operations.append({
                "operation": "UPDATE agents SET status='inactive', `terminated`=1 WHERE status='active' AND role != 'operator'",
                "description": f"Archived {agents_updated} active agents (excluding operators)"
            })
            sub_tables = [
                "subscription_ask",
                "subscription_task", 
                "subscription_step",
                "subscription_sidecar",
                "subscription_keyword",
                "subscription_docket",
                "subscription_agent",
                "subscription_operator",
                "watercooler_queue_step",
                "watercooler_queue_task",
                "watercooler_queue_ask",
                "watercooler_queue_docket",
                "watercooler_queue_sidecar",
                "watercooler_queue_keyword",
                "watercooler_queue_agent",
                "watercooler_queue_operator"
            ]
            for table in sub_tables:
                cursor.execute(f"DELETE FROM {table}")
                rows_deleted = cursor.rowcount
                if rows_deleted > 0:
                    log(f"Cleaned {rows_deleted} records from {table}")
                    operations.append({
                        "operation": f"DELETE FROM {table}",
                        "description": f"Cleaned {rows_deleted} {table} records for all agents"
                    })
            result_data = {
                "type": "agent_purge",
                "success": True,
                "message": f"Successfully archived agents and cleaned operational state and queues",
                "agents_affected": agents_updated,
                "dry_run": False,
                "operations": operations
            }
            log(f"Purge operation completed successfully: {agents_updated} agents affected")
            gateway.response.set_action_response(success_payload(result_data))
            trace_out()
            return True
    except Exception as e:
        warn(f"Failed to purge agents: {str(e)}")
        report_error("backend", f"Failed to purge agents: {str(e)}")
        trace_out()
        return False
