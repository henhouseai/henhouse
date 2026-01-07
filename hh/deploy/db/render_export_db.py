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


def render_export_db_section(source_data, lines):
    trace_in()
    try:
        db_data = TableData()
        db_data.add_row(
            'project_header',
            value=source_data.get('project_name', 'Unknown')
        )
        export_file = source_data.get('export_file', 'Unknown')
        db_data.add_row(
            'export_file',
            value=export_file
        )
        export_size = source_data.get('export_size', 0)
        size_mb = export_size / (1024 * 1024)
        db_data.add_row(
            'export_size',
            value=f"{size_mb:.2f} MB"
        )
        table_count = source_data.get('table_count', 0)
        db_data.add_row(
            'table_count',
            value=f"{table_count} tables"
        )
        
        # Render the pre-formatted table data from the action
        table_info = source_data.get('table_info', [])
        if table_info:
            # Convert table_info list to TableData object
            table_data = TableData()
            for row in table_info:
                table_data.add_row(
                    row.get('field_type', 'table_info'),
                    label=row.get('label', ''),
                    name=row.get('name', ''),
                    row_count=row.get('row_count', '')
                )
            lines.append(render_block(
                table_data,
                FieldConfig()
                    .add_simple(['label', 'name', 'row_count']),
                table_overrides={'margin_l': 4}
            ))
    except Exception as e:
        warn(f"Failed to render database export section: {str(e)}")
    finally:
        trace_out()

@register_parser('export_db')
def export_db() -> bool:
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
    lines.append(render_header_block('l_export_db_header'))
    source_data = get_data(json_data if json_data is not None else {})
    log(f"Processing database export data successfully")
    render_export_db_section(source_data, lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
