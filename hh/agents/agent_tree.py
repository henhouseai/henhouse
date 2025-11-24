from __future__ import annotations
from typing import List
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

@register_action('agent_tree')
@register_command('agent_tree')
def agent_tree() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return False
    agent_id = gateway.get_arg('agent_id')
    deep_mode = gateway.get_arg('deep')
    log(f"Processing agent tree for agent_id={agent_id}, deep_mode={deep_mode}")
    if not agent_id:
        warn("Agent ID is required but not provided")
        report_error("action", "Agent ID is required")
        trace_out()
        return False
    try:
        agent_query = """
        SELECT a.id, a.agent_key, a.role, a.status, a.created_at,
               a.terminated, a.gate_status, a.gate_started_ts, a.session_id
        FROM agents a
        WHERE a.id = %s
        """
        agent_results = gateway.conn.read(agent_query, [agent_id])
        if not agent_results:
            warn(f"Agent {agent_id} not found")
            report_error("action", f"Agent {agent_id} not found")
            trace_out()
            return False
        agent_row = agent_results[0]
        log(f"Found agent: {agent_row.get('agent_key', 'Unknown')} (ID: {agent_id})")
        ensure_iso_timestamps(agent_row, ['created_at', 'gate_started_ts'])
        result_data = {
            "type": "agent_tree",
            "agent": agent_row
        }
        if not deep_mode:
            log("Deep mode disabled, returning basic agent data")
            gateway.response.set_action_response(success_payload(result_data))
            trace_out()
            return True
        runs_query = """
        SELECT ar.id, ar.session_id, ar.prompt, ar.model, ar.log_path,
               ar.started_ts, ar.last_heartbeat_ts, ar.status, ar.notes
        FROM agent_runs ar
        WHERE ar.agent_id = %s
        ORDER BY ar.started_ts DESC
        LIMIT 10
        """
        runs = gateway.conn.read(runs_query, [agent_id])
        log(f"Loaded {len(runs)} agent runs for agent {agent_id}")
        for run in runs:
            ensure_iso_timestamps(run, ['started_ts', 'last_heartbeat_ts'])
        result_data["agent_runs"] = runs
        activity_query = """
        SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts
        FROM watercooler_messages wm
        WHERE wm.from_agent_id = %s
        ORDER BY wm.occurred_ts DESC
        LIMIT 50
        """
        activities = gateway.conn.read(activity_query, [agent_id])
        log(f"Loaded {len(activities)} activities for agent {agent_id}")
        for activity in activities:
            ensure_iso_timestamps(activity, ['occurred_ts'])
            if activity.get('meta') and isinstance(activity['meta'], str):
                try:
                    import json
                    activity['meta'] = json.loads(activity['meta'])
                except:
                    pass
        result_data["activities"] = activities
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
        subscriptions = gateway.conn.read(subscriptions_query, [agent_id])
        log(f"Loaded {len(subscriptions)} subscriptions for agent {agent_id}")
        for sub in subscriptions:
            ensure_iso_timestamps(sub, [])
        result_data["subscriptions"] = subscriptions
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
        LIMIT 30
        """
        linked_items = gateway.conn.read(linked_items_query, [agent_id])
        log(f"Loaded {len(linked_items)} linked items for agent {agent_id}")
        for item in linked_items:
            ensure_iso_timestamps(item, ['occurred_ts'])
            if item.get('meta') and isinstance(item['meta'], str):
                try:
                    import json
                    item['meta'] = json.loads(item['meta'])
                except:
                    pass
        result_data["linked_items"] = linked_items
        state_query = """
        SELECT mode, latch, fail_count, last_cycle_ts, last_validation_json
        FROM agent_runtime_state
        WHERE agent_id = %s
        """
        state_results = gateway.conn.read(state_query, [agent_id])
        if state_results:
            state_row = state_results[0]
            log(f"Loaded agent state for agent {agent_id}")
            ensure_iso_timestamps(state_row, ['last_cycle_ts'])
            result_data["agent_state"] = state_row
        log(f"Agent tree operation completed successfully for agent {agent_id}")
        gateway.response.set_action_response(success_payload(result_data))
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to get agent tree: {str(e)}")
        report_error("backend", f"Failed to get agent tree: {str(e)}")
        trace_out()
        return False
