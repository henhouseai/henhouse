from __future__ import annotations
import json
from typing import List, Dict, Any, Optional
from hh.gateway.connection.utils import iso_now, ensure_iso_timestamps
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.agents.feed.feed_utils import validate_channels
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

@register_action('peek')
@register_command('peek')
def peek(args: List[str] = None) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return False    
    agent_id = gateway.get_arg('agent_id')
    channels = gateway.get_arg('channels')
    deep_mode = gateway.get_arg('deep')
    log(f"Peek command args: agent_id={agent_id}, channels={channels}, deep_mode={deep_mode}")
    try:
        channels = validate_channels(channels)
        channel_queries = []
        params = []
        for channel in channels:
            table_name = f"watercooler_queue_{channel}"
            query = f"SELECT watercooler_queue_{channel}.id as queue_id, watercooler_queue_{channel}.agent_id, watercooler_queue_{channel}.message_id, watercooler_queue_{channel}.queued_ts, '{channel}' as channel_name, watercooler_messages.occurred_ts, watercooler_messages.from_agent_id, watercooler_messages.to_agent_id, watercooler_messages.kind, watercooler_messages.content, watercooler_messages.meta, agents.agent_key FROM watercooler_queue_{channel} JOIN watercooler_messages ON watercooler_queue_{channel}.message_id = watercooler_messages.id LEFT JOIN agents ON agents.id = watercooler_messages.from_agent_id"
            if agent_id is not None:
                query += f" WHERE watercooler_queue_{channel}.agent_id = %s"
                params.append(agent_id)
            query += f" ORDER BY watercooler_queue_{channel}.queued_ts ASC, watercooler_queue_{channel}.id ASC"
            channel_queries.append(query)
        log(f"Built {len(channel_queries)} channel queries for channels: {channels}")
        if len(channel_queries) == 1:
            combined_query = channel_queries[0]
            combined_params = params
        else:
            combined_query = " UNION ALL ".join([f"({q})" for q in channel_queries])
            combined_query += " ORDER BY queued_ts ASC, queue_id ASC"
            combined_params = params
        rows = gateway.conn.read(combined_query, combined_params)
        log(f"Query executed: {len(rows)} rows returned")
        messages = []
        for row in rows:
            message = dict(row)
            ensure_iso_timestamps(message, ['queued_ts', 'occurred_ts'])
            full_message_json = {}
            for key, value in [
                ("queue_id", message.get('queue_id')),
                ("agent_id", message.get('agent_id')),
                ("message_id", message.get('message_id')),
                ("queued_ts", message.get('queued_ts')),
                ("channel_name", message.get('channel_name')),
                ("agent_key", message.get('agent_key')),
                ("occurred_ts", message.get('occurred_ts')),
                ("from_agent_id", message.get('from_agent_id')),
                ("to_agent_id", message.get('to_agent_id')),
                ("kind", message.get('kind')),
                ("content", message.get('content')),
                ("meta", message.get('meta'))
            ]:
                if value is not None:
                    full_message_json[key] = str(value) if not isinstance(value, (dict, list)) else value
            json_string = json.dumps(full_message_json, ensure_ascii=False)
            character_count = len(json_string)
            if not deep_mode:
                log(f"Processing message in summary mode: character_count={character_count}")
                summary_message = {
                    "character_count": character_count
                }
                for key, value in [
                    ("queue_id", message.get('queue_id')),
                    ("agent_id", message.get('agent_id')),
                    ("message_id", message.get('message_id')),
                    ("queued_ts", message.get('queued_ts')),
                    ("occurred_ts", message.get('occurred_ts')),
                    ("channel_name", message.get('channel_name')),
                    ("from_display_name", message.get('agent_key')),
                    ("from_agent_id", message.get('agent_id')),
                    ("kind", message.get('kind'))
                ]:
                    if value is not None:
                        summary_message[key] = str(value) if not isinstance(value, (dict, list)) else value
                messages.append(summary_message)
            else:
                log(f"Processing message in deep mode: queue_id={message.get('queue_id')}")
                filtered_message = {}
                for k, v in message.items():
                    if v is not None:
                        filtered_message[k] = str(v) if not isinstance(v, (dict, list)) else v
                messages.append(filtered_message)
        result = {
            "channels": channels,
            "message_count": len(messages),
            "messages": messages,
            "timestamp": iso_now(),
        }
        if agent_id is not None:
            result["agent_id"] = agent_id
        log(f"Peek completed: {len(messages)} messages for {len(channels)} channels")
        log(f"Peek command completed successfully: {result.get('message_count', 0)} messages")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
    except ValueError as e:
        warn(f"Peek command validation error: {str(e)}")
        report_error("action", str(e))
        trace_out()
        return False
