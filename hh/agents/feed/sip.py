from __future__ import annotations
import json
from typing import List, Dict, Any
from hh.gateway.connection.decorators import db_write
from hh.gateway.connection.connection import r_query, d_query
from hh.gateway.connection.utils import ensure_iso_timestamps
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.agents.feed.feed_utils import validate_channels, generate_sip_json
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

@db_write
def sip_messages(conn, agent_id: int, channels: List[str]) -> Dict[str, Any]:
    trace_in()
    channel_queries = []
    params = []
    for channel in channels:
        table_name = f"watercooler_queue_{channel}"
        query = f"""
            SELECT 
                wq.id as queue_id,
                wq.agent_id,
                wq.message_id,
                wq.queued_ts,
                '{channel}' as channel_name,
                wm.id as message_id,
                wm.occurred_ts,
                wm.from_agent_id,
                wm.to_agent_id,
                wm.kind,
                wm.content,
                wm.meta,
                ap.display_name as from_display_name
            FROM {table_name} wq
            JOIN watercooler_messages wm ON wq.message_id = wm.id
            LEFT JOIN agent_profiles ap ON ap.agent_id = wm.from_agent_id
            WHERE wq.agent_id = %s
            ORDER BY wq.queued_ts ASC, wq.id ASC
        """
        channel_queries.append(query)
        params.append(agent_id)
    log(f"Built {len(channel_queries)} channel queries for agent {agent_id}, channels: {channels}")
    if len(channel_queries) == 1:
        combined_query = channel_queries[0]
        combined_params = params
    else:
        combined_query = " UNION ALL ".join([f"({q})" for q in channel_queries])
        combined_query += " ORDER BY queued_ts ASC, queue_id ASC"
        combined_params = params
    rows = r_query(conn, combined_query, combined_params)
    log(f"Query executed: {len(rows)} rows returned")
    messages = []
    queue_ids_by_channel = {}
    for row in rows:
        message = dict(row)
        channel_name = message['channel_name']
        queue_id = message['queue_id']
        if channel_name not in queue_ids_by_channel:
            queue_ids_by_channel[channel_name] = []
        queue_ids_by_channel[channel_name].append(queue_id)
        ensure_iso_timestamps(message, ['queued_ts', 'occurred_ts'])
        if message.get('meta'):
            try:
                message['meta'] = json.loads(message['meta'])
                log(f"Meta JSON parsed successfully for message {queue_id}")
            except (json.JSONDecodeError, TypeError):
                message['meta'] = {"raw": message['meta']}
                log(f"Meta JSON parse failed for message {queue_id}, using raw value")
        messages.append(message)
    
    # Delete messages from queues
    for channel, queue_ids in queue_ids_by_channel.items():
        if queue_ids:  # Only delete if there are messages
            placeholders = ','.join(['%s'] * len(queue_ids))
            delete_query = f"DELETE FROM watercooler_queue_{channel} WHERE id IN ({placeholders})"
            deleted_count = d_query(conn, delete_query, queue_ids)
            log(f"Deleted {deleted_count} messages from channel {channel}")
    log(f"Sip completed: {len(messages)} messages processed for agent {agent_id}")
    trace_out()
    return generate_sip_json(messages, agent_id, channels)

@register_action('sip')
@register_command('sip')
def sip(args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    agent_id = gateway.get_arg('agent_id')
    badge_ts = gateway.get_arg('badge_ts')
    channels = gateway.get_arg('channels')
    log(f"Sip command args: agent_id={agent_id}, badge_ts={badge_ts}, channels={channels}")
    if not agent_id:
        warn("Agent ID is required for sip command")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    try:
        channels = validate_channels(channels)
        result = sip_messages(agent_id=agent_id, channels=channels)
        log(f"Sip command completed successfully: {result.get('message_count', 0)} messages")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
    except ValueError as e:
        warn(f"Sip command validation error: {str(e)}")
        report_error("action", str(e))
        trace_out()
        return False
