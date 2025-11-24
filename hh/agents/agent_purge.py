from __future__ import annotations
from typing import Dict, Union, List
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

def get_active_agents() -> List[Dict[str, Union[str, int]]]:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    query = """
    SELECT a.id, a.agent_key, a.role, a.status, a.created_at, ap.display_name
    FROM agents a
    LEFT JOIN agent_profiles ap ON a.id = ap.agent_id
    WHERE a.status = 'active' AND a.role != 'operator'
    ORDER BY a.created_at DESC
    """
    agents = gateway.conn.read(query)
    log(f"Found {len(agents)} active agents (excluding operators)")
    for agent in agents:
        ensure_iso_timestamps(agent, ['created_at'])
    trace_out()
    return agents

@register_action('agent_purge')
@register_command('agent_purge')
def agent_purge() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return False    
    confirm = gateway.get_arg('confirm')
    log(f"Purge operation parameters: confirm={confirm}")
    if not confirm:
        warn("Purge operation attempted without confirmation")
        report_error("action", "Purge operation requires --confirm flag for safety")
        trace_out()
        return False
    
    try:
        active_agents = get_active_agents()
        operations = []
        log("Executing purge operation")
        update_query = "UPDATE agents SET status='inactive', `terminated`=1 WHERE status='active' AND role != 'operator'"
        agents_updated = gateway.conn.update(update_query)
        log(f"Updated {agents_updated} agents to inactive status")
        operations.append({
            "operation": update_query,
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
            delete_query = f"DELETE FROM {table}"
            rows_deleted = gateway.conn.delete(delete_query)
            if rows_deleted > 0:
                log(f"Cleaned {rows_deleted} records from {table}")
                operations.append({
                    "operation": delete_query,
                    "description": f"Cleaned {rows_deleted} {table} records for all agents"
                })
        result_data = {
            "type": "agent_purge",
            "success": True,
            "message": f"Successfully archived agents and cleaned operational state and queues",
            "agents_affected": agents_updated,
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
