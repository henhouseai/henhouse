from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List, Optional, Union
from hh.gateway.connection.utils import ensure_iso_timestamps
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

@register_action('gossip')
@register_command('gossip')
def gossip(args: Optional[List[str]] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return False    
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    to_agent_id = gateway.get_arg('to_agent_id')
    to_full_name = gateway.get_arg('to_full_name')
    message = gateway.get_arg('message')
    meta_json = gateway.get_arg('meta_json')
    log(f"Gossip command args: agent_id={agent_id}, to_agent_id={to_agent_id}, to_full_name={to_full_name}, message_length={len(message) if message else 0}")
    if not agent_id:
        warn("Agent ID is required for gossip command")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    if not message:
        warn("Message is required for gossip command")
        report_error("action", "Message is required")
        trace_out()
        return False
    if not to_agent_id and not to_full_name:
        warn("Either to_agent_id or to_full_name must be provided for gossip command")
        report_error("action", "Either --to-agent-id or --to-full-name must be provided")
        trace_out()
        return False
    try:
        from_agent_id = agent_id
        agent_results = gateway.conn.read("SELECT role FROM agents WHERE id=%s", (from_agent_id,))
        if not agent_results:
            warn(f"Agent {from_agent_id} not found in database")
            raise ValueError(f"Agent {from_agent_id} not found")
        role = agent_results[0]['role']
        
        profile_results = gateway.conn.read("SELECT display_name FROM agent_profiles WHERE agent_id=%s", (from_agent_id,))
        display_name = profile_results[0]['display_name'] if profile_results else None
        
        from_info = {
            "role": role,
            "display_name": display_name or role.capitalize()
        }
        log(f"Agent info resolved: id={from_agent_id}, role={role}, display_name={from_info['display_name']}")
        
        if to_agent_id:
            target_agent_id = to_agent_id
            log(f"Target agent resolved by ID: {to_agent_id}")
        elif to_full_name:
            results = gateway.conn.read("SELECT agent_id FROM agent_profiles WHERE display_name=%s LIMIT 1", (to_full_name,))
            if results:
                target_agent_id = results[0]['agent_id']
                log(f"Target agent resolved by name: {to_full_name} -> {target_agent_id}")
            else:
                log(f"Target agent not found by name: {to_full_name}")
                warn("Target agent not found during gossip resolution")
                raise ValueError("Target agent not found")
        else:
            warn("Target agent not found during gossip resolution")
            raise ValueError("Target agent not found")
        
        to_agent_results = gateway.conn.read("SELECT role FROM agents WHERE id=%s", (target_agent_id,))
        if not to_agent_results:
            warn(f"Agent {target_agent_id} not found in database")
            raise ValueError(f"Agent {target_agent_id} not found")
        to_role = to_agent_results[0]['role']
        
        to_profile_results = gateway.conn.read("SELECT display_name FROM agent_profiles WHERE agent_id=%s", (target_agent_id,))
        to_display_name = to_profile_results[0]['display_name'] if to_profile_results else None
        
        to_info = {
            "role": to_role,
            "display_name": to_display_name or to_role.capitalize()
        }
        
        meta = None
        if meta_json:
            try:
                meta = json.loads(meta_json)
                log(f"Meta JSON parsed successfully: {len(str(meta))} characters")
            except json.JSONDecodeError:
                meta = {"raw": meta_json}
                log("Meta JSON parse failed, using raw value")
        else:
            log("No meta JSON provided")
        message_id = gateway.conn.create("""
            INSERT INTO watercooler_messages 
            (from_agent_id, to_agent_id, kind, content, meta)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            from_agent_id,
            target_agent_id,
            'message',
            message,
            json.dumps(meta) if meta else None
        ))
        if message_id is None:
            warn("Failed to insert message")
            raise ValueError("Failed to insert message")
        log(f"Message inserted: id={message_id}, from={from_agent_id}, to={target_agent_id}")
        
        queue_id = gateway.conn.create("""
            INSERT INTO watercooler_queue_dm (agent_id, message_id, queued_ts)
            VALUES (%s, %s, NOW(6))
        """, (target_agent_id, message_id))
        if queue_id is None:
            warn("Failed to queue message")
            raise ValueError("Failed to queue message")
        log(f"Message queued for agent {target_agent_id}")
        message_data = {
            "queue_id": None,
            "agent_id": target_agent_id,
            "message_id": message_id,
            "queued_ts": datetime.now().isoformat(sep=" ", timespec="microseconds"),
            "channel_name": "dm",
            "occurred_ts": datetime.now().isoformat(sep=" ", timespec="microseconds"),
            "from_agent_id": from_agent_id,
            "to_agent_id": target_agent_id,
            "kind": "message",
            "content": message,
            "meta": meta,
            "from_display_name": from_info['display_name']
        }
        ensure_iso_timestamps(message_data, ['queued_ts', 'occurred_ts'])
        result = {
            "agent_id": target_agent_id,
            "channels": ["dm"],
            "message_count": 1,
            "messages": [message_data],
            "timestamp": datetime.now().isoformat(sep=" ", timespec="microseconds")
        }
        log(f"Gossip completed: message_id={message_id}, content_length={len(message)}")
        log(f"Gossip command completed successfully: message_count={result.get('message_count', 0)}")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
    except ValueError as e:
        warn(f"Gossip command failed with ValueError: {e}")
        report_error("action", str(e))
        trace_out()
        return False
