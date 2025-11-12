from __future__ import annotations
from typing import Dict, List, Any, Optional, Union
from hh.gateway.connection.decorators import db_write
from hh.gateway.connection.connection import r_query, c_query
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

class TrainingProgress:
    """Progress tracking and response recording for agent training."""
    
    def has_completed(self, conn, agent_id: int, doc_path: str) -> bool:
        """Check if agent has completed a specific document."""
        trace_in()
        query = "SELECT response FROM agent_onboarding_responses WHERE agent_id=%s AND path=%s ORDER BY created_ts DESC LIMIT 1"
        results = r_query(conn, query, [agent_id, doc_path])
        if not results:
            log(f"Agent {agent_id} has not completed {doc_path}")
            trace_out()
            return False
        response = (results[0].get("response") or "").strip()
        completed = response not in {"Viewed document; answer pending", "", None}
        log(f"Agent {agent_id} completion status for {doc_path}: {completed}")
        trace_out()
        return completed
    
    @db_write
    def record_answer(self, conn, agent_id: int, badge_ts: str, doc_path: str, filename: str, question: str, response: str) -> bool:
        """Record agent's answer to training question. Idempotent - skips if non-placeholder answer exists."""
        trace_in()
        # Check if already answered (non-placeholder)
        query = "SELECT id, response FROM agent_onboarding_responses WHERE agent_id=%s AND path=%s ORDER BY created_ts DESC LIMIT 1"
        results = r_query(conn, query, [agent_id, doc_path])
        if results:
            existing_response = (results[0].get("response") or "").strip()
            if existing_response not in {"Viewed document; answer pending", "No question required", ""}:
                log(f"Agent {agent_id} already has non-placeholder answer for {doc_path}, skipping")
                trace_out()
                return True
        
        # Record the answer
        response_id = c_query(conn, """
            INSERT INTO agent_onboarding_responses (agent_id, badge_ts, path, filename, question, response)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (agent_id, badge_ts, doc_path, filename, question or "", response or "No question required"))
        if response_id is None:
            warn(f"Failed to record answer for agent {agent_id}, document {doc_path}")
            trace_out()
            return False
        log(f"Recorded answer for agent {agent_id}, document {doc_path}")
        trace_out()
        return True
    
    def get_training_progress(self, conn, agent_id: int, role: str, required_docs: List[str]) -> Dict[str, List[int]]:
        """Get training progress counts (coffees: [done, total], exams: [done, total])."""
        trace_in()
        coffees_done = sum(1 for doc_path in required_docs if self.has_completed(conn, agent_id, doc_path))
        coffees_total = len(required_docs)
        
        # Count exams (gates with questions)
        from .training_matrix import TrainingMatrix
        matrix = TrainingMatrix()
        general_cfg = matrix.load_gate_config("general")
        role_cfg = matrix.load_gate_config(role)
        combined = general_cfg.get("gates", []) + role_cfg.get("gates", [])
        
        exams_total = 0
        exams_done = 0
        for gate in combined:
            doc_path = gate.get("doc_path", "")
            question = gate.get("question", "")
            if doc_path in required_docs and question.strip():
                exams_total += 1
                if self.has_completed(conn, agent_id, doc_path):
                    exams_done += 1
        
        progress = {
            "coffees": [coffees_done, coffees_total],
            "exams": [exams_done, exams_total]
        }
        log(f"Training progress for agent {agent_id}: {progress}")
        trace_out()
        return progress
    
    def is_training_complete(self, conn, agent_id: int, role: str, required_docs: List[str]) -> bool:
        """Check if all required training documents are completed."""
        trace_in()
        complete = all(self.has_completed(conn, agent_id, doc_path) for doc_path in required_docs)
        log(f"Training complete for agent {agent_id}, role {role}: {complete}")
        trace_out()
        return complete
    
    def is_role_training_complete(self, conn, agent_id: int, role: str) -> bool:
        """Check if role-specific training is complete."""
        trace_in()
        from .training_matrix import TrainingMatrix
        matrix = TrainingMatrix()
        role_cfg = matrix.load_gate_config(role)
        role_required = [gate.get("doc_path", "") for gate in role_cfg.get("gates", []) if gate.get("doc_path", "")]
        
        if not role_required:
            log(f"No role-specific training required for role {role}")
            trace_out()
            return True
        
        complete = all(self.has_completed(conn, agent_id, doc_path) for doc_path in role_required)
        log(f"Role training complete for agent {agent_id}, role {role}: {complete}")
        trace_out()
        return complete
