from __future__ import annotations
from typing import Dict, Any, Optional
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from .training_matrix import TrainingMatrix
from .training_progress import TrainingProgress
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

def validate_agent_identity(agent_id: int, badge_ts: str) -> Optional[Dict[str, Any]]:
    """Validate agent identity and return agent data."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return None
    query = "SELECT id, role, badge_ts, status FROM agents WHERE id=%s AND badge_ts=%s"
    results = gateway.conn.read(query, [agent_id, badge_ts])
    if results:
        log(f"Agent identity validated for agent_id={agent_id}")
        trace_out()
        return results[0]
    else:
        warn(f"Agent identity not found for agent_id={agent_id}")
        trace_out()
        return None

def validate_role(role: str) -> bool:
    """Validate that the target role exists in training configuration."""
    trace_in()
    matrix = TrainingMatrix()
    available_roles = matrix.discover_roles()
    valid = role in available_roles
    log(f"Role validation for {role}: {valid}")
    trace_out()
    return valid

def promote_agent(agent_id: int, badge_ts: str, new_role: str) -> Dict[str, Any]:
    """Promote agent to new role and queue role-specific training."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway or connection available"}
    # Validate agent identity
    agent_data = validate_agent_identity(agent_id, badge_ts)
    if not agent_data:
        warn("Agent identity not found during promotion")
        trace_out()
        return {"error": "Agent identity not found"}
    
    current_role = agent_data["role"]
    log(f"Promoting agent {agent_id} from {current_role} to {new_role}")
    
    # Validate target role
    if not validate_role(new_role):
        warn(f"Invalid role {new_role} for promotion")
        trace_out()
        return {"error": f"Invalid role '{new_role}'. Available roles: {', '.join(TrainingMatrix().discover_roles())}"}
    
    # Check if agent is currently active and punch out if needed
    if agent_data["status"] == "active":
        log(f"Agent {agent_id} is currently active, punching out first")
        affected = gateway.conn.update("UPDATE agents SET status='inactive' WHERE id=%s", (agent_id,))
        if affected == 0:
            warn(f"Failed to punch out agent {agent_id}")
            trace_out()
            return {"error": "Failed to punch out agent"}
    
    # Update agent role
    affected = gateway.conn.update("UPDATE agents SET role=%s WHERE id=%s", (new_role, agent_id))
    if affected == 0:
        warn(f"Failed to update agent {agent_id} role to {new_role}")
        trace_out()
        return {"error": "Failed to update agent role"}
    log(f"Updated agent {agent_id} role to {new_role}")
    
    # Initialize training components
    matrix = TrainingMatrix()
    progress = TrainingProgress()
    messaging = TrainingMessaging()
    
    # Check if role-specific training is needed
    role_required_docs = matrix.list_required_docs_for(agent_id, new_role)
    general_required_docs = matrix.list_required_docs_for(agent_id, "general")
    all_required_docs = list(set(general_required_docs + role_required_docs))
    
    # Check if role training is already complete
    role_training_complete = progress.is_role_training_complete(agent_id, new_role)
    
    result = {
        "agent_id": agent_id,
        "badge_ts": badge_ts,
        "old_role": current_role,
        "new_role": new_role,
        "promotion_successful": True,
        "role_training_complete": role_training_complete
    }
    
    if role_training_complete:
        # Role training already complete, queue completion message
        messaging.queue_completion_message(agent_id, "role_complete", badge_ts, new_role)
        result["next_command"] = f"hh punch-in --agent-id {agent_id} --badge-ts {badge_ts}"
        result["message"] = f"Promoted to {new_role}. Role training already complete. You can punch in now."
    else:
        # Queue role-specific training start message
        messaging.queue_promotion_message(agent_id, new_role, badge_ts)
        result["next_command"] = f"hh sip --agent-id {agent_id} --badge-ts {badge_ts}"
        result["message"] = f"Promoted to {new_role}. Complete role-specific training to continue."
    
    log(f"Promotion completed for agent {agent_id} to role {new_role}")
    trace_out()
    return result

@register_action('promote')
@register_command('promote')
def promote() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    new_role = gateway.get_arg('role')
    
    log(f"Promote command: agent_id={agent_id}, badge_ts={badge_ts}, new_role={new_role}")
    
    if not agent_id:
        warn("Agent ID is required for promote command")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    
    if not badge_ts:
        warn("Badge timestamp is required for promote command")
        report_error("action", "Badge timestamp is required")
        trace_out()
        return False
    
    if not new_role:
        warn("Role is required for promote command")
        report_error("action", "Role is required")
        trace_out()
        return False
    
    try:
        result = promote_agent(agent_id=agent_id, badge_ts=badge_ts, new_role=new_role)
        if "error" in result:
            warn(f"Promotion failed: {result['error']}")
            report_error("action", result['error'])
            trace_out()
            return False
        
        log(f"Promote command completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Promotion failed: {str(e)}")
        report_error("backend", f"Promotion failed: {str(e)}")
        trace_out()
        return False
