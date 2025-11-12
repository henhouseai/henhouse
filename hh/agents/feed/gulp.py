from __future__ import annotations
import argparse
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.connection import r_query
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.agents.feed.feed_utils import validate_channels
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

def generate_gulp_filename(conn, agent_id: int) -> str:
    trace_in()
    results = r_query(conn, """
        SELECT a.agent_key, a.role, ap.display_name 
        FROM agents a 
        LEFT JOIN agent_profiles ap ON ap.agent_id = a.id 
        WHERE a.id = %s
    """, (agent_id,))
    
    if results:
        r = results[0]
        agent_key = r.get("agent_key")
        role_name = r.get("role")
        display_name = r.get("display_name")
        if agent_key:
            base_name = agent_key
        elif display_name:
            base_name = display_name
        elif role_name:
            base_name = role_name.capitalize()
        else:
            base_name = "Agent"
    else:
        base_name = "Agent"
    
    base_name = base_name.replace(" ", "_")
    filename = f"bootstrap/agents/gulp/{base_name}.gulp"
    log(f"Generated filename for agent {agent_id}: {filename}")
    trace_out()
    return filename

@db_read
def gulp(conn, agent_id: int, channels: List[str], output_file: Optional[str] = None) -> Dict[str, Any]:
    trace_in()
    if not output_file:
        output_file = generate_gulp_filename(conn, agent_id)
    log(f"Gulp export: agent_id={agent_id}, channels={channels}, output_file={output_file}")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    query = """
        SELECT 
            wm.id as message_id,
            wm.occurred_ts,
            wm.from_agent_id,
            wm.to_agent_id,
            wm.kind,
            wm.content,
            wm.meta,
            ap.display_name as from_display_name,
            CASE 
                WHEN wm.from_agent_id = %s THEN 'sent'
                WHEN wm.to_agent_id = %s THEN 'received'
                ELSE 'unknown'
            END as direction
        FROM watercooler_messages wm
        LEFT JOIN agent_profiles ap ON ap.agent_id = wm.from_agent_id
        WHERE wm.from_agent_id = %s OR wm.to_agent_id = %s
        ORDER BY wm.occurred_ts ASC, wm.id ASC
    """
    combined_query = query
    combined_params = [agent_id, agent_id, agent_id, agent_id]
    rows = r_query(conn, combined_query, combined_params)
    log(f"Query executed: {len(rows)} messages found for export")
    gulp_data = {
        "agent_id": agent_id,
        "channels": channels,
        "export_timestamp": datetime.now().isoformat(sep=" ", timespec="microseconds"),
        "message_count": len(rows),
        "messages": rows
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(gulp_data, f, indent=2, default=str)
    log(f"Gulp data written to file: {output_file}")
    table_of_contents = []
    for i, row in enumerate(rows[:10]):
        if row['direction'] == 'received':
            sender = row['from_display_name'] or f"agent {row['from_agent_id']}"
            direction_text = f"from {sender}"
        else:
            receiver = f"agent {row['to_agent_id']}"
            direction_text = f"to {receiver}"
        toc_entry = {
            "message_index": i + 1,
            "kind": row['kind'],
            "direction": direction_text,
            "content_preview": row['content'][:50] + "..." if len(row['content']) > 50 else row['content']
        }
        table_of_contents.append(toc_entry)
    log(f"Generated table of contents with {len(table_of_contents)} entries")
    result = {
        "agent_id": agent_id,
        "channels": channels,
        "output_file": output_file,
        "message_count": len(rows),
        "table_of_contents": table_of_contents,
        "export_timestamp": datetime.now().isoformat(sep=" ", timespec="microseconds")
    }
    log(f"Gulp export completed: {len(rows)} messages exported to {output_file}")
    trace_out()
    return result

@register_action('gulp')
@register_command('gulp')
def gulp(args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    channels = gateway.get_arg('channels')
    output_file = gateway.get_arg('output_file')
    
    log(f"Gulp command args: agent_id={agent_id}, badge_ts={badge_ts}, channels={channels}, output_file={output_file}")
    
    if not agent_id:
        warn("Agent ID is required for gulp command")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    try:
        channels = validate_channels(channels)
        result = gulp(agent_id=agent_id, channels=channels, output_file=output_file)
        log(f"Gulp command completed successfully: {result.get('message_count', 0)} messages exported")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
    except ValueError as e:
        warn(f"Gulp command validation error: {str(e)}")
        report_error("action", str(e))
        trace_out()
        return False
    except Exception as e:
        warn(f"Gulp command export error: {str(e)}")
        report_error("backend", str(e))
        trace_out()
        return False
