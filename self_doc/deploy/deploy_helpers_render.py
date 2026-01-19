"""
Self-doc deployment render hooks.

Provides summary contribution and detail table for context deployment.
"""
from typing import Dict, Any
from hh.render.render import TableData, FieldConfig, render_block
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


@register_module_hook('deploy_95_render', 'Contribute context deployment summary')
def render_context_summary_contribution() -> Dict[str, Any]:
    """Contribute context deployment summary to deployment summary table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find context deployment data
    files_deployed = 0
    dirs_deployed = 0
    for result in hook_results:
        if result.get('component') == 'context_deployment':
            files_deployed = result.get('files_deployed', 0)
            dirs_deployed = result.get('directories_deployed', 0)
            break

    if files_deployed == 0 and dirs_deployed == 0:
        return trace_out({})

    # Create summary line
    table_data = TableData()
    summary = f"{files_deployed} files, {dirs_deployed} directories"
    table_data.add_row('context_summary', value=f"Context: {summary}")

    field_config = FieldConfig()
    field_config.add_simple(['context_summary'])

    return trace_out({
        "table_data": table_data,
        "field_config": field_config
    })


@register_module_hook('deploy_95_render', 'Render context detail table')
def render_context_detail_table() -> Dict[str, Any]:
    """Render context deployment details as a separate full table."""
    trace_in()

    gateway = get_gateway()
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data) if json_data else {}
    hook_results = source_data.get('hook_results', [])

    # Find context deployment data
    context_items = []
    for result in hook_results:
        if result.get('component') == 'context_deployment' and result.get('items'):
            context_items = result['items']
            break

    if not context_items:
        return trace_out({})

    table_data = TableData()
    table_data.add_row('context_detail_header', value='')

    for item in context_items:
        table_data.add_row('context_item', value=item)

    field_config = FieldConfig()
    field_config.add_header('context_detail_header')
    field_config.add_simple(['context_item'])

    context_table_html = render_block(table_data, field_config, table_overrides={'margin_l': 4}, block_type='context_items')
    return trace_out({
        "render_block": context_table_html
    })
