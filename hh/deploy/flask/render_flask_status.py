from hh.gateway.registry.registry import register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data

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

def render_flask_daemons(source_data, lines):
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_flask_daemons")
        trace_out()
        return
    
    block = 'daemons'
    if not gateway.is_no(block):
        daemons_data = TableData()
        
        # Add header row to define column structure
        daemons_data.add_row('daemon_status_header', name='Tier', user='User', port='Port')
        
        daemons = source_data.get('daemons', [])
        log(f"Rendering {len(daemons)} Flask daemons")
        
        for daemon in daemons:
            tier = daemon.get('tier', 'unknown')
            status = daemon.get('status', 'unknown')
            user = daemon.get('user', '')
            port = daemon.get('port', '')
            
            user_str = safe_str(user) if user else '-'
            port_str = safe_str(str(port)) if port else '-'
            
            if status == 'running':
                daemons_data.add_row('daemon_running', name=safe_str(tier), user=user_str, port=port_str)
            elif status == 'stopped':
                daemons_data.add_row('daemon_stopped', name=safe_str(tier), user=user_str, port=port_str)
            elif status == 'not_deployed':
                daemons_data.add_row('daemon_not_deployed', name=safe_str(tier), user=user_str, port=port_str)
            elif status == 'error':
                error_msg = daemon.get('error', 'Unknown error')
                daemons_data.add_row('daemon_error', name=safe_str(tier), user=user_str, port=port_str)
        
        lines.append(render_block(
            daemons_data,
            FieldConfig()
                .add_header('daemon_status_header')
                .add_simple(['daemon_running', 'daemon_stopped', 'daemon_not_deployed', 'daemon_error']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    
    trace_out()

@register_parser('flask_status')
def flask_status() -> bool:
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
    lines = []
    lines.append(render_header_block('l_flask_status_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing Flask status data")
    
    render_flask_daemons(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

