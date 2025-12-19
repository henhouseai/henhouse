from __future__ import annotations
from typing import Dict, List, Union, TypedDict, Optional, Any
from hh.agents.feed.feed_utils import bulk_add_to_queue, bulk_remove_from_queue
from hh.agents.feed.subscription_spec import SubscriptionSpec, SUBSCRIPTION_SPECS
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

class TargetInfo(TypedDict):
    target_id: int
    target_type: str
    target_title: str

class QueueResult(TypedDict, total=False):
    messages_queued: int
    messages_removed: int
    total_characters: int

class SubscriptionResponse(TypedDict, total=False):
    subscription_created: bool
    subscription_removed: bool
    target_id: int
    target_type: str
    target_title: str
    messages_queued: int
    messages_removed: int
    total_characters: int
    queue_table: str
    error: str
    message: str

def _require_target(spec: SubscriptionSpec, target_id: int) -> Union[TargetInfo, Dict[str, Union[str, int]]]:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    target_query = f"SELECT {spec.target_id_field}, {spec.target_title_field} FROM {spec.target_table} WHERE {spec.target_id_field}=%s"
    log(f"Querying target: {spec.key} {target_id}")
    target_results = gateway.conn.read(target_query, [target_id])
    if not target_results:
        warn(f"Target not found: {spec.key} {target_id}")
        trace_out()
        return {
            "error": f"{spec.key}_not_found",
            "target_id": target_id,  # type: ignore[dict-item]
            "target_type": spec.key,
            "target_title": "Unknown"
        }
    target_row = target_results[0]
    target_title = target_row[spec.target_title_field]
    log(f"Target found: {spec.key} {target_id} - {target_title}")
    trace_out()
    return {
        "target_id": target_id,
        "target_type": spec.key,
        "target_title": target_title
    }

def _ensure_subscription(spec: SubscriptionSpec, agent_id: int, target_id: int) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    subscription_id = gateway.conn.create(f"""
        INSERT IGNORE INTO {spec.subscription_table} (agent_id, {spec.link_id_field})
        VALUES (%s, %s)
    """, (agent_id, target_id))
    # Note: INSERT IGNORE returns 0 if duplicate, which is fine for this use case
    log(f"Ensured subscription: agent {agent_id} -> {spec.key} {target_id}")
    trace_out()

def _assert_subscription_exists(spec: SubscriptionSpec, agent_id: int, target_id: int) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    subscription_query = f"SELECT id FROM {spec.subscription_table} WHERE agent_id=%s AND {spec.link_id_field}=%s"
    log(f"Checking subscription exists: agent {agent_id} -> {spec.key} {target_id}")
    subscription_results = gateway.conn.read(subscription_query, [agent_id, target_id])
    if not subscription_results:
        warn(f"Subscription not found: agent {agent_id} -> {spec.key} {target_id}")
        trace_out()
        raise ValueError("not_subscribed")
    log(f"Subscription confirmed: agent {agent_id} -> {spec.key} {target_id}")
    trace_out()

def _collect_message_ids(spec: SubscriptionSpec, target_id: int, options: Dict[str, Union[str, bool]]) -> List[int]:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    if spec.message_query_factory:
        message_query = spec.message_query_factory(str(target_id))
        log("Using custom message query factory")
    else:
        message_query = f"""
            SELECT DISTINCT wm.id
            FROM {spec.link_table} wl
            JOIN watercooler_messages wm ON wm.id = wl.watercooler_message_id
            WHERE wl.{spec.link_id_field} = %s
        """
        log("Using default message query")
    params: List[Union[str, int]] = [target_id]
    if options.get("since_timestamp"):
        since_ts = options["since_timestamp"]
        if isinstance(since_ts, str):
            message_query += " AND wm.occurred_ts >= %s"
            params.append(since_ts)
        log(f"Added since_timestamp filter: {options['since_timestamp']}")
    elif options.get("new_only"):
        message_query += " AND wm.occurred_ts > NOW() - INTERVAL 1 HOUR"
        log("Added new_only filter (last hour)")
    log(f"Collecting messages for {spec.key} {target_id}")
    message_results = gateway.conn.read(message_query, params)
    message_ids = [row["id"] for row in message_results]
    log(f"Found {len(message_ids)} messages before filtering")
    if spec.message_filter_hook:
        original_count = len(message_ids)
        message_ids = [mid for mid in message_ids if spec.message_filter_hook({"id": mid})]
        log(f"Applied message filter: {original_count} -> {len(message_ids)} messages")
    trace_out()
    return message_ids

def _delete_subscription(spec: SubscriptionSpec, agent_id: int, target_id: int) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        raise ValueError("No gateway or connection available")
    affected = gateway.conn.delete(f"""
        DELETE FROM {spec.subscription_table} 
        WHERE agent_id=%s AND {spec.link_id_field}=%s
    """, (agent_id, target_id))
    if affected == 0:
        warn(f"No subscription found to delete: agent {agent_id} -> {spec.key} {target_id}")
    else:
        log(f"Deleted subscription: agent {agent_id} -> {spec.key} {target_id}")
    trace_out()

def _success_payload(operation: str, spec: SubscriptionSpec, target: Union[TargetInfo, Dict[str, Union[str, int]]], queue_result: Union[QueueResult, Dict[str, Any]]) -> SubscriptionResponse:
    trace_in()
    # Extract target info safely
    if isinstance(target, dict):
        target_id_val = target.get("target_id", 0)
        target_type_val_raw = target.get("target_type", "unknown")
        target_type_val = str(target_type_val_raw) if target_type_val_raw is not None else "unknown"
        target_title_val_raw = target.get("target_title", "Unknown")
        target_title_val = str(target_title_val_raw) if target_title_val_raw is not None else "Unknown"
    else:
        target_id_val = target["target_id"]
        target_type_val = target["target_type"]
        target_title_val = target["target_title"]
    
    # Extract queue result info safely
    if isinstance(queue_result, dict):
        messages_queued_val = queue_result.get("messages_queued", 0)
        messages_removed_val = queue_result.get("messages_removed", 0)
        total_characters_val = queue_result.get("total_characters", 0)
    else:
        messages_queued_val = getattr(queue_result, "messages_queued", 0)
        messages_removed_val = getattr(queue_result, "messages_removed", 0)
        total_characters_val = getattr(queue_result, "total_characters", 0)
    
    if operation == "subscription_created":
        result: SubscriptionResponse = {
            "subscription_created": True,
            "target_id": target_id_val,  # type: ignore[typeddict-item]
            "target_type": target_type_val,
            "target_title": target_title_val,
            "messages_queued": messages_queued_val,
            "total_characters": total_characters_val,
            "queue_table": spec.queue_table
        }
        log(f"Created subscription payload: {target_type_val} {target_id_val}, {messages_queued_val} messages")
    elif operation == "subscription_removed":
        result = {
            "subscription_removed": True,
            "target_id": target_id_val,  # type: ignore[typeddict-item]
            "target_type": target_type_val,
            "target_title": target_title_val,
            "messages_removed": messages_removed_val,
            "total_characters": total_characters_val,
            "queue_table": spec.queue_table
        }
        log(f"Removed subscription payload: {target_type_val} {target_id_val}, {messages_removed_val} messages")
    else:
        warn(f"Unknown operation: {operation}")
        trace_out()
        raise ValueError(f"Unknown operation: {operation}")
    trace_out()
    return result  # type: ignore[return-value]

def subscribe(spec_key: str, *, agent_id: int, target_id: int, options: Dict[str, Union[str, bool]]) -> SubscriptionResponse:
    trace_in()
    try:
        if spec_key not in SUBSCRIPTION_SPECS:
            warn(f"Unknown subscription type: {spec_key}")
            trace_out()
            return {"error": f"unknown_subscription_type: {spec_key}"}
        spec = SUBSCRIPTION_SPECS[spec_key]
        log(f"Subscribing agent {agent_id} to {spec_key} {target_id}")
        target = _require_target(spec, target_id)
        if isinstance(target, dict) and "error" in target:
            trace_out()
            return target  # type: ignore[return-value]
        _ensure_subscription(spec, agent_id, target_id)
        message_ids = _collect_message_ids(spec, target_id, options)
        log(f"Adding {len(message_ids)} messages to queue")
        queue_result = bulk_add_to_queue(agent_id, message_ids, spec.queue_table)
        result = _success_payload("subscription_created", spec, target, queue_result)
        trace_out()
        return result
        
    except Exception as e:
        error_str = str(e)
        warn(f"Subscription failed: {error_str}")
        if "Duplicate entry" in error_str and "for key" in error_str:
            duplicate_spec: Optional[SubscriptionSpec] = SUBSCRIPTION_SPECS.get(spec_key, None)
            target_type = duplicate_spec.key if duplicate_spec else spec_key
            target_title_raw = target.get("target_title", "Unknown") if isinstance(target, dict) and "target" in locals() else "Unknown"
            target_title: str = str(target_title_raw) if target_title_raw is not None else "Unknown"
            log(f"Duplicate subscription detected: {target_type} {target_id}")
            trace_out()
            return {
                "error": "already_subscribed",
                "target_id": target_id,
                "target_type": target_type,
                "target_title": target_title,
                "message": f"Already subscribed to {target_type} {target_id}. Use unsubscribe first if you want to resubscribe."
            }
        else:
            trace_out()
            return {"error": f"subscription_failed: {error_str}"}

def unsubscribe(spec_key: str, *, agent_id: int, target_id: int) -> SubscriptionResponse:
    trace_in()
    try:
        if spec_key not in SUBSCRIPTION_SPECS:
            warn(f"Unknown subscription type: {spec_key}")
            trace_out()
            return {"error": f"unknown_subscription_type: {spec_key}"}
        spec = SUBSCRIPTION_SPECS[spec_key]
        log(f"Unsubscribing agent {agent_id} from {spec_key} {target_id}")
        target = _require_target(spec, target_id)
        if isinstance(target, dict) and "error" in target:
            trace_out()
            return target  # type: ignore[return-value]
        try:
            _assert_subscription_exists(spec, agent_id, target_id)
        except ValueError as e:
            if str(e) == "not_subscribed":
                warn(f"Not subscribed: agent {agent_id} -> {spec.key} {target_id}")
                trace_out()
                target_title_str = str(target["target_title"]) if isinstance(target, dict) else target["target_title"]
                return {
                    "error": "not_subscribed",
                    "target_id": target_id,
                    "target_type": spec.key,
                    "target_title": target_title_str,
                    "message": f"Not subscribed to {spec.key} {target_id}. Nothing to unsubscribe from."
                }
            else:
                raise
        log(f"Removing messages from queue for {spec.key} {target_id}")
        queue_result = bulk_remove_from_queue(agent_id, target_id, spec.key, spec.queue_table)
        _delete_subscription(spec, agent_id, target_id)
        result = _success_payload("subscription_removed", spec, target, queue_result)
        trace_out()
        return result
    except Exception as e:
        warn(f"Unsubscription failed: {str(e)}")
        trace_out()
        return {"error": f"unsubscription_failed: {str(e)}"}
