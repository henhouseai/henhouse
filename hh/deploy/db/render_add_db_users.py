from hh.gateway.registry.registry import register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData

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



def render_db_user_deploy_section(source_data, lines):
    """Render the database user deployment section."""
    trace_in()
    try:
        db_data = TableData()
        
        # Project info
        db_data.add_row(
            'project_header',
            value=source_data.get('project_name', 'Unknown')
        )
        
        # Individual user results
        user_results = source_data.get('user_results', [])
        for result in user_results:
            username = result.get('username', 'Unknown')
            tier = result.get('tier', 'Unknown')
            status = result.get('status', 'Unknown')
            error = result.get('error', '')
            permissions = result.get('permissions', [])
            
            # Main user status
            if status == 'created':
                field_type = 'user_created'
            elif status == 'exists':
                field_type = 'user_existing'
            elif status == 'updated':
                field_type = 'user_updated'
            elif status == 'failed':
                field_type = 'user_failed'
            else:
                field_type = 'user_failed'  # fallback for unknown status
            value = f"{username} ({tier})"
            if error:
                value += f" - {error}"
            
            db_data.add_row(
                field_type,
                value=value
            )
            
            # Show privileges for created, existing, or updated users
            if permissions and status in ['created', 'exists', 'updated']:
                db_data.add_row(
                    'permission_message',
                    value=f"Privileges: {', '.join(permissions)}"
                )
            
            # Show detailed permission changes for updated users
            if status in ['updated', 'exists'] and 'permission_status' in result:
                perm_status = result['permission_status']
                if perm_status.get('status') == 'updated':
                    message = perm_status.get('message', '')
                    db_data.add_row(
                        'permission_message',
                        value=f"Updated: {message}"
                    )
                elif perm_status.get('status') == 'correct':
                    db_data.add_row(
                        'permission_message',
                        value="Permissions already correct"
                    )
                elif perm_status.get('status') == 'error':
                    db_data.add_row(
                        'permission_message',
                        value=f"Permission check failed: {perm_status.get('message', 'unknown error')}"
                    )
        
        # Render the data
        lines.append(render_block(
            db_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['user_created', 'user_existing', 'user_failed', 'user_updated', 'permission_message']),
            table_overrides={'margin_l': 4}
        ))
        
    except Exception as e:
        warn(f"Failed to render database user deployment section: {str(e)}")
    finally:
        trace_out()

@register_parser('add_db_users')
def parse_add_db_users() -> bool:
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
    lines.append(render_header_block('l_add_db_users_header'))
    source_data = get_data(json_data)
    log(f"Processing database user deployment data successfully")
    
    render_db_user_deploy_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True