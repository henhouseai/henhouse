from __future__ import annotations
import json
import hashlib
import random
import importlib.resources
from typing import Optional, Dict, Union
from hh.gateway.connection.decorators import db_write
from hh.gateway.connection.connection import r_query, u_query, c_query
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

def load_persona_names():
    trace_in()
    try:
        persona_file = importlib.resources.files('hh.agents') / 'timeclock' / 'persona_names.txt'
        with open(persona_file, 'r') as f:
            names = [line.strip() for line in f if line.strip()]
        log(f"Loaded {len(names)} persona names from file")
        trace_out()
        return names
    except FileNotFoundError:
        warn("Persona names file not found, using default names")
        default_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        log(f"Using {len(default_names)} default persona names")
        trace_out()
        return default_names

def pick_persona_name_from_badge_ts(badge_ts: str, role: str) -> str:
    trace_in()
    seed = hashlib.md5(badge_ts.encode()).hexdigest()
    names = load_persona_names()
    if not names:
        warn("No persona names available")
        trace_out()
        return f"Unknown {role}"
    random.seed(int(seed[:8], 16))
    idx = random.randint(0, len(names) - 1)
    chosen_name = names[idx]
    result = f"{chosen_name} {role}"
    log(f"Selected persona name: {result} for role {role}")
    trace_out()
    return result

def validate_agent_identity(conn, agent_id: int, badge_ts: str) -> Optional[Dict[str, Union[str, int]]]:
    trace_in()
    query = "SELECT id, role, badge_ts, status FROM agents WHERE id=%s AND badge_ts=%s"
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
def punch_in_impl(conn, agent_id: int, badge_ts: str) -> Dict[str, Union[str, int, bool]]:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    agent_data = validate_agent_identity(conn, agent_id, badge_ts)
    if not agent_data:
        warn("Agent identity not found during punch in")
        report_error("action", "Agent identity not found")
        trace_out()
        return False
    if agent_data["status"] != "inactive":
        warn(f"Agent {agent_id} is already active, cannot punch in")
        report_error("action", "Agent is already active")
        trace_out()
        return False
    db_role = agent_data["role"]
    log(f"Processing punch in for agent {agent_id} with role {db_role}")
    display_name = pick_persona_name_from_badge_ts(badge_ts, db_role)
    
    # Check if agent profile exists
    exists = r_query(conn, "SELECT 1 FROM agent_profiles WHERE agent_id=%s", (agent_id,))
    if exists:
        log(f"Updating existing agent profile for agent {agent_id}")
        affected = u_query(conn, "UPDATE agent_profiles SET display_name=%s WHERE agent_id=%s", (display_name, agent_id))
        if affected == 0:
            warn(f"Failed to update agent profile for agent {agent_id}")
            trace_out()
            return False
    else:
        log(f"Creating new agent profile for agent {agent_id}")
        profile_id = c_query(conn, "INSERT INTO agent_profiles (agent_id, display_name, country, lineage_key, generation, persona_json) VALUES (%s,%s,%s,%s,%s,%s)",
                           (agent_id, display_name, "US", f"{db_role}:{badge_ts[:10]}", 1, json.dumps(display_name)))
        if profile_id is None:
            warn(f"Failed to create agent profile for agent {agent_id}")
            trace_out()
            return False
    
    # Update agent key
    affected = u_query(conn, "UPDATE agents SET agent_key=%s WHERE id=%s", (display_name, agent_id))
    if affected == 0:
        warn(f"Failed to update agent key for agent {agent_id}")
        trace_out()
        return False
    
    # Update agent status
    affected = u_query(conn, "UPDATE agents SET status='active' WHERE id=%s", (agent_id,))
    if affected == 0:
        warn(f"Failed to update agent status for agent {agent_id}")
        trace_out()
        return False
    
    log(f"Successfully punched in agent {agent_id} as {display_name}")
    result_data = {
        "agent_key": display_name,
        "agent_id": agent_id,
        "full_name": display_name,
        "status": "active"
    }
    trace_out()
    return result_data

@register_action('punch_in')
@register_command('punch_in')
def punch_in() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False   
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    log(f"Punch in request: agent_id={agent_id}, badge_ts={badge_ts}")
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
        result_data = punch_in_impl(agent_id=agent_id, badge_ts=badge_ts)
        if "error" in result_data:
            warn(f"Punch in failed: {result_data['message']}")
            report_error("backend", result_data['message'])
            trace_out()
            return False
        log(f"Punch in operation completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result_data))
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to punch in: {str(e)}")
        report_error("backend", f"Failed to punch in: {str(e)}")
        trace_out()
        return False
