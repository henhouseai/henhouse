from __future__ import annotations
from typing import TypedDict
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.utils import ensure_iso_timestamps
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
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

class AgentListResponse(TypedDict, total=False):
    agents: list
    count: int
    status: str

@register_action('agent_list')
@register_command('agent_list')
@db_read
def agent_list(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False  
    try:
        role = gateway.get_arg('role')
        status = gateway.get_arg('status')
        ask_id = gateway.get_arg('ask_id')
        task_id = gateway.get_arg('task_id')
        step_id = gateway.get_arg('step_id')
        deep_mode = gateway.get_arg('deep')
        limit = gateway.get_arg('limit')
        log(f"Processing agent list with filters: role={role}, status={status}, ask_id={ask_id}, task_id={task_id}, step_id={step_id}, deep_mode={deep_mode}, limit={limit}")
        base_query = """
            SELECT DISTINCT a.id, a.agent_key, a.role, a.status, a.created_at,
                   a.terminated, a.gate_status, a.gate_started_ts, a.session_id
            FROM agents a
        """
        conditions = []
        params = []
        if status:
            conditions.append("a.status = %s")
            params.append(status)
        else:
            conditions.append("a.status = 'active'")
        if role:
            conditions.append("a.role = %s")
            params.append(role)
        if ask_id or task_id or step_id:
            activity_conditions = []
            if ask_id:
                activity_conditions.append("EXISTS (SELECT 1 FROM wc_microlog_link_ask wla WHERE wla.watercooler_message_id = wm.id AND wla.ask_id = %s)")
                params.append(ask_id)
            if task_id:
                activity_conditions.append("EXISTS (SELECT 1 FROM wc_microlog_link_task wlt WHERE wlt.watercooler_message_id = wm.id AND wlt.task_id = %s)")
                params.append(task_id)
            if step_id:
                activity_conditions.append("EXISTS (SELECT 1 FROM wc_microlog_link_step wls WHERE wls.watercooler_message_id = wm.id AND wls.step_id = %s)")
                params.append(step_id)
            if activity_conditions:
                conditions.append(f"EXISTS (SELECT 1 FROM watercooler_messages wm WHERE wm.from_agent_id = a.id AND {' OR '.join(activity_conditions)})")
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        base_query += " ORDER BY a.created_at DESC"
        agents = r_query(conn, base_query, params)
        log(f"Found {len(agents)} agents from database query")
        for agent in agents:
            ensure_iso_timestamps(agent, ['created_at'])
        if deep_mode:
            log(f"Deep mode enabled, loading additional data for {len(agents)} agents")
            for agent in agents:
                agent_id = agent['id']
                activity_query = """
                    SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts
                    FROM watercooler_messages wm
                    WHERE wm.from_agent_id = %s
                    ORDER BY occurred_ts DESC
                    LIMIT 10
                """
                activities = r_query(conn, activity_query, [agent_id])
                log(f"Loaded {len(activities)} recent activities for agent {agent_id}")
                for activity in activities:
                    ensure_iso_timestamps(activity, ['occurred_ts'])
                agent['recent_activity'] = activities
                subscriptions_query = """
                    WITH agent_subscriptions AS (
                        SELECT %s as agent_id
                    )
                    SELECT 'ask' as type, sa.ask_id as target_id,
                           a.title as target_title, a.status as target_status
                    FROM subscription_ask sa
                    LEFT JOIN asks a ON sa.ask_id = a.id
                    CROSS JOIN agent_subscriptions
                    WHERE sa.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'task' as type, st.task_id as target_id,
                           t.title as target_title, t.status as target_status
                    FROM subscription_task st
                    LEFT JOIN tasks t ON st.task_id = t.id
                    CROSS JOIN agent_subscriptions
                    WHERE st.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'step' as type, ss.step_id as target_id,
                           s.title as target_title, s.status as target_status
                    FROM subscription_step ss
                    LEFT JOIN steps s ON ss.step_id = s.id
                    CROSS JOIN agent_subscriptions
                    WHERE ss.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'sidecar' as type, ssc.sidecar_file_id as target_id,
                           sf.title as target_title, sf.path as target_path
                    FROM subscription_sidecar ssc
                    LEFT JOIN sidecar_files sf ON ssc.sidecar_file_id = sf.id
                    CROSS JOIN agent_subscriptions
                    WHERE ssc.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'docket' as type, sd.docket_id as target_id,
                           wd.title as target_title, wd.status as target_status
                    FROM subscription_docket sd
                    LEFT JOIN work_dockets wd ON sd.docket_id = wd.id
                    CROSS JOIN agent_subscriptions
                    WHERE sd.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'keyword' as type, sk.keyword_id as target_id,
                           k.keyword as target_title, k.status as target_status
                    FROM subscription_keyword sk
                    LEFT JOIN keywords k ON sk.keyword_id = k.id
                    CROSS JOIN agent_subscriptions
                    WHERE sk.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'agent' as type, sa.target_agent_id as target_id,
                           a.agent_key as target_title, a.status as target_status
                    FROM subscription_agent sa
                    LEFT JOIN agents a ON sa.target_agent_id = a.id
                    CROSS JOIN agent_subscriptions
                    WHERE sa.agent_id = agent_subscriptions.agent_id
                    UNION ALL
                    SELECT 'operator' as type, so.operator_id as target_id,
                           o.agent_key as target_title, o.status as target_status
                    FROM subscription_operator so
                    LEFT JOIN agents o ON so.operator_id = o.id
                    CROSS JOIN agent_subscriptions
                    WHERE so.agent_id = agent_subscriptions.agent_id
                """
                subscriptions = r_query(conn, subscriptions_query, [agent_id])
                log(f"Loaded {len(subscriptions)} subscriptions for agent {agent_id}")
                for sub in subscriptions:
                    ensure_iso_timestamps(sub, [])
                agent['subscriptions'] = subscriptions
                agent['subscription_count'] = len(subscriptions)
                linked_items_query = """
                    WITH agent_linked_items AS (
                        SELECT %s as agent_id
                    )
                    SELECT 'ask' as type, wla.ask_id as target_id, a.title as target_title, a.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_ask wla
                    JOIN watercooler_messages wm ON wla.watercooler_message_id = wm.id
                    LEFT JOIN asks a ON wla.ask_id = a.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'task' as type, wlt.task_id as target_id, t.title as target_title, t.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_task wlt
                    JOIN watercooler_messages wm ON wlt.watercooler_message_id = wm.id
                    LEFT JOIN tasks t ON wlt.task_id = t.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'step' as type, wls.step_id as target_id, s.title as target_title, s.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_step wls
                    JOIN watercooler_messages wm ON wls.watercooler_message_id = wm.id
                    LEFT JOIN steps s ON wls.step_id = s.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'docket' as type, wld.docket_id as target_id, wd.title as target_title, wd.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_docket wld
                    JOIN watercooler_messages wm ON wld.watercooler_message_id = wm.id
                    LEFT JOIN work_dockets wd ON wld.docket_id = wd.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'sidecar' as type, wlsf.sidecar_file_id as target_id, sf.title as target_title, sf.path as target_path,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_sidecar wlsf
                    JOIN watercooler_messages wm ON wlsf.watercooler_message_id = wm.id
                    LEFT JOIN sidecar_files sf ON wlsf.sidecar_file_id = sf.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'keyword' as type, wlk.keyword_id as target_id, k.keyword as target_title, k.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_keyword wlk
                    JOIN watercooler_messages wm ON wlk.watercooler_message_id = wm.id
                    LEFT JOIN keywords k ON wlk.keyword_id = k.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'agent' as type, wlaa.agent_id as target_id, a.agent_key as target_title, a.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_agent wlaa
                    JOIN watercooler_messages wm ON wlaa.watercooler_message_id = wm.id
                    LEFT JOIN agents a ON wlaa.agent_id = a.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    UNION ALL
                    SELECT 'operator' as type, wlo.operator_id as target_id, o.agent_key as target_title, o.status as target_status,
                           wm.occurred_ts, wm.content, wm.meta
                    FROM wc_microlog_link_operator wlo
                    JOIN watercooler_messages wm ON wlo.watercooler_message_id = wm.id
                    LEFT JOIN agents o ON wlo.operator_id = o.id
                    CROSS JOIN agent_linked_items
                    WHERE wm.from_agent_id = agent_linked_items.agent_id
                    ORDER BY occurred_ts DESC
                    LIMIT 20
                """
                linked_items = r_query(conn, linked_items_query, [agent_id])
                log(f"Loaded {len(linked_items)} linked items for agent {agent_id}")
                for item in linked_items:
                    ensure_iso_timestamps(item, ['occurred_ts'])
                agent['linked_items'] = linked_items
        result_data = {
            "type": "agent_list",
            "agents": agents,
            "count": len(agents),
            "filters": {
                "role": role,
                "status": status,
                "ask_id": ask_id,
                "task_id": task_id,
                "step_id": step_id
            }
        }
        if limit and result_data.get("agents"):
            result_data["agents"] = result_data["agents"][:limit]
            result_data["count"] = len(result_data["agents"])
            log(f"Applied limit of {limit}, final count: {result_data['count']}")
        
        log(f"Agent list operation completed successfully with {result_data['count']} agents")
        gateway.response.set_action_response(success_payload(result_data))
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to list agents: {str(e)}")
        report_error("backend", f"Failed to list agents: {str(e)}")
        trace_out()
        return False
