from __future__ import annotations
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from hh.gateway.connection.utils import ensure_iso_timestamps
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

VALID_CHANNELS = ['docket', 'ask', 'task', 'step', 'sidecar', 'keyword', 'agent', 'operator', 'dm']

def validate_channels(channels_str: Optional[str]) -> List[str]:
    trace_in()
    if not channels_str:
        log("No channels specified, returning all valid channels")
        trace_out()
        return VALID_CHANNELS
    channels = [ch.strip() for ch in channels_str.split(',')]
    invalid_channels = [ch for ch in channels if ch not in VALID_CHANNELS]
    if invalid_channels:
        warn(f"Invalid channels detected: {invalid_channels}")
        trace_out()
        raise ValueError(f"Invalid channels: {invalid_channels}")
    log(f"Channels validated successfully: {channels}")
    trace_out()
    return channels

def generate_sip_json(messages, agent_id, channels):
    trace_in()
    if isinstance(channels, str):
        channels = [channels]
    log(f"Generating sip JSON for agent {agent_id}, {len(messages)} messages, channels: {channels}")
    result = {
        "agent_id": agent_id,
        "channels": channels,
        "message_count": len(messages),
        "messages": messages,
        "timestamp": datetime.now().isoformat(sep=" ", timespec="microseconds")
    }
    trace_out()
    return result

def bulk_add_to_queue(agent_id: int, message_ids: List[int], queue_table: str) -> Dict[str, Any]:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    if not message_ids:
        log("No message IDs provided, returning empty result")
        trace_out()
        return {
            'messages_queued': 0,
            'total_characters': 0,
            'queue_table': queue_table
        }
    if not queue_table.startswith('watercooler_queue_'):
        warn(f"Invalid queue table format: {queue_table}")
        raise ValueError(f"Invalid queue table: {queue_table}")
    channel = queue_table.replace('watercooler_queue_', '')
    if channel not in VALID_CHANNELS:
        warn(f"Invalid channel: {channel}")
        raise ValueError(f"Invalid channel: {channel}")
    log(f"Bulk adding {len(message_ids)} messages to queue {queue_table} for agent {agent_id}")
    try:
        # Insert messages one by one (since we don't have executemany in our query methods)
        for msg_id in message_ids:
            queue_id = gateway.conn.create(f"""
                INSERT INTO {queue_table} (agent_id, message_id, queued_ts)
                VALUES (%s, %s, NOW(6))
            """, (agent_id, msg_id))
            if queue_id is None:
                warn(f"Failed to insert message {msg_id} into queue")
                raise Exception(f"Failed to insert message {msg_id} into queue")
        log(f"Inserted {len(message_ids)} messages into queue")
        
        # Retrieve the queued messages
        placeholders = ','.join(['%s'] * len(message_ids))
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
            FROM {queue_table} wq
            JOIN watercooler_messages wm ON wq.message_id = wm.id
            LEFT JOIN agent_profiles ap ON ap.agent_id = wm.from_agent_id
            WHERE wq.agent_id = %s AND wq.message_id IN ({placeholders})
            ORDER BY wq.queued_ts ASC, wq.id ASC
        """
        rows = gateway.conn.read(query, [agent_id] + message_ids)
        log(f"Retrieved {len(rows)} queued messages")
        messages = []
        for row in rows:
            message = dict(row)
            ensure_iso_timestamps(message, ['queued_ts', 'occurred_ts'])
            if message.get('meta'):
                try:
                    message['meta'] = json.loads(message['meta'])
                except (json.JSONDecodeError, TypeError):
                    message['meta'] = {"raw": message['meta']}
            messages.append(message)
        sip_json = generate_sip_json(messages, agent_id, channel)
        json_string = json.dumps(sip_json, ensure_ascii=False)
        total_characters = len(json_string)
        log(f"Bulk add completed: {len(message_ids)} messages queued, {total_characters} characters")
        trace_out()
        return {
            'messages_queued': len(message_ids),
            'total_characters': total_characters,
            'queue_table': queue_table
        }
    except Exception as e:
        warn(f"Bulk add failed: {str(e)}")
        raise e

def bulk_remove_from_queue(agent_id: int, target_id: int, target_type: str, queue_table: str) -> Dict[str, Any]:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    if not queue_table.startswith('watercooler_queue_'):
        warn(f"Invalid queue table format: {queue_table}")
        raise ValueError(f"Invalid queue table: {queue_table}")
    channel = queue_table.replace('watercooler_queue_', '')
    if channel not in VALID_CHANNELS:
        warn(f"Invalid channel: {channel}")
        raise ValueError(f"Invalid channel: {channel}")
    log(f"Bulk removing messages for target {target_type}:{target_id} from queue {queue_table} for agent {agent_id}")
    try:
        # Determine the query based on target_type
        if target_type == 'step':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_step wls
                JOIN watercooler_messages wm ON wm.id = wls.watercooler_message_id
                WHERE wls.step_id = %s
            """
        elif target_type == 'ask':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_ask wla
                JOIN watercooler_messages wm ON wm.id = wla.watercooler_message_id
                WHERE wla.ask_id = %s
            """
        elif target_type == 'task':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_task wlt
                JOIN watercooler_messages wm ON wm.id = wlt.watercooler_message_id
                WHERE wlt.task_id = %s
            """
        elif target_type == 'operator':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_operator wlo
                JOIN watercooler_messages wm ON wm.id = wlo.watercooler_message_id
                WHERE wlo.operator_id = %s
            """
        elif target_type == 'keyword':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_keyword wlk
                JOIN watercooler_messages wm ON wm.id = wlk.watercooler_message_id
                WHERE wlk.keyword_id = %s
            """
        elif target_type == 'sidecar':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_sidecar wls
                JOIN watercooler_messages wm ON wm.id = wls.watercooler_message_id
                WHERE wls.sidecar_id = %s
            """
        elif target_type == 'agent':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_agent wla
                JOIN watercooler_messages wm ON wm.id = wla.watercooler_message_id
                WHERE wla.agent_id = %s
            """
        elif target_type == 'docket':
            query = """
                SELECT DISTINCT wm.id
                FROM wc_microlog_link_docket wld
                JOIN watercooler_messages wm ON wm.id = wld.watercooler_message_id
                WHERE wld.docket_id = %s
            """
        else:
            warn(f"Invalid target_type: {target_type}")
            raise ValueError(f"Invalid target_type: {target_type}")
        
        message_rows = gateway.conn.read(query, (target_id,))
        message_ids = [row["id"] for row in message_rows]
        log(f"Found {len(message_ids)} messages linked to {target_type}:{target_id}")
        if not message_ids:
            log("No messages found to remove")
            return {
                'messages_removed': 0,
                'total_characters': 0,
                'queue_table': queue_table
            }
        
        # Get the messages before deletion
        placeholders = ','.join(['%s'] * len(message_ids))
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
            FROM {queue_table} wq
            JOIN watercooler_messages wm ON wq.message_id = wm.id
            LEFT JOIN agent_profiles ap ON ap.agent_id = wm.from_agent_id
            WHERE wq.agent_id = %s AND wq.message_id IN ({placeholders})
            ORDER BY wq.queued_ts ASC, wq.id ASC
        """
        rows = gateway.conn.read(query, [agent_id] + message_ids)
        log(f"Retrieved {len(rows)} queued messages for removal")
        messages = []
        for row in rows:
            message = dict(row)
            ensure_iso_timestamps(message, ['queued_ts', 'occurred_ts'])
            if message.get('meta'):
                try:
                    message['meta'] = json.loads(message['meta'])
                except (json.JSONDecodeError, TypeError):
                    message['meta'] = {"raw": message['meta']}
            messages.append(message)
        sip_json = generate_sip_json(messages, agent_id, channel)
        json_string = json.dumps(sip_json, ensure_ascii=False)
        total_characters = len(json_string)
        
        # Delete the messages
        delete_query = f"""
            DELETE wq FROM {queue_table} wq
            WHERE wq.agent_id = %s AND wq.message_id IN ({placeholders})
        """
        messages_removed = gateway.conn.delete(delete_query, [agent_id] + message_ids)
        log(f"Bulk remove completed: {messages_removed} messages removed, {total_characters} characters")
        trace_out()
        return {
            'messages_removed': messages_removed,
            'total_characters': total_characters,
            'queue_table': queue_table
        }
    except Exception as e:
        warn(f"Bulk remove failed: {str(e)}")
        raise e
