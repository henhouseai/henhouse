from __future__ import annotations
from datetime import datetime
from typing import List, TypedDict, Optional, Dict, Union
from hh.render.render import render_block, break_section, FieldConfig, TableData
from hh.render.config.config import dc, safe_str
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

class AgentInfo(TypedDict, total=False):
    id: int
    agent_key: str
    role: str
    status: str
    badge_ts: str
    created_at: str
    updated_at: str
    last_punch_in: str
    last_punch_out: str

class SubscriptionInfo(TypedDict, total=False):
    id: int
    agent_id: int
    target_id: int
    target_type: str
    target_title: str
    created_at: str

class LinkedItemInfo(TypedDict, total=False):
    id: int
    agent_id: int
    item_id: int
    item_type: str
    item_title: str
    created_at: str

class ActivityInfo(TypedDict, total=False):
    id: int
    agent_id: int
    activity_type: str
    description: str
    timestamp: str

def validate_agent_identity(agent_id: int, badge_ts: str) -> Optional[Dict[str, Union[str, int]]]:
    """Validate agent identity and return agent data if valid."""
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return None
    query = "SELECT id, role, badge_ts, status, agent_key FROM agents WHERE id=%s AND badge_ts=%s"
    results = gateway.conn.read(query, [agent_id, badge_ts])
    if results:
        log(f"Agent identity validated for agent_id={agent_id}")
        trace_out()
        return results[0]
    else:
        warn(f"Agent identity not found for agent_id={agent_id}")
        trace_out()
        return None

def render_subscription_details(subscriptions: List[SubscriptionInfo], lines: List[str]) -> None:
    trace_in()
    debug(f"render_subscription_details called with subscriptions type: {type(subscriptions)}")
    if not subscriptions:
        log("No subscriptions to render, skipping subscription details")
        trace_out()
        return
    block = 'breakdown'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        subscriptions = subscriptions or []
        debug(f"After null check, subscriptions type: {type(subscriptions)}, length: {len(subscriptions) if subscriptions is not None else 'None'}")
        log(f"Rendering {len(subscriptions)} subscription details")
        subscription_data = TableData()
        if not gateway.is_no('header'):
            subscription_data.add_row(
                'subscriptions',
                subscription_id=dc('l_id'),
                subscription_title=dc('l_title')
            )
        for sub in subscriptions:
            sub_type = sub.get('type', 'Unknown')
            field_type = f'subscription_{sub_type}'
            log(f"Processing subscription: type={sub_type}, target_id={sub.get('target_id', 'Unknown')}")
            
            subscription_data.add_row(
                field_type,
                subscription_id=str(sub.get('target_id', 'Unknown')) if not gateway.is_no('subscription_id') else None,
                subscription_title=safe_str(sub.get('target_title', 'Unknown')) if not gateway.is_no('subscription_title') else None
            )
        lines.append(render_block(
            subscription_data,
            FieldConfig()
                .add_simple(['subscriptions'])
                .add_group(['subscription_ask', 'subscription_task', 'subscription_step', 'subscription_docket', 'subscription_sidecar', 'subscription_keyword', 'subscription_agent', 'subscription_operator'], 'subscription'),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_linked_items_details(linked_items: List[LinkedItemInfo], lines: List[str]) -> None:
    trace_in()
    debug(f"render_linked_items_details called with linked_items type: {type(linked_items)}")
    if not linked_items:
        log("No linked items to render, skipping linked items details")
        trace_out()
        return
    block = 'breakdown'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        linked_items = linked_items or []
        debug(f"After null check, linked_items type: {type(linked_items)}, length: {len(linked_items) if linked_items is not None else 'None'}")
        log(f"Rendering {len(linked_items)} linked items details")
        linked_items_data = TableData()
        if not gateway.is_no('header'):
            linked_items_data.add_row(
                'linked_items',
                linked_item_id=dc('l_id'),
                linked_item_title=dc('l_title'),
                linked_item_timestamp=dc('l_timestamp')
            )
        for item in linked_items:
            item_type = item.get('type', 'Unknown')
            field_type = f'linked_item_{item_type}'
            log(f"Processing linked item: type={item_type}, target_id={item.get('target_id', 'Unknown')}")
            
            # Handle timestamp formatting
            timestamp_value = None
            if not gateway.is_no('linked_item_timestamp'):
                occurred_ts = item.get('occurred_ts', '')
                if occurred_ts:
                    try:
                        dt = datetime.fromisoformat(occurred_ts.replace('Z', '+00:00'))
                        timestamp_value = dt.strftime('%Y-%m-%d %H:%M:%S')
                        log(f"Formatted timestamp: {occurred_ts} -> {timestamp_value}")
                    except:
                        log(f"Failed to parse timestamp: {occurred_ts}, using original")
                        timestamp_value = occurred_ts
                else:
                    timestamp_value = 'Unknown'
            
            linked_items_data.add_row(
                field_type,
                linked_item_id=str(item.get('target_id', 'Unknown')) if not gateway.is_no('linked_item_id') else None,
                linked_item_title=safe_str(item.get('target_title', 'Unknown')) if not gateway.is_no('linked_item_title') else None,
                linked_item_timestamp=timestamp_value
            )
        lines.append(render_block(
            linked_items_data,
            FieldConfig()
                .add_simple(['linked_items'])
                .add_group(['linked_item_ask', 'linked_item_task', 'linked_item_step', 'linked_item_docket', 'linked_item_sidecar', 'linked_item_keyword', 'linked_item_agent', 'linked_item_operator'], 'linked_item'),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_activity_details(activities: List[ActivityInfo], lines: List[str], block_type: str = 'activity') -> None:
    trace_in()
    debug(f"render_activity_details called with activities type: {type(activities)}, block_type: {block_type}")
    block = block_type
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no(block):
        activities = activities or []
        debug(f"After null check, activities type: {type(activities)}, length: {len(activities) if activities is not None else 'None'}")
        log(f"Rendering {len(activities)} activity details with block_type={block_type}")
        for activity in activities:
            activity_data = TableData()
            activity_id = activity.get('id')
            activity_kind = activity.get('kind')
            log(f"Processing activity: id={activity_id}, kind={activity_kind}")
            
            if activity_id:
                activity_data.add_row(
                    'activity_id',
                    value=str(activity_id)
                )
            if activity_kind:
                activity_data.add_row(
                    'activity_kind',
                    value=safe_str(activity_kind)
                )
            if activity.get('occurred_ts'):
                activity_data.add_row(
                    'activity_timestamp',
                    value=safe_str(activity.get('occurred_ts'))
                )
            if activity.get('content'):
                activity_data.add_row(
                    'activity_content',
                    value=safe_str(activity.get('content'))
                )
            if activity_data.num_rows() > 0:
                log(f"Rendering activity block with {activity_data.num_rows()} fields")
                lines.append(render_block(
                    activity_data,
                    FieldConfig()
                        .add_group(['activity_id', 'activity_kind', 'activity_timestamp', 'activity_content'], 'activity'),
                    table_overrides={'margin_l': 6},
                    block_type=block
                ))
            if not gateway.is_no('meta'):
                meta = activity.get('meta')
                if meta is not None:
                    log("Rendering activity meta block")
                    lines.append(render_block(
                        meta,
                        block_type='meta'
                    ))
                else:
                    log("No meta data to render for activity")
            break_section(lines)
    trace_out()
