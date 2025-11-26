from __future__ import annotations
import datetime as dt
from typing import Dict, Any, Tuple
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from .training_matrix import TrainingMatrix
from .training_messaging import TrainingMessaging
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

def create_training_agent(default_role: str = "apprentice") -> Tuple[int, str]:
    """Create a new training agent and return (agent_id, badge_ts)."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise Exception("No gateway or connection available")
    badge_ts = dt.datetime.now().time()
    agent_id = gateway.conn.create("""
        INSERT INTO agents (agent_key, role, badge_ts, status)
        VALUES (%s, %s, %s, 'inactive')
    """, (str(badge_ts), default_role, badge_ts))
    if agent_id is None:
        warn("Failed to create training agent")
        trace_out()
        raise Exception("Failed to create training agent")
    log(f"Created training agent: id={agent_id}, badge_ts={badge_ts}")
    trace_out()
    return agent_id, str(badge_ts)

def onboard_agent(agent_id: int, badge_ts: str) -> Dict[str, Any]:
    """Onboard agent by creating record and queuing first training message."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway or connection available"}
    # Get agent role
    query = "SELECT role FROM agents WHERE id=%s AND badge_ts=%s"
    results = gateway.conn.read(query, [agent_id, badge_ts])
    if not results:
        warn(f"Agent {agent_id} not found during onboarding")
        trace_out()
        return {"error": "Agent not found"}
    
    role = results[0]["role"]
    log(f"Onboarding agent {agent_id} with role {role}")
    
    # Initialize training components
    matrix = TrainingMatrix()
    messaging = TrainingMessaging()
    
    # Get first training gate
    next_gate = matrix.get_next_gate(agent_id, role)
    if not next_gate:
        warn(f"No training gates found for agent {agent_id}")
        trace_out()
        return {"error": "No training gates available"}
    
    doc_path, filename, question = next_gate
    gate_number = 1  # First gate
    
    # Queue first training message
    messaging.queue_training_message(agent_id, doc_path, question, gate_number, badge_ts)
    
    result = {
        "agent_id": agent_id,
        "badge_ts": badge_ts,
        "role": role,
        "next_command": f"hh sip --agent-id {agent_id} --badge-ts {badge_ts}",
        "training_started": True,
        "first_gate": {
            "doc_path": doc_path,
            "filename": filename,
            "has_question": bool(question.strip()),
            "gate_number": gate_number
        }
    }
    
    log(f"Onboarding completed for agent {agent_id}")
    trace_out()
    return result

@register_action('onboard')
@register_command('onboard')
def onboard() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    try:
        # Create new training agent
        agent_id, badge_ts = create_training_agent("apprentice")
        log(f"Created agent: id={agent_id}, badge_ts={badge_ts}")
        
        # Onboard the agent
        result = onboard_agent(agent_id=agent_id, badge_ts=badge_ts)
        if "error" in result:
            warn(f"Onboarding failed: {result['error']}")
            report_error("action", result['error'])
            trace_out()
            return False
        
        log(f"Onboarding completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Onboarding failed: {str(e)}")
        report_error("backend", f"Onboarding failed: {str(e)}")
        trace_out()
        return False
