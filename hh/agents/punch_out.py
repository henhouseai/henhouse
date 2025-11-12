from __future__ import annotations
from typing import Optional, Dict, Union
from hh.gateway.connection.decorators import  db_write
from hh.gateway.connection.connection import r_query, u_query
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
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

def validate_agent_identity(conn, agent_id: int, badge_ts: str) -> Optional[Dict[str, Union[str, int]]]:
    trace_in()
    query = "SELECT id, agent_key, status FROM agents WHERE id=%s AND badge_ts=%s"
    results = r_query(conn, query, [agent_id, badge_ts])
    if results:
        log(f"Agent identity validated for agent_id={agent_id}")
        trace_out()
        return results[0]
    else:
        warn(f"Agent identity not found for agent_id={agent_id}")
        trace_out()
        return None

@db_write
def punch_out_impl(conn, agent_id: int, badge_ts: str) -> Dict[str, Union[str, int, bool]]:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    agent_data = validate_agent_identity(conn, agent_id, badge_ts)
    if not agent_data:
        warn("Agent identity not found during punch out")
        report_error("action", "Agent identity not found")
        trace_out()
        return False
    if agent_data["status"] != "active":
        warn(f"Agent {agent_id} is not active, cannot punch out")
        report_error("action", "Agent is not active")
        trace_out()
        return False    
    db_agent_key = agent_data["agent_key"]
    log(f"Processing punch out for agent {agent_id} ({db_agent_key})")   
    affected = u_query(conn, "UPDATE agents SET status='inactive' WHERE id=%s", (agent_id,))
    if affected == 0:
        warn(f"Failed to punch out agent {agent_id}")
        trace_out()
        return False
    log(f"Successfully punched out agent {agent_id}")    
    result_data = {
        "agent_key": db_agent_key,
        "agent_id": agent_id,
        "status": "inactive"
    }
    trace_out()
    return result_data

@register_action('punch_out')
@register_command('punch_out')
def punch_out() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    log(f"Punch out request: agent_id={agent_id}, badge_ts={badge_ts}")    
    if not agent_id:
        warn("Agent ID is required but not provided")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    if not badge_ts:
        warn("Badge timestamp is required but not provided")
        report_error("action", "Badge timestamp is required")
        trace_out()
        return False    
    try:
        result_data = punch_out_impl(agent_id=agent_id, badge_ts=badge_ts)
        if "error" in result_data:
            warn(f"Punch out failed: {result_data['message']}")
            report_error("backend", result_data['message'])
            trace_out()
            return False
        log(f"Punch out operation completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result_data))
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to punch out: {str(e)}")
        report_error("backend", f"Failed to punch out: {str(e)}")
        trace_out()
        return False
