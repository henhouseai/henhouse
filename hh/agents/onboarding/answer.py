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

def process_answer(agent_id: int, badge_ts: str, answer: str = None, ack_read: bool = False) -> Dict[str, Any]:
    """Process agent's answer and queue next training message."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway or connection available"}
    # Validate agent identity
    agent_data = validate_agent_identity(agent_id, badge_ts)
    if not agent_data:
        warn("Agent identity not found during answer processing")
        trace_out()
        return {"error": "Agent identity not found"}
    
    role = agent_data["role"]
    log(f"Processing answer for agent {agent_id} with role {role}")
    
    # Initialize training components
    matrix = TrainingMatrix()
    progress = TrainingProgress()
    messaging = TrainingMessaging()
    
    # Get current training gate
    next_gate = matrix.get_next_gate(agent_id, role)
    if not next_gate:
        warn(f"No training gates found for agent {agent_id}")
        trace_out()
        return {"error": "No training gates available"}
    
    doc_path, filename, question = next_gate
    
    # Record the answer
    if ack_read:
        response_text = "No question required"
    elif answer:
        response_text = answer
    else:
        warn("Either answer or ack_read must be provided")
        trace_out()
        return {"error": "Either --answer or --ack-read must be provided"}
    
    # Record the response
    progress.record_answer(agent_id, badge_ts, doc_path, filename, question, response_text)
    
    # Get required docs for progress calculation
    required_docs = matrix.list_required_docs_for(agent_id, role)
    training_progress = progress.get_training_progress(agent_id, role, required_docs)
    
    # Check if training is complete
    is_complete = progress.is_training_complete(agent_id, role, required_docs)
    
    result = {
        "agent_id": agent_id,
        "badge_ts": badge_ts,
        "role": role,
        "doc_path": doc_path,
        "filename": filename,
        "has_question": bool(question.strip()),
        "response_recorded": True,
        "progress": training_progress,
        "training_complete": is_complete
    }
    
    if is_complete:
        # Queue completion message
        if role == "apprentice":
            messaging.queue_completion_message(agent_id, "general_complete", badge_ts, role)
            result["next_command"] = f"hh punch-in --agent-id {agent_id} --badge-ts {badge_ts}"
        else:
            messaging.queue_completion_message(agent_id, "role_complete", badge_ts, role)
            result["next_command"] = f"hh punch-in --agent-id {agent_id} --badge-ts {badge_ts}"
    else:
        # Get next training gate
        next_gate = matrix.get_next_gate(agent_id, role)
        if next_gate:
            next_doc_path, next_filename, next_question = next_gate
            gate_number = training_progress["coffees"][0] + 1  # Next gate number
            messaging.queue_training_message(agent_id, next_doc_path, next_question, gate_number, badge_ts)
            result["next_command"] = f"hh sip --agent-id {agent_id} --badge-ts {badge_ts}"
        else:
            # No more gates, should be complete
            messaging.queue_completion_message(agent_id, "general_complete", badge_ts, role)
            result["next_command"] = f"hh punch-in --agent_id {agent_id} --badge-ts {badge_ts}"
    
    log(f"Answer processed for agent {agent_id}")
    trace_out()
    return result

@register_action('answer')
@register_command('answer')
def answer() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    answer_text = gateway.get_arg('answer')
    ack_read = gateway.is_no('ack_read') == False and gateway.get_arg('ack_read') is not None
    
    log(f"Answer command: agent_id={agent_id}, badge_ts={badge_ts}, has_answer={bool(answer_text)}, ack_read={ack_read}")
    
    if not agent_id:
        warn("Agent ID is required for answer command")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    
    if not badge_ts:
        warn("Badge timestamp is required for answer command")
        report_error("action", "Badge timestamp is required")
        trace_out()
        return False
    
    if not answer_text and not ack_read:
        warn("Either --answer or --ack-read must be provided")
        report_error("action", "Either --answer or --ack-read must be provided")
        trace_out()
        return False
    
    try:
        result = process_answer(agent_id=agent_id, badge_ts=badge_ts, answer=answer_text, ack_read=ack_read)
        if "error" in result:
            warn(f"Answer processing failed: {result['error']}")
            report_error("action", result['error'])
            trace_out()
            return False
        
        log(f"Answer command completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Answer processing failed: {str(e)}")
        report_error("backend", f"Answer processing failed: {str(e)}")
        trace_out()
        return False
