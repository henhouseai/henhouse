from __future__ import annotations
from typing import Optional, Dict, Union
from hh.agents.agents_utils import validate_agent_identity
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

@register_action('punch_out')
@register_command('punch_out')
def punch_out() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
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
        agent_data = validate_agent_identity(agent_id, badge_ts)
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
        affected = gateway.conn.update("UPDATE agents SET status='inactive' WHERE id=%s", (agent_id,))
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
        log(f"Punch out operation completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result_data))
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to punch out: {str(e)}")
        report_error("backend", f"Failed to punch out: {str(e)}")
        trace_out()
        return False
