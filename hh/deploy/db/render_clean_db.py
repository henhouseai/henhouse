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


def render_clean_db_section(source_data, lines):
    trace_in()
    try:
        db_data = TableData()
        db_data.add_row(
            'project_header',
            value=source_data.get('project_name', 'Unknown')
        )
        clean_sql_file = source_data.get('clean_sql_file', 'Unknown')
        db_data.add_row(
            'clean_sql_file',
            value=clean_sql_file
        )
        remaining_tables = source_data.get('remaining_tables', 0)
        db_data.add_row(
            'remaining_tables',
            value=f"{remaining_tables} tables remaining"
        )
        cleanup_successful = source_data.get('cleanup_successful', False)
        status_text = "Complete" if cleanup_successful else "Partial"
        db_data.add_row(
            'cleanup_status',
            value=f"Cleanup: {status_text}"
        )
        lines.append(render_block(
            db_data,
            FieldConfig()
                .add_header('project_header')
                .add_simple(['clean_sql_file', 'remaining_tables', 'cleanup_status']),
            table_overrides={'margin_l': 4}
        ))
    except Exception as e:
        warn(f"Failed to render db cleanup section: {str(e)}")
    finally:
        trace_out()

@register_parser('clean_db')
def clean_db() -> bool:
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
    lines.append(render_header_block('l_clean_db_header'))
    source_data = get_data(json_data)
    log(f"Processing db cleanup data successfully")
    render_clean_db_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
