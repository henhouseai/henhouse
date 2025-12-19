from __future__ import annotations
from typing import Dict, List, Union, Any
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.agents.agents_utils import render_subscription_details, render_linked_items_details, render_activity_details

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


def render_agents_summary(source_data: Dict[str, Union[str, int, list]], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return None
    if not gateway.is_no(block):
        count = source_data.get('count', 0)
        filters_raw: Any = source_data.get('filters', {})
        filters: Dict[str, Any] = {}
        if isinstance(filters_raw, dict):
            filters = filters_raw
        log(f"Rendering agents summary: count={count}, filters={filters}")
        summary_data = TableData()
        summary_data.add_row(
            'agent_list_header',
            value=f"Found {count} agent{'s' if count != 1 else ''}"
        )
        summary_data.add_row(
            'count',
            value=str(count)
        )
        if filters and any(v is not None for v in filters.values()):
            filter_parts = []
            for key, value in filters.items():
                if value is not None:
                    filter_parts.append(f"{key}={value}")
            if filter_parts:
                log(f"Active filters applied: {', '.join(filter_parts)}")
                summary_data.add_row(
                    'filters',
                    value=', '.join(filter_parts)
                )
        lines.append(render_block(
            summary_data,
            FieldConfig()
                .add_header('agent_list_header')
                .add_simple(['count', 'filters', 'agent_id', 'agent_name', 'created_at', 'terminated', 'gate_status', 'gate_started_ts', 'session_id', 'runs'])
                .add_group(['role_active', 'role_inactive', 'role_terminated'], 'agent_role')
                .add_group(['status_active', 'status_inactive'], 'agent_status'),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_agent_summary(agent: Dict[str, Union[str, int]], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return None
    if not gateway.is_no(block): 
        table_data = TableData()
        agent_id = agent.get('id', 'Unknown')
        agent_key = agent.get('agent_key', 'Unknown')
        log(f"Rendering agent summary: id={agent_id}, key={agent_key}")
        table_data.add_row(
            'agent_id',
            value=str(agent_id)
        )
        table_data.add_row(
            'agent_name',
            value=agent_key
        )
        role = agent.get('role', 'Unknown')
        status = agent.get('status', 'Unknown')
        role_field_type = f"role_{status}" if status in ['active', 'inactive', 'terminated'] else 'role_active'
        table_data.add_row(
            role_field_type,
            value=safe_str(role)
        )
        status_field_type = f"status_{status}" if status in ['active', 'inactive'] else 'status_active'
        table_data.add_row(
            status_field_type,
            value=safe_str(status)
        )
        if agent.get('created_at'):
            table_data.add_row(
                'created_at',
                value=safe_str(agent.get('created_at'))
            )
        if agent.get('terminated') is not None:
            terminated_value = "Yes" if agent.get('terminated') else "No"
            table_data.add_row(
                'terminated',
                value=terminated_value
            )
        if agent.get('gate_status'):
            table_data.add_row(
                'gate_status',
                value=safe_str(agent.get('gate_status'))
            )
        if agent.get('gate_started_ts'):
            table_data.add_row(
                'gate_started_ts',
                value=safe_str(agent.get('gate_started_ts'))
            )
        if agent.get('session_id'):
            table_data.add_row(
                'session_id',
                value=str(agent.get('session_id'))
            )
        if 'agent_runs' in agent:
            agent_runs: Any = agent.get('agent_runs', [])
            runs_count = len(agent_runs) if isinstance(agent_runs, (list, tuple)) else 0
            log(f"Agent has {runs_count} agent runs")
            table_data.add_row(
                'runs',
                value=str(runs_count)
            )
        lines.append(render_block(
            table_data,
            FieldConfig()
                .add_header('agent_list_header')
                .add_simple(['count', 'filters', 'agent_id', 'agent_name', 'created_at', 'terminated', 'gate_status', 'gate_started_ts', 'session_id', 'runs'])
                .add_group(['role_active', 'role_inactive', 'role_terminated'], 'agent_role')
                .add_group(['status_active', 'status_inactive'], 'agent_status'),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()

def render_agent_rows(agents: List[Dict[str, Union[str, int]]], lines: List[str]) -> None:
    trace_in()
    debug(f"render_agent_rows called with agents type: {type(agents)}")
    agents = agents or []
    debug(f"After null check, agents type: {type(agents)}, length: {len(agents) if agents is not None else 'None'}")
    log(f"Rendering {len(agents)} agent rows")
    for i, agent in enumerate(agents):
        debug(f"Processing agent {i}: type={type(agent)}, keys={list(agent.keys()) if hasattr(agent, 'keys') else 'No keys'}")
        render_agent_summary(agent, lines)
        subscriptions_raw: Any = agent.get('subscriptions', [])
        subscriptions: List[Any] = []
        if isinstance(subscriptions_raw, list):
            subscriptions = subscriptions_raw
        debug(f"Agent {i} subscriptions type: {type(subscriptions)}, length: {len(subscriptions) if subscriptions is not None else 'None'}")
        render_subscription_details(subscriptions, lines)
        linked_items_raw: Any = agent.get('linked_items', [])
        linked_items: List[Any] = []
        if isinstance(linked_items_raw, list):
            linked_items = linked_items_raw
        debug(f"Agent {i} linked_items type: {type(linked_items)}, length: {len(linked_items) if linked_items is not None else 'None'}")
        render_linked_items_details(linked_items, lines)
        recent_activity_raw: Any = agent.get('recent_activity', [])
        recent_activity: List[Any] = []
        if isinstance(recent_activity_raw, list):
            recent_activity = recent_activity_raw
        debug(f"Agent {i} recent_activity type: {type(recent_activity)}, length: {len(recent_activity) if recent_activity is not None else 'None'}")
        if recent_activity:
            log(f"Rendering {len(recent_activity)} recent activities for agent")
            render_activity_details(recent_activity, lines, 'activity')
        break_section(lines)
    trace_out()

@register_parser('agent_list')
def agent_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False   
    json_data = gateway.response.get_action_response()
    if json_data is None:
        warn("No action response data available")
        trace_out()
        return False
    debug(f"Raw action response type: {type(json_data)}")
    debug(f"Raw action response keys: {list(json_data.keys()) if hasattr(json_data, 'keys') else 'No keys method'}")
    lines = []
    lines.append(render_header_block('l_agent_list'))
    source_data = get_data(json_data)
    debug(f"Parsed source_data type: {type(source_data)}")
    debug(f"Parsed source_data keys: {list(source_data.keys()) if hasattr(source_data, 'keys') else 'No keys method'}")
    if 'agents' in source_data:
        log("Processing multiple agents data")
        agents = source_data.get('agents', [])
        debug(f"Agents type: {type(agents)}, length: {len(agents) if agents is not None else 'None'}")
        render_agents_summary(source_data, lines)
        render_agent_rows(agents, lines)
    elif 'agent' in source_data:
        log("Processing single agent data")
        render_agent_summary(source_data.get('agent', {}), lines)
        render_subscription_details(source_data.get('subscriptions', []), lines)
        render_linked_items_details(source_data.get('linked_items', []), lines)
        activities = source_data.get('activities', [])
        if activities:
            log(f"Rendering {len(activities)} activities for single agent")
            render_activity_details(activities, lines, 'activity')
    else:
        log("No agent data found in response")
        lines.append("No agent data found in response")
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

@register_parser('agent_tree')
def agent_tree() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False   
    json_data = gateway.response.get_action_response()
    if json_data is None:
        warn("No action response data available")
        trace_out()
        return False
    lines = []
    lines.append(render_header_block('l_agent_list'))
    source_data = get_data(json_data)
    if 'agent' in source_data:
        log("Processing single agent data for agent_tree")
        render_agent_summary(source_data.get('agent', {}), lines)
        render_subscription_details(source_data.get('subscriptions', []), lines)
        render_linked_items_details(source_data.get('linked_items', []), lines)
        activities = source_data.get('activities', [])
        if activities:
            log(f"Rendering {len(activities)} activities for single agent")
            render_activity_details(activities, lines, 'activity')
    elif 'agents' in source_data:
        log("Processing multiple agents data")
        render_agents_summary(source_data, lines)
        render_agent_rows(source_data.get('agents', []), lines)
    else:
        log("No agent data found in response")
        lines.append("No agent data found in response")
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

