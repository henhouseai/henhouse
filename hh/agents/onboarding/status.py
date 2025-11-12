from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.connection import r_query
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from .training_progress import TrainingProgress
from .training_matrix import TrainingMatrix
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


def get_agent_answers(conn, agent_id: int) -> List[Dict[str, Any]]:
    """Get all answered questions for an agent"""
    trace_in()
    try:
        query = """
            SELECT 
                aor.path as doc_path,
                aor.filename,
                aor.question,
                aor.response,
                aor.created_ts as created_at,
                1 as gate_number
            FROM agent_onboarding_responses aor
            WHERE aor.agent_id = %s
            ORDER BY aor.created_ts
        """
        results = r_query(conn, query, [agent_id])
        
        answers = []
        for row in results:
            answers.append({
                'doc_path': row['doc_path'],
                'filename': row['filename'],
                'question': row['question'],
                'response': row['response'],
                'created_at': row['created_at'],
                'gate_number': row['gate_number']
            })
        
        log(f"Retrieved {len(answers)} answers for agent {agent_id}")
        trace_out()
        return answers
    except Exception as e:
        warn(f"Error getting agent answers: {e}")
        trace_out()
        return []


def get_agent_status(conn, agent_id: int, badge_ts: str) -> Dict[str, Any]:
    """Get comprehensive status for an agent"""
    trace_in()
    try:
        # Get agent info
        query = """
            SELECT 
                a.id,
                a.badge_ts,
                a.role,
                a.status,
                a.created_at,
                a.terminated
            FROM agents a
            WHERE a.id = %s AND a.badge_ts = %s
        """
        results = r_query(conn, query, [agent_id, badge_ts])
        
        if not results:
            warn(f"Agent {agent_id} not found with badge {badge_ts}")
            trace_out()
            return {
                'success': False,
                'error': 'Agent not found or invalid credentials'
            }
        
        agent_row = results[0]
        agent_info = {
            'agent_id': agent_row['id'],
            'badge_ts': str(agent_row['badge_ts']),
            'persona_name': f"Agent-{agent_row['id']}",  # No persona_name in agents table
            'role': agent_row['role'],
            'punch_in_ts': None,  # No punch_in_ts in agents table
            'punch_out_ts': None,  # No punch_out_ts in agents table
            'is_active': agent_row['status'] == 'active',
            'created_at': str(agent_row['created_at']),
            'terminated': bool(agent_row['terminated'])
        }
        
        # Get training progress
        progress_tracker = TrainingProgress()
        
        # Get required docs for the role
        from .training_matrix import TrainingMatrix
        matrix = TrainingMatrix()
        general_cfg = matrix.load_gate_config("general")
        role_cfg = matrix.load_gate_config(agent_info['role'])
        combined = general_cfg.get("gates", []) + role_cfg.get("gates", [])
        required_docs = [gate.get("doc_path", "") for gate in combined if gate.get("doc_path", "")]
        
        raw_progress = progress_tracker.get_training_progress(conn, agent_id, agent_info['role'], required_docs)
        is_complete = progress_tracker.is_training_complete(conn, agent_id, agent_info['role'], required_docs)
        is_role_complete = progress_tracker.is_role_training_complete(conn, agent_id, agent_info['role'])
        
        # Format training progress for parser
        training_progress = {
            agent_info['role']: {
                'completed': raw_progress['coffees'][0],
                'total': raw_progress['coffees'][1],
                'percentage': (raw_progress['coffees'][0] / raw_progress['coffees'][1] * 100) if raw_progress['coffees'][1] > 0 else 0
            }
        }
        
        # Get answered questions
        answers = get_agent_answers(conn, agent_id)
        
        # Get available roles
        matrix = TrainingMatrix()
        available_roles = matrix.discover_roles()
        
        result = {
            'success': True,
            'agent_info': agent_info,
            'training_progress': training_progress,
            'is_training_complete': is_complete,
            'is_role_training_complete': is_role_complete,
            'answers': answers,
            'available_roles': available_roles,
            'timestamp': datetime.now().isoformat()
        }
        
        log(f"Retrieved status for agent {agent_id}")
        trace_out()
        return result
        
    except Exception as e:
        warn(f"Error getting agent status: {e}")
        trace_out()
        return {
            'success': False,
            'error': f'Database error: {str(e)}'
        }


@register_action('status')
@register_command('status')
@db_read
def status(conn) -> bool:
    """Show training progress and answered questions for an agent"""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    try:
        # Get arguments from gateway
        agent_id = gateway.get_arg('agent_id')
        badge_ts = gateway.get_arg('badge_ts')
        
        if not agent_id or not badge_ts:
            warn("Missing required arguments: agent_id and badge_ts")
            report_error("action", "Missing required arguments: agent_id and badge_ts")
            trace_out()
            return False
        
        log(f"Status called with agent_id={agent_id}, badge_ts={badge_ts}")
        
        # Get agent status
        status_data = get_agent_status(conn, agent_id, badge_ts)
        
        if not status_data['success']:
            warn(f"Status failed: {status_data['error']}")
            report_error("action", status_data['error'])
            trace_out()
            return False
        
        log(f"Status completed for agent {agent_id}")
        gateway.response.set_action_response(success_payload(status_data))
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Status error: {e}")
        report_error("backend", f"Status error: {e}")
        trace_out()
        return False


if __name__ == "__main__":
    status()
