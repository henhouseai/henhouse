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


def render_init_db_section(source_data, lines):
    trace_in()
    try:
        db_data = TableData()
        db_data.add_row(
            'project_header',
            value=source_data.get('project_name', 'Unknown')
        )
        init_sql_file = source_data.get('init_sql_file', 'Unknown')
        db_data.add_row(
            'init_sql_file',
            value=init_sql_file
        )
        created_tables = source_data.get('created_tables', 0)
        db_data.add_row(
            'created_tables',
            value=f"{created_tables} tables created"
        )
        initialization_successful = source_data.get('initialization_successful', False)
        status_text = "Complete" if initialization_successful else "Failed"
        db_data.add_row(
            'initialization_status',
            value=f"Initialization: {status_text}"
        )
        lines.append(render_block(
            db_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['init_sql_file', 'created_tables', 'initialization_status']),
            table_overrides={'margin_l': 4}
        ))
    except Exception as e:
        warn(f"Failed to render db initialization section: {str(e)}")
    finally:
        trace_out()

@register_parser('init_db')
def init_db() -> bool:
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
    lines.append(render_header_block('l_init_db_header'))
    source_data = get_data(json_data)
    log(f"Processing db initialization data successfully")
    render_init_db_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
