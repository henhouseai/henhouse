"""
MCP Tool Registrations for Agent Operations

Registers agent-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Read operations - available to all tiers
@register_mcp_tool(
    tool_name='agent_list',
    description='List available agents with optional filtering by role, status, ask/task/step, and other criteria.',
    inputSchema={
        'type': 'object',
        'properties': {
            'role': {'type': 'string', 'description': 'Filter agents by role'},
            'status': {'type': 'string', 'description': "Filter agents by status (defaults to 'active' if not provided)"},
            'ask_id': {'type': 'integer', 'description': 'Filter agents that have activity related to a specific ask'},
            'task_id': {'type': 'integer', 'description': 'Filter agents that have activity related to a specific task'},
            'step_id': {'type': 'integer', 'description': 'Filter agents that have activity related to a specific step'},
            'deep': {'type': 'boolean', 'description': 'Enable deep mode for additional details'},
            'limit': {'type': 'integer', 'description': 'Limit the number of results returned'}
        },
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='agent_tree',
    description='Get detailed information about a specific agent including basic profile data, work docket assignment, and optional deep mode for comprehensive activity logs, subscriptions, linked items, and runtime state.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to retrieve information for'},
            'deep': {'type': 'boolean', 'description': 'Enable deep mode for comprehensive additional data including activity logs, subscriptions, and relationship data'}
        },
        'required': ['agent_id']
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='peek',
    description='View queued messages without removing them from queues. Can filter by agent and channels.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'Optional agent ID to filter messages. If not provided, shows messages for all agents.'},
            'channels': {'type': 'string', 'description': "Comma-separated list of channels to view (defaults to all channels if not provided). Valid channels: docket, ask, task, step, sidecar, keyword, agent, operator, dm"},
            'deep': {'type': 'boolean', 'description': 'Enable deep mode for additional message details'}
        },
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='status',
    description='Get comprehensive status for an agent including training progress, answers, and current state.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to get status for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'}
        },
        'required': ['agent_id', 'badge_ts']
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
# Write operations - available to admin and root tiers only
@register_mcp_tool(
    tool_name='agent_purge',
    description='Archive active agents (excluding operators) and clean up related data. Requires confirmation flag for safety. Use dry-run to preview changes.',
    inputSchema={
        'type': 'object',
        'properties': {
            'confirm': {'type': 'boolean', 'description': 'Confirmation flag required for purge operation. Must be set to true to proceed.'},
            'dry_run': {'type': 'boolean', 'description': 'Preview what would be affected without making changes'}
        },
        'required': ['confirm']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='punch_in',
    description='Punch in an agent to start a work session. Creates or updates agent profile and sets status to active.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to punch in'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'}
        },
        'required': ['agent_id', 'badge_ts']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='punch_out',
    description='Punch out an agent to end a work session. Sets agent status to inactive.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to punch out'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'}
        },
        'required': ['agent_id', 'badge_ts']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='gossip',
    description='Send a message from one agent to another. Creates a watercooler message and queues it for the target agent.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent sending the message'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation (optional)'},
            'message': {'type': 'string', 'description': 'The message content to send'},
            'to_agent_id': {'type': 'integer', 'description': 'The ID of the target agent (alternative to to_full_name)'},
            'to_full_name': {'type': 'string', 'description': 'The full name of the target agent (alternative to to_agent_id)'},
            'meta_json': {'type': 'string', 'description': 'Optional JSON metadata to attach to the message'}
        },
        'required': ['agent_id', 'message']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='gulp',
    description='Export queued messages for an agent to a file. Messages are removed from queues after export.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent whose messages to export'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation (optional)'},
            'channels': {'type': 'string', 'description': "Comma-separated list of channels to export (defaults to all channels if not provided). Valid channels: docket, ask, task, step, sidecar, keyword, agent, operator, dm"},
            'output_file': {'type': 'string', 'description': 'Optional output file path. If not provided, a default filename is generated based on agent name.'}
        },
        'required': ['agent_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='sip',
    description='Consume and remove queued messages for an agent. Messages are removed from queues after being retrieved.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent whose messages to consume'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation (optional)'},
            'channels': {'type': 'string', 'description': "Comma-separated list of channels to consume (defaults to all channels if not provided). Valid channels: docket, ask, task, step, sidecar, keyword, agent, operator, dm"}
        },
        'required': ['agent_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='subscribe_agent',
    description='Subscribe an agent to receive messages from another agent. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'target_agent_id': {'type': 'integer', 'description': 'The ID of the target agent to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'target_agent_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_ask',
    description='Subscribe an agent to receive messages related to a specific ask. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'ask_id': {'type': 'integer', 'description': 'The ID of the ask to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'ask_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_task',
    description='Subscribe an agent to receive messages related to a specific task. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'task_id': {'type': 'integer', 'description': 'The ID of the task to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'task_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_step',
    description='Subscribe an agent to receive messages related to a specific step. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'step_id': {'type': 'integer', 'description': 'The ID of the step to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'step_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_sidecar',
    description='Subscribe an agent to receive messages related to a specific sidecar file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'sidecar_file_id': {'type': 'integer', 'description': 'The ID of the sidecar file to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'sidecar_file_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_keyword',
    description='Subscribe an agent to receive messages related to a specific keyword. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'keyword_id': {'type': 'integer', 'description': 'The ID of the keyword to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'keyword_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_docket',
    description='Subscribe an agent to receive messages related to a specific work docket. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'docket_id': {'type': 'integer', 'description': 'The ID of the work docket to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'docket_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='subscribe_operator',
    description='Subscribe an agent to receive messages from an operator. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to create the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'operator_id': {'type': 'integer', 'description': 'The ID of the operator to subscribe to'},
            'all_back_data': {'type': 'boolean', 'description': 'Include all historical data in the subscription (optional)'},
            'since_timestamp': {'type': 'string', 'description': 'Include data since this timestamp (optional)'},
            'new_only': {'type': 'boolean', 'description': 'Only include new data going forward (optional)'}
        },
        'required': ['agent_id', 'badge_ts', 'operator_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='unsubscribe_agent',
    description='Unsubscribe an agent from receiving messages from another agent. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'target_agent_id': {'type': 'integer', 'description': 'The ID of the target agent to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'target_agent_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_ask',
    description='Unsubscribe an agent from receiving messages related to a specific ask. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'ask_id': {'type': 'integer', 'description': 'The ID of the ask to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'ask_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_task',
    description='Unsubscribe an agent from receiving messages related to a specific task. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'task_id': {'type': 'integer', 'description': 'The ID of the task to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'task_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_step',
    description='Unsubscribe an agent from receiving messages related to a specific step. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'step_id': {'type': 'integer', 'description': 'The ID of the step to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'step_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_sidecar',
    description='Unsubscribe an agent from receiving messages related to a specific sidecar file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'sidecar_file_id': {'type': 'integer', 'description': 'The ID of the sidecar file to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'sidecar_file_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_keyword',
    description='Unsubscribe an agent from receiving messages related to a specific keyword. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'keyword_id': {'type': 'integer', 'description': 'The ID of the keyword to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'keyword_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_docket',
    description='Unsubscribe an agent from receiving messages related to a specific work docket. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'docket_id': {'type': 'integer', 'description': 'The ID of the work docket to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'docket_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='unsubscribe_operator',
    description='Unsubscribe an agent from receiving messages from an operator. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to remove the subscription for'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'operator_id': {'type': 'integer', 'description': 'The ID of the operator to unsubscribe from'}
        },
        'required': ['agent_id', 'badge_ts', 'operator_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='onboard',
    description='Create a new training agent and begin onboarding process. Automatically creates agent with \'apprentice\' role and queues first training message.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='promote',
    description='Promote an agent to a new role and queue role-specific training. Agent must be inactive (will be punched out if active).',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent to promote'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'role': {'type': 'string', 'description': 'The new role to promote the agent to'}
        },
        'required': ['agent_id', 'badge_ts', 'role']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='answer',
    description='Process an agent\'s answer to a training question and queue the next training message. Either answer text or ack_read flag must be provided.',
    inputSchema={
        'type': 'object',
        'properties': {
            'agent_id': {'type': 'integer', 'description': 'The ID of the agent submitting the answer'},
            'badge_ts': {'type': 'string', 'description': 'The badge timestamp for agent identity validation'},
            'answer': {'type': 'string', 'description': 'The answer text to the training question (alternative to ack_read)'},
            'ack_read': {'type': 'boolean', 'description': 'Acknowledge that the document was read without providing an answer (alternative to answer)'}
        },
        'required': ['agent_id', 'badge_ts']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
def _agent_tools_registration():
    """Registration placeholder for all agent-related MCP tools."""
    pass

