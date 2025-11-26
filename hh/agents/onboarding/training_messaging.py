from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

class TrainingMessaging:

    def queue_training_message(self, agent_id: int, doc_path: str, question: str, gate_number: int, badge_ts: str) -> bool:
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("No gateway or connection available")
            trace_out()
            return False
        # Convert doc_path to deployment directory format
        deployment_path = f"/src/<project>/context/{doc_path}"
        content = f"Training Gate {gate_number}\n\nPlease read the following document:\n{deployment_path}\n\n"
        if question.strip():
            content += f"After reading, answer this question:\n{question}\n\nWhen you're ready, run:\nhh answer --agent-id {agent_id} --badge-ts {badge_ts} --answer \"your answer here\"\n"
        else:
            content += f"After reading, run:\nhh answer --agent-id {agent_id} --badge-ts {badge_ts} --ack-read\n"
        message_id = gateway.conn.create("INSERT INTO watercooler_messages (from_agent_id, to_agent_id, kind, content, meta) VALUES (%s, %s, %s, %s, %s)", (None, agent_id, 'message', content, None))
        if message_id is None:
            warn("Failed to create training message")
            trace_out()
            return False
        log(f"Created training message {message_id} for agent {agent_id}")
        
        queue_id = gateway.conn.create("INSERT INTO watercooler_queue_dm (agent_id, message_id, queued_ts) VALUES (%s, %s, NOW(6))", (agent_id, message_id))
        if queue_id is None:
            warn("Failed to queue training message")
            trace_out()
            return False
        log(f"Queued training message for agent {agent_id}")
        trace_out()
        return True
    
    def queue_completion_message(self, agent_id: int, message_type: str, badge_ts: str, role: str = None) -> bool:
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("No gateway or connection available")
            trace_out()
            return False
        if message_type == "general_complete":
            content = f"🎉 General Training Complete!\n\nYour general training is now complete. You can now punch in to start working:\n\nhh punch-in --agent-id {agent_id} --badge-ts {badge_ts}\n\nAfter punching in, you'll receive your persona name and can start participating in the system.\n"
        elif message_type == "role_complete":
            content = f"🎉 Role Training Complete!\n\nYour {role} training is now complete. You can now punch in to start working in your new role:\n\nhh punch-in --agent-id {agent_id} --badge-ts {badge_ts}\n\nAfter punching in, you'll receive your updated persona name and can start working as a {role}.\n"
        else:
            content = f"Training Complete!\n\nYour training is now complete. You can now punch in to start working:\n\nhh punch-in --agent-id {agent_id} --badge-ts {badge_ts}\n"
        message_id = gateway.conn.create("INSERT INTO watercooler_messages (from_agent_id, to_agent_id, kind, content, meta) VALUES (%s, %s, %s, %s, %s)", (None, agent_id, 'message', content, None))
        if message_id is None:
            warn("Failed to create completion message")
            trace_out()
            return False
            
        queue_id = gateway.conn.create("INSERT INTO watercooler_queue_dm (agent_id, message_id, queued_ts) VALUES (%s, %s, NOW(6))", (agent_id, message_id))
        if queue_id is None:
            warn("Failed to queue completion message")
            trace_out()
            return False
        log(f"Queued completion message for agent {agent_id}")
        trace_out()
        return True
    
    def queue_promotion_message(self, agent_id: int, new_role: str, badge_ts: str) -> bool:
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("No gateway or connection available")
            trace_out()
            return False
        content = f"🎯 Role Promotion: {new_role.title()}\n\nCongratulations! You've been promoted to {new_role}.\n\nYou now need to complete {new_role}-specific training. Use the sip command to get your next training assignment:\n\nhh sip --agent-id {agent_id} --badge-ts {badge_ts}\n\nComplete all the role-specific training gates, then you'll be ready to punch in as a {new_role}.\n"
        message_id = gateway.conn.create("INSERT INTO watercooler_messages (from_agent_id, to_agent_id, kind, content, meta) VALUES (%s, %s, %s, %s, %s)", (None, agent_id, 'message', content, None))
        if message_id is None:
            warn("Failed to create promotion message")
            trace_out()
            return False
            
        queue_id = gateway.conn.create("INSERT INTO watercooler_queue_dm (agent_id, message_id, queued_ts) VALUES (%s, %s, NOW(6))", (agent_id, message_id))
        if queue_id is None:
            warn("Failed to queue promotion message")
            trace_out()
            return False
        log(f"Queued promotion message for agent {agent_id} to role {new_role}")
        trace_out()
        return True
